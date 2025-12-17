# slowhand

```bash
pdm sync

pdm test -s
pdm test -k <PATTERN>

SLOWHAND_DEBUG=1 pdm run slowhand run setup
```

## Install locally

```bash
pdm build
pip install dist/slowhand-<version>-py3-none-any.whl --user --force-reinstall
```
