from slowhand.actions import create_action
from slowhand.config import settings
from slowhand.context import Context
from slowhand.errors import SlowhandException
from slowhand.expression import evaluate_condition
from slowhand.logging import get_logger, muted, primary
from slowhand.models import Job

logger = get_logger(__name__)


def run_job(job: Job, *, clean: bool = True) -> None:
    context = Context()
    try:
        logger.info("» Running job: %s", primary(job.name))
        for step in job.steps:
            if step.kind == "RunShell":
                # Convert a `RunShell` step to an `actions/shell` action
                action_name = "actions/shell"
                params = {
                    "script": step.run,
                    "working-dir": step.working_dir,
                }
            elif step.kind == "UseAction":
                action_name = step.uses
                params = step.params
            else:
                raise SlowhandException(f"Unknown step kind: {step.kind}")

            action = create_action(action_name)
            params = context.resolve(params or {})
            step_desc = (
                f"{primary(step.name)} ({muted(action_name)}), id={muted(step.id)}"
            )
            if step.condition is None or evaluate_condition(
                step.condition, context=context
            ):
                logger.info("● Running step: %s", step_desc)
                outputs = action.run(params, context=context)
                if step.id and outputs:
                    context.save_step_outputs(step.id, outputs)
            else:
                logger.info("○ Skipping step: %s", step_desc)

        if clean and not settings.debug:
            logger.info("Cleaning up...")
            context.teardown()

    except Exception as exc:
        logger.error("Job %s failed: %s", job.name, exc)
        logger.info("Run dir is kept: %s", context.run_dir)
        if settings.debug:
            raise
