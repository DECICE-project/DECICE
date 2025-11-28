# file: repository/unit_of_work.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

# Import our repository class
from .job_repository import JobRepository

class UnitOfWork:
    """
    A context manager that provides a transactional scope around a series of operations.
    It handles session management, transaction commit/rollback, and repository instantiation.
    This pattern ensures that a group of operations runs as a single atomic unit.
    """

    def __init__(self):
        """
        Initializes the Unit of Work by creating a session factory.
        The database URL is retrieved from an environment variable for flexibility.
        """
        # In a real application, you'd have better config management.
        # Defaulting to a local SQLite DB for development if the env var is not set.
        db_url = os.getenv("DATABASE_URL", "sqlite:///./database.db")
        
        self.session_factory = sessionmaker(
            bind=create_engine(db_url)
        )
        self.session: Session = None

    def __enter__(self):
        """
        Called when entering the 'with' statement.
        Creates a new database session and instantiates repositories.
        """
        self.session = self.session_factory()
        
        # Instantiate all repositories that are part of this unit of work.
        # The repositories will share the same database session.
        self.jobs = JobRepository(self.session)
        
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        """
        Called when exiting the 'with' statement.
        It handles transaction rollback in case of an error and ensures
        the session is always closed.
        """
        if exc_type:
            # If an exception occurred, roll back the transaction.
            self.rollback()
        
        # Always close the session to release the connection.
        self.session.close()

    def commit(self):
        """
        Commits the current transaction.
        All changes made within the session are persisted to the database.
        """
        self.session.commit()

    def rollback(self):
        """
        Rolls back the current transaction.
        All changes made within the session are discarded.
        """
        self.session.rollback()