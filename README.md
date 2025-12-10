# slowhand

```bash
pdm sync

pdm test -s
pdm test -k <PATTERN>

SLOWHAND_DEBUG=1 pdm run slowhand job revault-deploy-to-stg
```

## Terminology

Workflow, Job, Step

A **job** is a set of steps in a workflow. Each **step** is either a shell script that will be executed, or an action that will be run. Steps are executed in order and are dependent on each other. Since each step is executed on the same runner, you can share data from one step to another. For example, you can have a step that builds your application followed by a step that tests the application that was built.

## Jira

See: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/

- Authenticate in https://id.atlassian.com
- Create API token (don't use scopes)
- Specify API token name and expiration
- Select API token app: `Jira`
- Select Jira scopes:
  - `write:issue:jira` - Create and update issues
  - `write:issue.property:jira` - Create and update issue properties
- Create token, and save it in env var: `JIRA_API_TOKEN`

## Example
