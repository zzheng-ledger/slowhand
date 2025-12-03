from slowhand.config import config
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger, muted, primary
from slowhand.actions import ActionParams, create_action
from slowhand.models import Job
from slowhand.context import Context

logger = get_logger(__name__)


def run_action(
    name: str,
    id: str | None,
    *,
    params: ActionParams | None = None,
    context: Context,
):
    params = params or {}
    action = create_action(name, id)
    logger.info("● Running action: %s (%s)", primary(action.name), muted(action.id))
    action.run(params, context=context)


def run_job(job: Job, *, clean: bool = True) -> None:
    context = Context()
    try:
        logger.info("○ Running job: %s", primary(job.name))
        for step in job.steps:
            if step.kind == "RunShell":
                name = "actions/shell"
                params = {
                    "script": step.run,
                    "working-dir": step.working_dir,
                }
            elif step.kind == "UseAction":
                name = step.uses
                params = step.params
            else:
                raise SlowhandException(f"Unknown step kind: {step.kind}")
            run_action(name, step.id, params=context.resolve(params), context=context)
    except Exception as exc:
        logger.error("Job %s failed: %s", job.name, exc)
        if config.debug:
            raise
    finally:
        if clean:
            context.teardown()
