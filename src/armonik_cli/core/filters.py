import operator
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import cast, Any, List, Callable, Union, Optional

from armonik.common import (
    Filter,
    Partition,
    Result,
    ResultStatus,
    Session,
    SessionStatus,
    Task,
    TaskStatus,
)
from armonik.common.filter import (
    BooleanFilter,
    PartitionFilter,
    ResultFilter,
    SessionFilter,
    StringFilter,
    TaskFilter,
    TaskOptionFilter,
    StatusFilter,
    FilterError,
)
from armonik.common.filter.filter import FType
from lark import Lark, Transformer, Token, UnexpectedInput

from armonik_cli.utils import parse_time_delta, remove_string_delimiters


class ParsingError(Exception):
    """
    Exception raised for parsing errors in filter expressions.

    Attributes:
        msg: The error message describing the parsing issue.
        context: A snippet of the expression showing the error in context.
    """

    def __init__(self, msg: str, context: str = "") -> None:
        super().__init__()
        self.msg = msg
        self.context = context

    def __str__(self) -> str:
        """
        Generate a string representation of the parsing error.

        Returns:
            A detailed error message.
        """
        message = "Filter syntax error.\n\n"
        message += "\n".join([f"\t{line}" for line in self.context.split("\n")])
        message += f"\n{self.msg}"
        return message


class SemanticError(Exception):
    """
    Exception raised for semantic errors in filter expressions.

    Attributes:
        msg: The error message describing the semantic issue.
        expr: The filter expression where the error occurred.
        pos: The position of the error in the expression (zero-based index).
        context: A snippet of the expression showing the error in context.
    """

    def __init__(self, msg: str, expr: str, column: Optional[int] = None) -> None:
        super().__init__()
        self.msg = msg
        self.expr = expr
        self.pos = column - 1 if column is not None else -1
        self.context = self.get_context(80)

    def get_context(self, span: int) -> str:
        """
        Generate a context string highlighting the error position in the expression.

        Args:
            span: The number of characters to show before and after the error.

        Returns:
            A formatted string showing the error context.
        """
        start = max(self.pos - span, 0)
        end = self.pos + span
        before = self.expr[start : self.pos].rsplit("\n", 1)[-1]
        after = self.expr[self.pos : end].split("\n", 1)[0]
        return f"\n\t{before}{after}\n\t" + len(before.expandtabs()) * " " + "^\n\n"

    def __str__(self) -> str:
        """
        Generate a string representation of the semantic error.

        Returns:
            A detailed error message.
        """
        message = "Invalid filter expression.\n"
        message += self.context
        message += self.msg
        return message


class FilterParser:
    """
    A parser for processing and validating filter expressions.

    Attributes:
        obj: The ArmoniK API object associated with the filter.
        filter: The ArmoniK API filter corresponding to the object.
        status_enum: The enumeration for the object's status, if applicable.
        options_fields: Whether to allow filtering by options fields (e.g., TaskOptions).
        output_fields: Whether to allow filtering by output fields for Task filters.
    """

    _grammar_file = Path(__file__).parent / "filter_grammar.lark"

    def __init__(
        self,
        obj: Union[Partition, Result, Session, Task],
        filter: Union[PartitionFilter, ResultFilter, SessionFilter, TaskFilter],
        status_enum: Optional[Union[ResultStatus, SessionStatus, TaskStatus, None]] = None,
        options_fields: bool = False,
        output_fields: bool = False,
    ) -> None:
        self.obj = obj
        self.filter = filter
        self.status_enum = status_enum
        self.options_fields = options_fields
        self.output_fields = output_fields

    @classmethod
    def get_parser(cls) -> Lark:
        """
        Generate a Lark parser for the grammar associated with the filter.

        Returns:
            A Lark parser instance.
        """
        with cls._grammar_file.open() as file:
            grammar = file.read()
            return Lark(grammar, start="start", parser="earley")

    def parse(self, expression: str) -> Filter:
        """
        Parse a filter expression into a Filter object.

        Args:
            expression: The filter expression as a string.

        Returns:
            A Filter object constructed from the parsed expression.
        """
        if not expression:
            raise ParsingError(msg="Empty filter expression.")
        try:
            tree = self.get_parser().parse(expression)
            filter = FilterTransformer(
                obj=self.obj,
                filter=self.filter,
                status_enum=self.status_enum,
                options_fields=self.options_fields,
                output_fields=self.output_fields,
                expr=expression,
            ).transform(tree)
            return filter
        except UnexpectedInput as error:
            label = error.match_examples(
                parse_fn=self.get_parser().parse,
                examples={
                    "Invalid character.": ["#", "c#"],
                    "Invalid boolean operator.": ["(status = running) zig (session_id = string)"],
                    "Missing field before operator.": ["= string"],
                    "Missing operator after identifier": ["session_id string"],
                    "Missing value after operator.": ["session_id ="],
                },
            )
            if label is None:
                label = "The expression is not a valid filter."
            raise ParsingError(msg=label, context=error.get_context(expression))


class FilterTransformer(Transformer):
    """
    A transformer to convert parsed filter expressions into Filter objects.

    Attributes:
        obj: The ArmoniK API object associated with the filter.
        filter: The ArmoniK API filter corresponding to the object.
        status_enum: The object status enumeration.
        options_fields: Whether options fields are allowed in the filter.
        output_fields: Whether output fields are allowed in the filter.
        expr: The original filter expression.
    """

    def __init__(
        self,
        obj: Union[Partition, Result, Session, Task],
        filter: Union[PartitionFilter, ResultFilter, SessionFilter, TaskFilter],
        expr: str,
        status_enum: Optional[Union[ResultStatus, SessionStatus, TaskStatus, None]] = None,
        options_fields: bool = False,
        output_fields: bool = False,
    ) -> None:
        super().__init__(visit_tokens=True)
        self._obj = obj
        self._filter = filter
        self._status_enum = status_enum
        self._expr = expr
        self._options_fields = options_fields
        self._output_fields = output_fields

    def expr(self, args: List[Union[Filter, Token]]) -> Filter:
        """
        Combine multiple filter expressions using logical OR.

        Args:
            args: A list of filters and OR tokens.

        Returns:
            The combined filter expression.
        """
        return reduce(operator.or_, [item for item in args if not isinstance(item, Token)])

    def term(self, args: List[Union[Filter, Token]]) -> Filter:
        """
        Combine multiple filter expressions using logical AND.

        Args:
            args: A list of filters and AND tokens.

        Returns:
            The combined filter expression.
        """
        return reduce(operator.and_, [item for item in args if not isinstance(item, Token)])

    def factor(self, args: List[Union[Filter, Token]]) -> Filter:
        """
        Process a single filter or its negation.

        Args:
            args: A list containing a single filter and an optional token for its negation.

        Returns:
            The processed filter.
        """
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return -cast(Filter, args[1])
        msg = f"Unexpected token sequence: {args}."
        raise ValueError(msg)

    def comparison(self, args: List[Token]) -> Filter:
        """
        Process a comparison expression.

        Args:
            args: Tokens representing the comparison (field, operator, value).

        Returns:
            The resulting filter.
        """
        if len(args) != 3:
            msg = f"Unexpected token sequence: {args}."
            raise ValueError(msg)
        _, filter = args[0].value
        op: Callable[[Filter, Any], Filter] = args[1].value
        value: str = args[2].value

        try:
            if isinstance(filter, StatusFilter):
                value = getattr(self._status_enum, value.upper())
            return op(filter, value)
        except FilterError as error:
            if error.message.startswith("Operator"):
                tok = args[1]
            elif error.message.startswith("Expected value type"):
                tok = args[2]
            else:
                tok = args[0]
            raise SemanticError(
                msg=error.message,
                expr=self._expr,
                column=tok.column,
            )
        except AttributeError:
            msg = f"{self._obj.__name__.lower()} has no status '{value}'."
            raise SemanticError(
                msg=msg,
                expr=self._expr,
                column=args[2].column,
            )
        except AttributeError:
            msg = f"{self._obj.__name__.lower()} has no status '{value}'."
            raise SemanticError(
                msg=msg,
                expr=self._expr,
                column=args[2].column,
            )

    def test(self, args: List[Token]) -> BooleanFilter:
        """
        Process a test expression.

        Args:
            args: A list of tokens containing the field and filter data.

        Returns:
            The boolean filter extracted from the token.

        Raises:
            SemanticError: If the field's filter is not a boolean field.
            ValueError: If an unexpected token sequence is provided.
        """
        if len(args) == 1:
            field, filter = args[0].value
            if isinstance(filter, BooleanFilter):
                return filter
            msg = f"{self._obj.__name__.capitalize()} filter's '{field}' field is not a boolean field. You must use it in an expression of the form 'field op value'."
            raise SemanticError(
                msg=msg,
                expr=self._expr,
                column=args[0].column,
            )
        msg = f"Unexcepted token sequence: {args}."
        raise ValueError(msg)

    def identifier(self, args: List[Token]) -> Token:
        """
        Resolves and validates an identifier token, updating its value based on field type.

        Args:
            args: A list of tokens containing identifier details.

        Returns:
            The updated token with resolved field information.

        Raises:
            SemanticError: If the field is invalid or unsupported.
            ValueError: If an unexpected token sequence is provided.
        """
        if len(args) == 1:
            field = args[0].value
            if field.startswith("options."):
                option_field = field[8:]
                if not self._options_fields:
                    msg = f"{self._obj.__name__.capitalize()} fillers don't have options fields."
                    raise SemanticError(
                        msg=msg,
                        expr=self._expr,
                        column=args[0].column,
                    )
                if (
                    option_field not in TaskOptionFilter._fields
                    or TaskOptionFilter._fields[option_field][0] == FType.NA
                    or TaskOptionFilter._fields[option_field][0] == FType.UNKNOWN
                ):
                    msg = f"{self._obj.__name__.capitalize()} fillers don't have a field '{option_field}' in the option fields."
                    raise SemanticError(
                        msg=msg,
                        expr=self._expr,
                        column=args[0].column,
                    )
                return args[0].update(value=(field, getattr(self._obj.options, option_field)))
            elif field.startswith("output."):
                output_field = field[7:]
                if not self._output_fields:
                    msg = f"{self._obj.__name__.capitalize()} fillers don't have output fields."
                    raise SemanticError(
                        msg=msg,
                        expr=self._expr,
                        column=args[0].column,
                    )
                if output_field != "error":
                    msg = f"{self._obj.__name__.capitalize()} fillers don't have a field '{output_field}' in the output fields."
                    raise SemanticError(
                        msg=msg,
                        expr=self._expr,
                        column=args[0].column,
                    )
                return args[0].update(value=(field, getattr(self._obj.output, output_field)))
            if (
                field not in self._filter._fields
                or self._filter._fields[field][0] == FType.NA
                or self._filter._fields[field][0] == FType.UNKNOWN
            ):
                msg = f"{self._obj.__name__.capitalize()} filters don't have a field '{field}'."
                raise SemanticError(
                    msg=msg,
                    expr=self._expr,
                    column=args[0].column,
                )
            return args[0].update(value=(field, getattr(self._obj, field)))
        elif len(args) == 3:
            key = args[1].value
            if not self._options_fields:
                msg = f"{self._obj.__name__.capitalize()} fillers have no options fields and therefore no custom option fields.."
                raise SemanticError(
                    msg=msg,
                    expr=self._expr,
                    column=args[0].column,
                )
            return args[1].update(value=(f"option['{key}']", self._obj.options[key]))
        msg = f"Unexcepted token sequence: {args}."
        raise ValueError(msg)

    def STRING(self, tok: Token) -> Token:
        """
        Processes a STRING token by removing delimiters.

        Args:
            tok: A STRING token.

        Returns:
            The updated token with delimiters removed.
        """
        return tok.update(value=remove_string_delimiters(tok.value))

    def SIGNED_NUMBER(self, tok: Token) -> Token:
        """
        Converts a SIGNED_NUMBER token to an integer.

        Args:
            tok: A SIGNED_NUMBER token.

        Returns:
            The updated token with an integer value.
        """
        return tok.update(value=int(tok.value))

    def DATETIME(self, tok: Token) -> Token:
        """
        Parses a DATETIME token into a Python datetime object.

        Args:
            tok: A DATETIME token.

        Returns:
            The updated token with a datetime value.
        """
        return tok.update(
            value=datetime.strptime(
                tok.value, "%Y-%m-%dT%H:%M:%S" if "T" in tok.value else "%Y-%m-%d"
            )
        )

    def DURATION(self, tok: Token) -> Token:
        """
        Parses a DURATION token into a timedelta object.

        Args:
            tok: A DURATION token.

        Returns:
            The updated token with a timedelta value.
        """
        return tok.update(value=parse_time_delta(tok.value))

    def EQ(self, tok: Token) -> Token:
        """
        Maps an EQ token to the equality operator.

        Args:
            tok: An EQ token.

        Returns:
            The updated token with the equality operator.
        """
        return tok.update(value=operator.eq)

    def NEQ(self, tok: Token) -> Token:
        """
        Maps an EQ token to the unequality operator.

        Args:
            tok: An NEQ token.

        Returns:
            The updated token with the unequality operator.
        """
        return tok.update(value=operator.ne)

    def LT(self, tok: Token) -> Token:
        """
        Maps an LT token to the lower than operator.

        Args:
            tok: An LT token.

        Returns:
            The updated token with the lower than operator.
        """
        return tok.update(value=operator.lt)

    def LTE(self, tok: Token) -> Token:
        """
        Maps an LTE token to the lower than or equal operator.

        Args:
            tok: An LTE token.

        Returns:
            The updated token with the lower than or equal operator.
        """
        return tok.update(value=operator.le)

    def GT(self, tok: Token) -> Token:
        """
        Maps an GT token to the greater than operator.

        Args:
            tok: An GT token.

        Returns:
            The updated token with the greater than operator.
        """
        return tok.update(value=operator.gt)

    def GTE(self, tok: Token) -> Token:
        """
        Maps an GTE token to the greater than or equal operator.

        Args:
            tok: An GTE token.

        Returns:
            The updated token with the greater than or equal operator.
        """
        return tok.update(value=operator.ge)

    def CONTAINS(self, tok: Token) -> Token:
        """
        Maps an CONTAINS token to a contains operator.

        Args:
            tok: An CONTAINS token.

        Returns:
            The updated token with a function mimicking the contains operator.
        """

        def contains_func(filter: StringFilter, substr: str) -> BooleanFilter:
            return filter.contains(substr)

        return tok.update(value=contains_func)

    def NOTCONTAINS(self, tok: Token) -> Token:
        """
        Maps an NOTCONTAINS token to a not contains operator.

        Args:
            tok: An EQ token.

        Returns:
            The updated token with a function mimicking the not contains operator
        """

        def notcontains_func(filter: StringFilter, substr: str) -> BooleanFilter:
            return -filter.contains(substr)

        return tok.update(value=notcontains_func)

    def STARTSWITH(self, tok: Token) -> Token:
        """
        Maps an STARTSWITH token to a starts with operator.

        Args:
            tok: An STARTSWITH token.

        Returns:
            The updated token with a function mimicking the starts with operator
        """

        def startswith_func(filter: StringFilter, prefix: str) -> BooleanFilter:
            return filter.startswith(prefix)

        return tok.update(value=startswith_func)

    def ENDSWIDTH(self, tok: Token) -> Token:
        """
        Maps an ENDSWITH token to the ends with operator.

        Args:
            tok: An ENDSWITH token.

        Returns:
            The updated token with a function mimicking the ends with operator
        """

        def endswith_func(filter: StringFilter, suffix: str) -> BooleanFilter:
            return filter.endswith(suffix)

        return tok.update(value=endswith_func)

    def IS(self, tok: Token) -> Token:
        """
        Processes an IS token to evaluate a boolean filter.

        Args:
            tok: An IS token.

        Returns:
            The updated token with a function for boolean evaluation.
        """

        def is_func(filter: BooleanFilter, bool_str: str) -> BooleanFilter:
            if bool_str.lower() == "true":
                return filter
            elif bool_str.lower() == "false":
                return -filter
            else:
                msg = f"Invalid value for boolean field: {bool_str}."
                raise SemanticError(
                    msg=msg,
                    expr=self._expr,
                    column=tok.column,
                )

        return tok.update(value=is_func)
