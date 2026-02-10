# file: repository/models.py

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    func,
    String,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

# --- Base Model ---
# All ORM models will inherit from this base class.
Base = declarative_base()


# --- Custom UUID Type for Database Agnosticism ---
class UUID_CHAR(TypeDecorator):
    """
    Platform-independent UUID type.
    Uses PostgreSQL's native UUID type, and a CHAR(32) for other backends.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


# --- Enumerations for Database Columns ---
# These enums provide data integrity at the database level.
class ClusterTypeEnum(enum.Enum):
    VOLCANO = "VOLCANO"
    INTERLINK_SLURM = "INTERLINK_SLURM"


class JobStateEnum(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


# --- SQLAlchemy ORM Model for a Job ---
class Job(Base):
    """
    SQLAlchemy model representing a Job record in the database.
    This table stores the state of jobs submitted to the meta-scheduler.
    """

    __tablename__ = "jobs"

    # --- Table Columns ---
    id = Column(UUID_CHAR, primary_key=True, default=uuid.uuid4)

    # The user ID from the JWT 'sub' claim, used for ownership.
    user_id = Column(String, nullable=False, index=True)

    name = Column(String, nullable=False)

    # The name of the Kubernetes "Manager Pod" that oversees this job's lifecycle.
    manager_pod_name = Column(String, nullable=True, unique=True)

    # The cluster type where the job is scheduled to run.
    target_cluster = Column(SQLAlchemyEnum(ClusterTypeEnum), nullable=False)

    # The current execution status of the job.
    status = Column(
        SQLAlchemyEnum(JobStateEnum), nullable=False, default=JobStateEnum.PENDING
    )

    # The container image used for the job.
    image = Column(String, nullable=False)

    # Timestamps are managed by the database server for reliability.
    creation_timestamp = Column(DateTime, nullable=False, server_default=func.now())
    last_update_timestamp = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        """
        Converts the SQLAlchemy model instance into a dictionary.
        This facilitates decoupling the database layer from the API schema layer.
        """
        return {
            "jobId": self.id,
            "name": self.name,
            "status": self.status,
            "targetCluster": self.target_cluster,
            "creationTimestamp": self.creation_timestamp,
            "userId": self.user_id,
        }
