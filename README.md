# 🎸 slowhand

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

# slowhand should have been installed in `~/.local/bin/`
slowhand version
```

or just run:

```bash
./build-install.sh
```

## Slack app

Cadence

https://api.slack.com/apps/A0ABCGHB68G/install-on-team

| Field              | Value                              |
| ------------------ | ---------------------------------- |
| App ID             | `A0ABCGHB68G`                      |
| Client ID          | `3101026052.10386561380288`        |
| Client Secret      | `6e443cde799ddf1786859a22d8e36611` |
| Signing Secret     | `e7fbd55867b760a5c816cd0761bfd51b` |
| Verification Token | `jTA41AhuvG11tgrEhMiC3kzl`         |
