# Contributing

Thanks for considering a contribution to InstaPull.

## Local Setup

```bash
pip install -e ".[all]"
```

Create a local `.env` from the example:

```bash
cp .env.example .env
```

Do not commit `.env`.

## Adding An AI Provider

Providers live in `instapull/providers/`.

To add a provider:

1. Create a new provider file.
2. Implement the `VisionProvider` interface from `instapull/providers/base.py`.
3. Register the provider in `instapull/providers/__init__.py`.
4. Add any optional dependency to `pyproject.toml`.
5. Document the required environment variables in `.env.example` and `README.md`.

Local providers should not bundle model files in this repository. Prefer integrations with local runtimes, such as Ollama, so users can choose which model to download on their own machine.

## Checks

Before opening a pull request, run:

```bash
python3 -m compileall instapull
python3 -m unittest discover
python3 -m instapull.cli --help
python3 -m instapull.cli sync --help
```
