# file: services/exceptions.py


class JobNotFoundError(Exception):
    """Raised when a job with a specific ID is not found."""

    pass


class InvalidJobActionError(Exception):
    """Raised when an invalid action is attempted on a job (e.g., cancelling a completed job)."""

    pass


class SchedulingError(Exception):
    """Raised when the downstream scheduler (Volcano or Slurm) fails to accept a job."""

    pass
