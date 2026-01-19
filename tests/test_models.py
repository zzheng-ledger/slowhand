from slowhand.loader import load_job
from slowhand.models import JobInput


def test_compute_version():
    # See: `jobs/sample.yaml`
    job = load_job("sample")
    assert job.name == "Sample Job"
    assert job.inputs == {
        "strParam": JobInput(
            description="A required string parameter",
            type="string",
            required=True,
            default="foo bar",
        ),
        "intParam": JobInput(
            description="An optional int parameter",
            type="int",
            required=False,
            default=None,
        ),
        "boolParam": JobInput(
            description=None,
            type="bool",
            required=True,
            default=None,
        ),
    }
    assert [step.name for step in job.steps] == ["Clone git repo", "List files"]
