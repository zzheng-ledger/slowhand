# slowhand

```bash
pdm sync

pdm test -s
pdm test -k <PATTERN>

SLOWHAND_DEBUG=1 pdm run slowhand job revault-deploy-to-stg
```

## Install locally

```bash
pdm build
pip install dist/slowhand-<version>-py3-none-any.whl --user --force-reinstall
```

## Terminology

- A **job** is a set of steps in a workflow.
- Each **step** is either a shell script that will be executed, or an action that will be run.

## Jira

See: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/

- Authenticate in https://id.atlassian.com
- Create API token (don't use scopes)
- Specify API token name and expiration
- Create token, and save it in env var: `JIRA_API_TOKEN`

## Example
