# file: repository/job_repository.py

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

# Import the database ORM model
from .models import Job as JobModel

# We need a business domain model to return from the repository.
# For now, let's assume it exists in the business layer. We'll import it.
# This business object is what the rest of our application will work with.
from services.domain_models import Job  # This is a placeholder for the business object


class JobRepository:
    """
    The Job Repository class provides an interface to the jobs data storage.
    It encapsulates all the database access logic, following the Repository Pattern.
    """

    def __init__(self, session: Session):
        """
        Initializes the repository with a database session.
        Dependencies (the session) are injected.
        """
        self.session = session

    def _map_to_domain_object(self, job_model: JobModel) -> Job:
        """
        A private helper to convert the SQLAlchemy ORM model to a business domain object.
        This ensures the rest of the application is decoupled from the database schema.
        """
        job_data = job_model.to_dict()
        return Job(**job_data)

    def add(
        self, name: str, image: str, scheduler_target: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Adds a new Job record to the database session.
        It does NOT commit the transaction.

        Args:
            name (str): The name of the job.
            image (str): The container image for the job.
            scheduler_target (str): The target cluster type.
            user_id (str): The ID of the user submitting the job.

        Returns:
            Dict[str, Any]: The newly created Job as a dictionary.
        """
        # Create an instance of the SQLAlchemy ORM model
        new_job_model = JobModel(
            name=name, image=image, target_cluster=scheduler_target, user_id=user_id
        )
        self.session.add(new_job_model)
        self.session.flush()  # Flush to get DB-generated values like ID, timestamps
        return new_job_model.to_dict()

    def get(self, job_id: UUID, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single Job by its ID and owner.

        Args:
            job_id (UUID): The unique ID of the job.
            user_id (str): The ID of the user who owns the job.

        Returns:
            Optional[Dict[str, Any]]: The Job as a dictionary if found, otherwise None.
        """
        job_model = (
            self.session.query(JobModel).filter_by(id=job_id, user_id=user_id).first()
        )

        if job_model:
            return job_model.to_dict()
        return None

    def list(
        self,
        user_id: str,
        limit: int,
        offset: int,
        status: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves a list of Jobs, filtered by user and other optional criteria.

        Args:
            user_id (str): The ID of the user whose jobs to list.
            limit (int): The maximum number of jobs to return.
            offset (int): The number of jobs to skip.
            status (Optional[str]): Optional filter for job status.
            name (Optional[str]): Optional filter for job name (substring match).

        Returns:
            List[Dict[str, Any]]: A list of Job dictionaries.
        """
        query = self.session.query(JobModel).filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)

        if name:
            query = query.filter(
                JobModel.name.ilike(f"%{name}%")
            )  # Case-insensitive substring match

        job_models = (
            query.order_by(JobModel.creation_timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [job.to_dict() for job in job_models]

    def update(
        self, job_id: UUID, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Updates a job with new data.

        Args:
            job_id (UUID): The unique ID of the job.
            user_id (str): The ID of the user who owns the job.
            update_data (Dict[str, Any]): Dictionary of fields to update.

        Returns:
            Optional[Dict[str, Any]]: The updated Job as a dictionary if found, otherwise None.
        """
        job_model = (
            self.session.query(JobModel).filter_by(id=job_id, user_id=user_id).first()
        )

        if job_model:
            for key, value in update_data.items():
                if hasattr(job_model, key):
                    setattr(job_model, key, value)
            self.session.flush()
            return job_model.to_dict()
        return None

    def count(
        self, user_id: str, status: Optional[str] = None, name: Optional[str] = None
    ) -> int:
        """
        Counts the number of jobs matching the filter criteria for a user.
        This is useful for pagination.
        """
        query = self.session.query(func.count(JobModel.id)).filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)

        if name:
            query = query.filter(JobModel.name.ilike(f"%{name}%"))

        return query.scalar()
