# file: tests/unit/test_data_layer.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from datetime import datetime

# Import components from the Data Layer
from repository.models import Base, Job as JobModel
from repository.job_repository import JobRepository
from sqlalchemy import func

# Setup an in-memory SQLite database for testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Fixture to create a new database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_add_and_get_job(db_session: Session):
    """
    Unit test for the JobRepository.
    Tests the 'add' and 'get' methods in isolation.
    """
    repo = JobRepository(session=db_session)
    user_id = "unit-test-user"
    
    # 1. Test adding a job
    added_job = repo.add(
        name="test_job_1",
        image="test_image:v1",
        scheduler_target="VOLCANO",
        user_id=user_id
    )
    db_session.commit() # Commit to save the record

    assert added_job.name == "test_job_1"
    job_id = added_job.jobId

    # 2. Test getting the job
    retrieved_job = repo.get(job_id=job_id, user_id=user_id)
    assert retrieved_job is not None
    assert retrieved_job.jobId == job_id
    assert retrieved_job.name == "test_job_1"

# Add more tests for list(), count(), update(), etc.