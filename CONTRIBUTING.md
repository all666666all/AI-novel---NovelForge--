# Contributing to NovelForge

Thanks for taking the time to contribute! 🎉

## Ways to help

- 🐛 **Report bugs** — open an issue with steps to reproduce.
- 💡 **Suggest features** — describe the problem you're trying to solve.
- 💻 **Send a pull request** — fixes, features, docs, tests.

## Development setup

See the [Local development](README.md#-local-development) section of the README to run the
backend (FastAPI) and frontend (Vue 3) locally.

## Before you open a PR

Keep CI green. The same checks run in [GitHub Actions](.github/workflows/ci.yml):

```bash
# Backend
cd backend
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=. pytest tests -q

# Frontend (type-check + build)
cd frontend
npm ci
npm run build
```

## Guidelines

- Match the style and structure of the surrounding code.
- Keep pull requests focused; one logical change per PR is easier to review.
- Add or update tests when you change backend behavior.
- Update the docs/README when you change setup, configuration, or public behavior.

## Reporting security issues

Please do **not** open a public issue for security vulnerabilities. Report them privately to
the maintainer instead.
