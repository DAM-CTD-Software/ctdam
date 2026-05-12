class BinnedDataError(Exception):
    """A custom error to throw when binned data has been detected."""

    def __init__(self, file_name: str, step_name: str):
        super().__init__(
            f"{step_name} cannot be applied to binned data in {file_name}"
        )


class UnexpectedFileFormat(Exception):
    """A custom error to throw when a file is not formatted as expected."""

    def __init__(self, file_type: str, error: str) -> None:
        super().__init__(f"{file_type} is not formatted as expected: {error}")


class MissingParameterError(Exception):
    """A custom error to throw when necessary parameters are missing from the
    input .cnv file."""

    def __init__(self, step_name: str, parameter_name: str):
        super().__init__(
            f"Could not run processing step {
                step_name
            } due to a missing parameter: {parameter_name}"
        )


class InvalidArgumentCombination(Exception):
    """Exception raised when an invalid combination of arguments is provided."""

    pass
