from testcases.models import TestCase

from .pytest_runner import PytestExecutionRunner


class UnsupportedExecutionTypeError(ValueError):
    pass


RUNNER_REGISTRY = {
    TestCase.TestType.FUNCTIONAL: PytestExecutionRunner,
}


def get_execution_runner(testcase):
    test_type = getattr(testcase, 'test_type', TestCase.TestType.FUNCTIONAL)
    runner_cls = RUNNER_REGISTRY.get(test_type)
    if runner_cls is None:
        raise UnsupportedExecutionTypeError(
            f'Execution type "{test_type}" is not implemented yet.'
        )
    return runner_cls()
