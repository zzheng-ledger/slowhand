import hashlib
import re
import unicodedata

from slowhand.actions import create_action
from slowhand.config import settings
from slowhand.context import Context
from slowhand.errors import SlowhandException
from slowhand.expression import evaluate_condition
from slowhand.logging import alert, get_logger, muted, primary
from slowhand.models import Job, JobStep

logger = get_logger(__name__)


def _slugify(text: str) -> str:
    value = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value.strip("-_")


def _get_step_id(step: JobStep) -> str:
    if step.id:
        return step.id
    # Build a deterministic and non-empty ID from step name.
    prefix = "auto"
    slug = _slugify(step.name)
    suffix = hashlib.sha256(step.name.encode("utf-8")).hexdigest()[:8]
    return "-".join([prefix, slug, suffix])


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
        for step in job.steps:
            step_id = _get_step_id(step)
            step_desc = f"{primary(step.name)} ({muted(step_id)})"

            if context.has_step_outputs(step_id):
                logger.info("○ Skipping step: %s (already run)", step_desc)
                continue

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
            if step.condition is None or evaluate_condition(
                step.condition, context=context
            ):
                logger.info("● Running step: %s", step_desc)
                outputs = action.run(params, context=context, dry_run=dry_run)
                context.save_step_outputs(step_id, outputs)
            else:
                logger.info("○ Skipping step: %s", step_desc)

        logger.info("✓ Job completed successfully.")
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


def run_job(job: Job, *, dry_run: bool = False, clean: bool = True) -> None:
    context = Context(job.job_id)
    _run_job_with_context(job, context, dry_run=dry_run, clean=clean)


def resume_job(job: Job, *, dry_run: bool = False, clean: bool = True) -> None:
    context = Context.load_checkpoint()
    _run_job_with_context(job, context, dry_run=dry_run, clean=clean)
