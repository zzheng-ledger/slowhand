from slowhand.check import check_job
from slowhand.loader import load_builtin_jobs


def test_builtin_jobs():
    jobs = load_builtin_jobs()
    for job in jobs:
        print(f"Validating job: {job.source} : {job.name}")
        check_job(job)
