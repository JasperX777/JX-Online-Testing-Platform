import sys
from typing import Sequence

from executions.models import TestExecution

from .base import BaseExecutionRunner


class PytestExecutionRunner(BaseExecutionRunner):
    def build_command(self, execution: TestExecution) -> Sequence[str]:
        cmd = [sys.executable, '-m', 'pytest', '-q']
        if execution.testcase and execution.testcase.pytest_target:
            cmd.append(execution.testcase.pytest_target)
        return cmd
