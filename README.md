Patch tool with enhanced configuration:
- context line case ignore
- whitespace ignore
- string trimming
- skip wrong hunk lines

i will extend this readme later because i believe no one will even see it lmao.

# Install

```
pip install git+https://github.com/Toliak/sloppatch
```

To install specific version:
```
pip install git+https://github.com/Toliak/sloppatch@v0.1.0
```

# Dev dependencies

```bash
python3 -m venv .venv
source ./.venv/bin/activate
pip install -e '.[dev]'
```

Dev-container (optional):

```
make docker-dev
```

# Linting & tests

```
make ruff
```

```
make mypy
```

```
make test
```
