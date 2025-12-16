from slowhand.loader import load_job


def test_compute_version():
    job = load_job("sample")
    assert job.name == "Sample Job"
    assert len(job.steps) == 2
