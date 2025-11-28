from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TrainingDataset(Base):
    __tablename__ = "training_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Metadata
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    job_min: Mapped[int] = mapped_column(Integer, default=0)
    job_max: Mapped[int] = mapped_column(Integer, default=0)

    # Storage details
    # If S3/MinIO: "s3://my-bucket/datasets/v1/"
    # If Local: "/app/data/datasets/v1/"
    path: Mapped[str] = mapped_column(String)
    storage_type: Mapped[str] = mapped_column(
        String, default="local"
    )  # "local" or "s3"

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    scheduler_name: Mapped[str] = mapped_column(String)
    dataset_name: Mapped[str] = mapped_column(String)

    # Status: queued, running, canceling, canceled, completed, failed
    status: Mapped[str] = mapped_column(String, default="queued")

    current_cycle: Mapped[int] = mapped_column(Integer, default=0)
    total_cycles: Mapped[int] = mapped_column(Integer)

    # Metrics (JSON blob for accuracy/reward logs)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class EvaluationJob(Base):
    __tablename__ = "evaluation_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Inputs
    scheduler_name: Mapped[str] = mapped_column(String) # The Model being tested
    dataset_name: Mapped[str] = mapped_column(String)   # The Test Set
    
    # Status
    status: Mapped[str] = mapped_column(String, default="queued")
    
    # Results (The Report Card)
    optimality_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_regret: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_ai_reward: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Detailed JSON report (per-scenario breakdown if needed)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)