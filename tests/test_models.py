from pathlib import Path

from slowhand.models import load_job


def test_load_job():
    job = load_job("sample-job")
    assert job.name == "Sample Job"
    assert len(job.steps) == 6
