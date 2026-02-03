import json
from textwrap import indent

from slowhand.actions import create_action
from slowhand.config import settings
from slowhand.context import Context
from slowhand.errors import SlowhandException
from slowhand.expression import evaluate_condition
from slowhand.logging import alert, get_logger, muted, primary
from slowhand.models import Job, JobStep

logger = get_logger(__name__)


def _run_steps(
    steps: list[JobStep], context: Context, *, dry_run: bool = False, depth: int = 0
):
    def log_info(msg: str) -> None:
        logger.info(indent(msg, "  " * depth))

    for step in steps:
        step_id = step.id
        step_desc = f"{primary(step.name)} ({muted(step_id)})"

        skip_reason = None
        if context.has_step_outputs(step_id):
            skip_reason = "already run"
        elif step.condition and not evaluate_condition(step.condition, context=context):
            skip_reason = "condition not met"
        if skip_reason:
            log_info(f"○ Skipping step: {step_desc} ({skip_reason})")
            continue

        log_info(f"● Running step: {step_desc}")

        if step.kind == "StepsAction":
            _run_steps(step.steps, context, dry_run=dry_run, depth=depth + 1)
        else:
            if step.kind == "RunShell":
                step = step.as_use_action_step()
            if step.kind != "UseAction":
                raise SlowhandException(f"Unknown step kind: {step.kind}")
            action = create_action(step.uses)
            params = context.resolve(step.params or {})
            outputs = action.run(params, context=context, dry_run=dry_run)
            if outputs:
                log_info(json.dumps(outputs, indent=2))
            context.save_step_outputs(step_id, outputs)


def _run_job_with_context(
    job: Job, context: Context, *, dry_run: bool = False, clean: bool = True
) -> None:
    if job.job_id != context.job_id:
        raise SlowhandException(
            f"Job {job.job_id} does not match context {context.job_id}"
        )

    try:
        logger.info(
            "» Running job: %s%s",
            primary(job.name),
            muted(" (dry-run)") if dry_run else "",
        )
        _run_steps(job.steps, context, dry_run=dry_run)

        logger.info("✓ Job completed successfully.")
        job_outputs = context.get_outputs()
        if job_outputs:
            logger.info("Job outputs:")
            for name, value in job_outputs.items():
                logger.info(f"    {name} = {value}")

        context.delete_checkpoint()
        if clean and not settings.debug:
            context.teardown()

    except Exception as exc:
        logger.error("Job %s failed: %s", job.name, exc)
        checkpoint_file = context.save_checkpoint()
        logger.info("Saved checkpoint at: %s", alert(checkpoint_file))
        logger.info("Run dir is kept: %s", alert(context.run_dir))
        if settings.debug:
            raise

    finally:
        if settings.debug:
            logger.info("Dumping context state:\n%s", context.dump_state_json())


def run_job(
    job: Job, inputs: dict[str, str], *, dry_run: bool = False, clean: bool = True
) -> None:
    context = Context(job.job_id)
    context.save_inputs(job.parse_inputs(inputs))
    _run_job_with_context(job, context, dry_run=dry_run, clean=clean)


def resume_job(job: Job, *, dry_run: bool = False, clean: bool = True) -> None:
    context = Context.load_checkpoint()
    _run_job_with_context(job, context, dry_run=dry_run, clean=clean)
