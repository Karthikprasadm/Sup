Contributing to SUP
===================

Thanks for your interest in contributing!

Getting started
---------------
1. Fork and clone the repo
2. Create a virtual environment and install dev deps
```
python -m venv .venv
.venv/Scripts/activate
pip install -e sup-lang
pip install pytest pre-commit
pre-commit install
```
3. Run tests
```
pytest -q sup-lang
```

Development workflow
--------------------
- Create a feature branch from `main`
- Write tests in `sup-lang/tests/`
- Run `pre-commit run -a` to fix style/lint
- Ensure tests are green
- Open a PR with a clear title and description

Transpile testing
-----------------
```
sup transpile sup-lang/examples/06_mixed.sup --out dist_py
python dist_py/run.py
```

Pull request guidelines
-----------------------
- Keep PRs focused and small when possible
- Update docs and examples if behavior changes
- Follow the code style enforced by pre-commit hooks
- Add yourself to the PR description if you want attribution in CHANGELOG

Reporting issues
----------------
Please include:
- Repro steps or a minimal `.sup` snippet
- Expected vs actual behavior
- Version info (SUP version, Python version, OS)


