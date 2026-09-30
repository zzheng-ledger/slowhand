# AGENTS.md

Guidance for AI coding agents working in this repository.

## 1. Project overview

`slowhand` is a Python CLI tool (installed as both `slowhand` and `slow`) that
runs **jobs**: declarative, YAML-defined workflows made of **steps**, similar
in spirit to a mini GitHub Actions runner. It is used internally (Ledger) to
automate release/deploy chores such as:

- Cloning repos, creating branches, committing and pushing (`git`)
- Creating/editing GitHub PRs (`gh`)
- Creating Jira tickets
- Sending Slack messages
- Running arbitrary shell scripts
- App-specific automation for "Revault" deploy/dependency workflows

Each job is a YAML file describing inputs and a list of steps. Steps either:
- run a **built-in action** (`uses: actions/<name>`) implemented in Python, or
- run a **shell script** (`run: |- ...`), or
- group **nested steps** (`steps:` inside a step).

Job state (inputs/outputs/step outputs, metadata like `run_id`/`run_dir`) is
tracked in a `Context` object. Values in YAML can reference this state via
`${{ meta.xxx }}`, `${{ inputs.xxx }}`, `${{ outputs.xxx }}`,
`${{ steps.<id>.outputs.xxx }}`. Steps also support a small expression
language for `if:` conditions (see `src/slowhand/expression/`), e.g.
`if: inputs.env == "prod" && steps.build.outputs.ok == "true"`.

If a job fails mid-run, its state is checkpointed to
`~/.slowhand/checkpoint.json` and can be resumed later (`resume` CLI command,
see `src/slowhand/runner.py`).

## 2. Tech stack

- Python **>= 3.13** (see `pyproject.toml`; note the sandbox here may only
  have an older Python 3.11 available — check before assuming things run).
- Package/dependency manager: **PDM** (`pdm-backend`), lockfile `pdm.lock`.
- CLI framework: **Typer** (+ **Rich** for console output).
- Data/validation: **Pydantic v2** (+ `pydantic-settings` for config).
- YAML parsing: **PyYAML**.
- Integrations: `jira` (Jira REST client), `slack-sdk`, and shelling out to
  the `git` and `gh` (GitHub CLI) binaries.
- Lint/format: **ruff**. Type checking: **mypy** (with the pydantic plugin).
- Tests: **pytest**.

## 3. Directory structure

```
pyproject.toml         # project metadata, deps, pdm scripts, tool config
pdm.lock                # locked dependencies (managed by pdm, do not hand-edit)
build-install.sh        # cleans, builds wheel via pdm, installs it, sanity-checks it
src/slowhand/
  main.py                # Typer CLI entry point (commands: config, version, info,
                          #   jobs, show, run, resume, ...)
  models.py               # Pydantic models: Job, JobStep (UseAction/RunShell/StepsAction),
                          #   JobInput, and input parsing/validation
  loader.py               # Finds/loads job YAML files (user jobs dirs + builtin jobs/)
  runner.py               # run_job()/resume_job(): executes a Job's steps against a Context
  context.py              # Context: run state store, ${{ ... }} variable resolution,
                          #   checkpoint save/load, run_dir teardown
  check.py                # check_job(): validates a Job's steps (duplicate IDs, unknown actions)
  config.py               # Settings (pydantic-settings): env vars (SLOWHAND_*), and
                          #   ~/.slowhand/config.json persistence; also picks up
                          #   GITHUB_TOKEN / JIRA_API_TOKEN / SLACK_API_TOKEN env vars
  logging.py               # ConsoleLogger + rich color helpers (primary/secondary/muted/...)
  tools.py / utils.py      # run_command/run_shell_script subprocess helpers, misc utils
  version.py               # VERSION, read from generated src/slowhand/VERSION (pdm-scm)
  expression/              # Small lexer/parser + AST evaluator for `if:` conditions
    lexer.py, parser.py
  actions/                 # One file per action "family"; each Action subclass
                          #   implements `run(params, *, context, dry_run) -> dict | None`
    base.py                 # Action ABC + ActionParams type
    __init__.py              # create_action(name): registry mapping "actions/<name>" -> class
    git.py, github.py, jira.py, slack.py, shell.py, print.py, abort.py,
    setup.py, version.py, revault_deploy.py, revault_deps.py
  jobs/                    # Built-in job YAML definitions (shipped with the package)
    sample.yaml, setup.yaml, revault-*.yaml, update-release.yaml
tests/
  conftest.py               # shared fixtures (e.g. project_dir)
  test_expression.py, test_jobs.py, test_models.py
  actions/test_version.py   # per-action tests live under tests/actions/
```

## 4. Setup / install

This project uses **PDM**. If PDM isn't available, `uv` can usually manage an
equivalent venv/toolchain.

```bash
# Install PDM if missing (e.g. via pipx/uv)
pipx install pdm            # or: uv tool install pdm

# Install project + dev dependencies into a PDM-managed venv
pdm install -G dev
# (build-install.sh instead does `pdm sync` then builds/installs the wheel
#  with pip; use that when you want to test the *installed* CLI end-to-end)
```

Requires Python >= 3.13. `pyproject.toml` pins `requires-python = ">=3.13"`
and `pdm.lock` was generated for that constraint — don't try to install on an
older interpreter.

## 5. Build / run / test / lint (PDM scripts, from `pyproject.toml`)

Preferred: use the predefined `pdm` scripts so behavior matches CI/maintainer
expectations.

```bash
pdm run lint        # ruff check src tests
pdm run format       # ruff --fix + import sort + ruff format (auto-fixes in place)
pdm run typecheck    # mypy src tests --warn-unused-ignores
pdm run test         # pytest
pdm run slowhand     # or `pdm run slow` — run the CLI directly (e.g. `pdm run slow jobs`)
```

Equivalent raw commands (if you have the deps installed without pdm scripts):

```bash
ruff check src tests
ruff format src tests
mypy src tests --warn-unused-ignores
pytest
```

Build a wheel and install it into the current environment (full sanity check,
mirrors CI/release):

```bash
./build-install.sh
```

This removes `dist/`, runs `pdm sync` + `pdm build`, `pip install --user
--force-reinstall` the resulting wheel, then runs `slowhand version` to
verify installation.

Explore jobs without writing code:

```bash
pdm run slow jobs                 # list builtin + user jobs
pdm run slow show <job_id>        # show job details (steps, inputs)
pdm run slow show <job_id> --brief
pdm run slow run <job_id> --input key=value ...   # (see main.py for exact flags)
```

## 6. Coding conventions

- **Imports**: standard-lib, then third-party, then local (`slowhand.*`),
  each group sorted — enforced by `ruff check --select I --fix` (part of
  `pdm run format`). Always run `pdm run format` before finishing a change.
- **Typing**: fully type-hinted; `mypy` runs in `check_untyped_defs = true`
  mode with the pydantic mypy plugin. Use `@override` (from `typing`) when
  overriding `Action.run`.
- **Models**: use Pydantic `BaseModel` for structured data (job models,
  action params). Field aliases use kebab-case in YAML
  (`Field(None, alias="working-dir")`) mapped to snake_case Python attributes
  — keep this convention for any new step/action parameters.
- **Actions** (`src/slowhand/actions/*.py`):
  - Subclass `Action` (in `actions/base.py`), set a class attribute
    `name = "kebab-case-name"` (this becomes `actions/<name>` in YAML `uses:`).
  - Define a nested `Params(BaseModel)` class for input validation.
  - Implement `run(self, params: ActionParams, *, context: Context, dry_run: bool) -> dict | None`.
  - Respect `dry_run`: never perform side-effecting/destructive operations
    (git push, PR creation, ticket creation, sending messages, ...) when
    `dry_run=True`; log a warning instead (see `git.py`, `github.py` for the
    pattern).
  - Return step outputs as a flat `dict[str, SimpleValue]` (str/bool/int/None).
  - Register the new class in `_BUILTIN_ACTIONS` and `__all__`/imports in
    `src/slowhand/actions/__init__.py`.
- **Errors**: raise `slowhand.errors.SlowhandException` for expected/user
  facing failures (invalid input, missing job, disallowed operation, etc.).
  The runner catches this at the job level, checkpoints state, and reports a
  friendly error — don't let unexpected exceptions leak without reason.
- **Logging**: use `slowhand.logging.get_logger(__name__)` (a thin wrapper
  around stdlib `logging` + Rich), and the color helpers (`primary`,
  `secondary`, `muted`, `ok`, `success`, `danger`, `alert`, `notice`) for
  user-facing console messages rather than plain `print`.
- **Subprocess calls**: use `slowhand.utils.run_command` (argv-style, capture
  output, raises on non-zero) or `run_shell_script` (multi-line bash script
  with `set -e`) instead of calling `subprocess` directly.
- **Naming**: job step outputs and input keys are snake_case in Python /
  kebab-case where they appear as YAML `with:` keys.
- **Job YAML files** (`src/slowhand/jobs/*.yaml`): each file's basename
  (without extension) is its `job_id`. Steps need unique `name`s (an `id` is
  auto-derived by slugifying+hashing the name if not explicit); prefer adding
  an explicit `id:` for any step whose outputs are referenced elsewhere
  (`${{ steps.<id>.outputs.<key> }}`), since the auto-id changes if the name
  changes.
- **Tests**: mirror source layout — `tests/test_<module>.py`, and
  `tests/actions/test_<action_module>.py` for action-specific tests. New
  built-in jobs are automatically covered by `tests/test_jobs.py::test_builtin_jobs`,
  which loads and structurally validates (`check_job`) every job under
  `src/slowhand/jobs/`; make sure new/edited job YAML still passes this
  (unique step IDs, only referencing registered `actions/*`).

## 7. Gotchas / important notes

- **Never commit secrets.** `~/.slowhand/config.json` and env vars
  (`SLOWHAND_*`, `GITHUB_TOKEN`/`GH_TOKEN`, `JIRA_API_TOKEN`,
  `SLACK_API_TOKEN`) hold credentials for GitHub/Jira/Slack — these belong in
  the user's environment, never in the repo. `Settings.save()` explicitly
  excludes secret fields (`github.token`, `jira.api_token`) when persisting
  to disk; keep that exclusion in mind when adding new secret settings.
- **`src/slowhand/VERSION` is generated**, not checked in (see `.gitignore`
  and `[tool.pdm.version]` in `pyproject.toml`, using `pdm-backend`'s SCM
  versioning). Don't hand-write or commit this file; `version.py` falls back
  to `"0.0.0.dev"` if it's missing.
- **Actions that shell out to `git`/`gh`** assume those binaries are
  installed and authenticated (see `actions/setup.py` for the `setup` job
  that checks/bootstraps this). Don't assume they exist in a minimal sandbox.
- **Respect `dry_run` everywhere** — it's the main safety valve for
  destructive actions (git push, PR/ticket creation, Slack messages). Any new
  action performing external side effects must support it.
- **Context variable syntax** `${{ ... }}` only accepts a restricted set of
  variable name patterns (`meta.*`, `inputs.*`, `outputs.*`,
  `steps.<id>.outputs.*`) — see `_VAR_NAME_REGEX` in `context.py`. Don't
  invent new prefixes without updating that regex and the resolver.
- **Step IDs must be unique** within a job (checked by `check_job` /
  `Job.validate_steps`); duplicate IDs across nested `StepsAction` groups are
  also rejected.
- **Checkpointing**: on job failure, state is saved to a single, global
  `~/.slowhand/checkpoint.json` (not per-job) and the run's temp `run_dir` is
  kept on disk (only cleaned up on success, unless `debug` is set). Resuming
  loads this fixed checkpoint file. Avoid running two jobs in parallel/relying
  on concurrent checkpoints.
- **Python version mismatch risk**: `pyproject.toml`/`pdm.lock` require
  Python >= 3.13, using syntax like `match` statements and `typing.override`.
  If your sandbox's default `python3` is older (this repo's dev container may
  have 3.11), install/select a 3.13 interpreter (e.g. via `pdm python install
  3.13` or `uv python install 3.13`) before running `pdm install`/tests.
- **PDM/uv not preinstalled everywhere**: this repo assumes `pdm` is on PATH;
  if it's missing, install it first (`pipx install pdm` or `uv tool install
  pdm`) rather than trying to `pip install -e .` directly (dynamic
  SCM-sourced version + `pdm-backend` build backend expects pdm's build flow).
- Always run `pdm run format`, `pdm run lint`, `pdm run typecheck`, and
  `pdm run test` before considering a change complete.
