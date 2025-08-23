import pytest
from sup.cli import run_source
from sup.errors import SupRuntimeError
from sup.interpreter import _SupThrown


def test_try_catch_prints_thrown_value():
    code = (
        """
sup
  try
    throw "x"
  catch e
    print e
  end try
bye
""".strip()
    )
    out = run_source(code)
    assert out.strip() == "x"


def test_finally_runs_with_and_without_throw():
    code1 = (
        """
sup
  try
    throw "A"
  finally
    print "done"
  end try
bye
""".strip()
    )
    import pytest
    with pytest.raises(Exception):
        run_source(code1)

    code2 = (
        """
sup
  try
    print "ok"
  finally
    print "done"
  end try
bye
""".strip()
    )
    out2 = run_source(code2)
    assert out2.splitlines() == ["ok", "done"]


def test_uncaught_throw_propagates():
    code = (
        """
sup
  throw "boom"
bye
""".strip()
    )
    with pytest.raises((_SupThrown, SupRuntimeError)):
        run_source(code)


