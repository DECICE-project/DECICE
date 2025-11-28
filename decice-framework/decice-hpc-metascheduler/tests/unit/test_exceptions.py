# file: tests/unit/test_exceptions.py

import pytest

from services.exceptions import JobNotFoundError, InvalidJobActionError, SchedulingError


class TestBusinessExceptions:
    """Unit tests for business layer exceptions."""
    
    def test_job_not_found_error_creation(self):
        """Test JobNotFoundError can be created and raised."""
        error_message = "Job with id 12345 not found"
        
        with pytest.raises(JobNotFoundError) as exc_info:
            raise JobNotFoundError(error_message)
        
        assert str(exc_info.value) == error_message
        assert isinstance(exc_info.value, Exception)
    
    def test_job_not_found_error_without_message(self):
        """Test JobNotFoundError can be raised without a message."""
        with pytest.raises(JobNotFoundError):
            raise JobNotFoundError()
    
    def test_invalid_job_action_error_creation(self):
        """Test InvalidJobActionError can be created and raised."""
        error_message = "Cannot cancel a completed job"
        
        with pytest.raises(InvalidJobActionError) as exc_info:
            raise InvalidJobActionError(error_message)
        
        assert str(exc_info.value) == error_message
        assert isinstance(exc_info.value, Exception)
    
    def test_scheduling_error_creation(self):
        """Test SchedulingError can be created and raised."""
        error_message = "Kubernetes API server unavailable"
        
        with pytest.raises(SchedulingError) as exc_info:
            raise SchedulingError(error_message)
        
        assert str(exc_info.value) == error_message
        assert isinstance(exc_info.value, Exception)
    
    def test_all_exceptions_inherit_from_exception(self):
        """Test that all custom exceptions inherit from base Exception."""
        assert issubclass(JobNotFoundError, Exception)
        assert issubclass(InvalidJobActionError, Exception)
        assert issubclass(SchedulingError, Exception)
    
    def test_exceptions_are_distinct_types(self):
        """Test that each exception type is distinct."""
        job_not_found = JobNotFoundError("test")
        invalid_action = InvalidJobActionError("test")
        scheduling_error = SchedulingError("test")
        
        assert type(job_not_found) != type(invalid_action)
        assert type(invalid_action) != type(scheduling_error)
        assert type(job_not_found) != type(scheduling_error)
