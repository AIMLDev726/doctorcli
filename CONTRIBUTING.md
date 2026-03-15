# Contributing

Thank you for contributing to `doctorcli`.

## Repository

- Repository: [github.com/AIMLDev726/doctorcli](https://github.com/AIMLDev726/doctorcli)
- Issues: [github.com/AIMLDev726/doctorcli/issues](https://github.com/AIMLDev726/doctorcli/issues)

## Local setup

```bash
pip install -e ".[dev]"
```

## Before opening a pull request

1. Verify the CLI starts with `doctorcli`.
2. Run `python -m compileall src`.
3. Build artifacts with `python -m build`.
4. Keep generated files such as `__pycache__`, `.pytest_cache`, `dist`, `build`, and `*.egg-info` out of commits.
5. Update `README.md` if user-facing behavior, supported providers, or tools change.
