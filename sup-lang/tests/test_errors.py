import pytest
from sup.cli import run_source
from sup.errors import SupSyntaxError, SupRuntimeError


def test_program_must_start_with_sup():
    code = "print 1\nbye"
    with pytest.raises(SupSyntaxError):
        run_source(code)


def test_program_must_end_with_bye():
    code = "sup\nprint 1"
    with pytest.raises(SupSyntaxError):
        run_source(code)


def test_undefined_variable_runtime_error():
    code = (
        """
sup
  print foo
bye
""".strip()
    )
    with pytest.raises(SupRuntimeError):
        run_source(code)


