# Contributing

Python 3.11 or newer is required. Runtime code has no third-party dependencies; tests require `pytest`.

```powershell
python -m pip install pytest
$env:PYTHONPATH='src'
python -m pytest -q
python -m compileall -q src tests run.py
python run.py --db data/release_check.db release-check
```

## Contribution rules

- Keep each change focused and add relevant tests.
- Use minimal, sanitized, offline fixtures for parser tests. CI must not access live websites.
- Do not commit `data/*.db`, `.env`, webhooks, internal customer material, or private sales notes.
- Do not fabricate active opportunities, award amounts, competitors, or supplier roles.
- Mark vendor, integrator, and competitor classifications as uncertain unless supported by verifiable evidence.
- Do not solve collection failures by disabling TLS checks or bypassing CAPTCHA or access control.
- Document public availability and compliance constraints before adding a source.

Before opening a pull request, run the test suite, compile check, and `release-check`. The pull request should explain the problem, implementation, test evidence, and data/compliance impact.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
