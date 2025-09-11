# GeoExhibit

[![CI](https://github.com/burrbd/geoexhibit/actions/workflows/ci.yml/badge.svg)](https://github.com/burrbd/geoexhibit/actions/workflows/ci.yml)

A minimal, test-driven Python toolkit for publishing static STAC metadata and raster outputs to S3.

## Development Rules

This project follows strict development rules enforced by Cursor and GitHub Actions:

- **Commit Discipline**: One unit of code with its matching test per commit; push frequently
- **Conventional Commits**: Clean, task-level commit messages
- **CI Gate**: All code must pass ruff linting, black formatting, pytest tests, and mypy type checking
- **Python Standards**: Python ≥ 3.11, type hints everywhere, mypy --strict

Rules are stored in `.cursor/rules/` as individual `.mdc` files for proper Cursor registration.

## CI Gate

The CI gate is enforced via:

1. **GitHub Actions**: Runs ruff, black, pytest, mypy on every push/PR
2. **CI Checker**: Use `python3 ci_gate.py burrbd geoexhibit` to check status
3. **Required**: Set `GITHUB_TOKEN` environment variable for CI status checks

## Quick Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Check code quality
black --check .
ruff check .
mypy geoexhibit
```

## Current Status

- ✅ Project setup with pyproject.toml
- ✅ TimeSpan model with tests
- ✅ GitHub Actions CI pipeline
- ✅ CI gate checker utility
- ✅ Proper Cursor rules registration
- 🚧 Analyzer interface (in progress)

## License

MIT