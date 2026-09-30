# HemaNet backend

Flask API and worker (modular monolith, ADR-001). Dependencies are managed with
[uv](https://docs.astral.sh/uv/) and locked in `uv.lock`.

**Phase E0:** `wsgi.py` and `worker.py` are placeholders so the container stack
can start. The real application structure (blueprint §P.1) begins in Phase E1.

```bash
uv sync                      # create .venv with runtime + dev dependencies
uv run pytest                # tests
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run mypy                  # type check (strict)
uv run bandit -c pyproject.toml -r .   # static security scan
```
