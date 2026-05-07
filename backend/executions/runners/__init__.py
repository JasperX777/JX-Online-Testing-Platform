class UnsupportedExecutionTypeError(ValueError):
    pass


def get_execution_runner(_testcase):
    raise UnsupportedExecutionTypeError('Automated execution runners are no longer supported.')
