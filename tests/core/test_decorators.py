import pytest

from grpc import RpcError, StatusCode

from armonik_cli_core.decorators import error_handler
from armonik_cli.exceptions import InternalArmoniKError, InternalCliError


class DummyRpcError(RpcError):
    def __init__(self, code, details):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


@pytest.mark.parametrize(
    ("exception", "code"),
    [(InternalArmoniKError, StatusCode.UNAVAILABLE)],
)
def test_error_handler_rpc_error(exception, code):
    @error_handler
    def raise_error(code, details):
        raise DummyRpcError(code=code, details=details)

    with pytest.raises(exception):
        raise_error(code, "")


@pytest.mark.parametrize("decorator", [error_handler, error_handler()])
def test_error_handler_other_no_debug(decorator):
    @decorator
    def raise_error():
        raise ValueError()

    with pytest.raises(InternalCliError):
        raise_error()


@pytest.mark.parametrize("decorator", [error_handler, error_handler()])
def test_error_handler_other_debug(decorator):
    @decorator
    def raise_error(debug=None):
        raise ValueError()

    with pytest.raises(InternalCliError):
        raise_error(debug=True)
