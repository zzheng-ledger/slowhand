from slowhand.actions import create_action
from slowhand.errors import SlowhandException
from slowhand.models import Job, JobStep


def _check_steps(steps: list[JobStep], seen_step_ids: set[str]) -> None:
    for step in steps:
        step_id = step.id
        if step_id in seen_step_ids:
            raise SlowhandException(f"Duplicated step ID: {step_id}")
        seen_step_ids.add(step_id)

        if step.kind == "StepsAction":
            _check_steps(step.steps, seen_step_ids)
        else:
            if step.kind == "RunShell":
                step = step.as_use_action_step()
            if step.kind != "UseAction":
                raise SlowhandException(f"Unknown step kind: {step.kind}")
            create_action(step.uses)


def check_job(job: Job) -> None:
    _check_steps(job.steps, set())
