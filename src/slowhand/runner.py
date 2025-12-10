from slowhand.actions import create_action
from slowhand.config import config
from slowhand.context import Context
from slowhand.errors import SlowhandException
from slowhand.expression import evaluate_condition
from slowhand.logging import Style, get_logger
from slowhand.models import Job

logger = get_logger(__name__)


def run_job(job: Job, *, clean: bool = True) -> None:
    context = Context()
    try:
        logger.info("» Running job: %s", Style.PRIMARY.apply(job.name))
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
                f"{Style.PRIMARY.apply(step.name)} "
                f"({Style.MUTED.apply(action_name)}), "
                f"id={Style.MUTED.apply(step.id)}"
            )
            if step.condition is None or evaluate_condition(
                step.condition, context=context
            ):
                logger.info("● Running step: %s", step_desc)
                output = action.run(params, context=context)
                if step.id and output:
                    context.save_output(step.id, output)
            else:
                logger.info("○ Skipping step: %s", step_desc)
    except Exception as exc:
        logger.error("Job %s failed: %s", job.name, exc)
        if config.debug:
            raise
    finally:
        if clean:
            context.teardown()
