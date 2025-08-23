#!/usr/bin/env python
import sys


def main() -> int:
    try:
        import pytest  # type: ignore
    except Exception as e:
        sys.stderr.write("pytest is not installed. Run: pip install pytest\n")
        return 3

    # Default to running the whole project tests quietly
    args = sys.argv[1:] or ["-q", "sup-lang"]
    # Ensure unbuffered output in some shells
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    code = pytest.main(args)
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())


