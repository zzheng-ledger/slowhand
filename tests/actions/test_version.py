import pytest

from slowhand.context import Context
from slowhand.actions import create_action
from slowhand.errors import SlowhandException


def test_compute_version():
    action = create_action("actions/compute-version")
    params = {
        "input": "1.2.3",
        "add-major": 1,
        "add-minor": -1,
        "add-patch": 9,
    }
    context = Context("fake-job-id")
    output = action.run(params, context=context, dry_run=False)
    assert output["result"] == "2.1.12"


def test_compute_version_without_patch():
    action = create_action("actions/compute-version")
    params = {
        "input": "1.2",
        "add-patch": 3,
    }
    context = Context("fake-job-id")
    output = action.run(params, context=context, dry_run=False)
    assert output["result"] == "1.2.3"


def test_patch_number_stays_none():
    action = create_action("actions/compute-version")
    params = {
        "input": "1.2",
        "add-patch": 0,
    }
    context = Context("fake-job-id")
    output = action.run(params, context=context, dry_run=False)
    assert output["result"] == "1.2"


def test_negative_version_component():
    action = create_action("actions/compute-version")
    params = {
        "input": "1.2",
        "add-minor": -3,
    }
    context = Context("fake-job-id")
    with pytest.raises(SlowhandException):
        action.run(params, context=context, dry_run=False)


def test_invalid_patch_number():
    action = create_action("actions/compute-version")
    params = {
        "input": "1.2",
        "add-patch": -1,
    }
    context = Context("fake-job-id")
    with pytest.raises(SlowhandException):
        action.run(params, context=context, dry_run=False)
