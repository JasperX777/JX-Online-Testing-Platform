import subprocess
from typing import Sequence

from django.conf import settings

from executions.models import TestExecution


class BaseExecutionRunner:
    def build_command(self, execution: TestExecution) -> Sequence[str]:
        raise NotImplementedError

    def run(self, execution: TestExecution) -> subprocess.CompletedProcess[str]:
        cmd = list(self.build_command(execution))
        return subprocess.run(
            cmd,
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
