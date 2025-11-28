from abc import ABC, abstractmethod

from db.models import Workflow


class AbstractWorkflowParser(ABC):
    """
    Abstract base class for all workflow parsers.

    A concrete parser must implement two methods:
    - can_parse: A class method to quickly determine if the parser can handle a file.
    - parse: The main method to perform the detailed parsing logic.
    """

    @classmethod
    @abstractmethod
    def can_parse(cls, filename: str, file_content: bytes) -> bool:
        """
        A class method that returns True if this parser is capable of parsing
        the given file, based on its name or content.
        """
        pass

    @abstractmethod
    def parse(self, file_content_bytes: bytes, filename: str) -> Workflow:
        """
        Parses the raw file content into the canonical Workflow object,
        including all its WorkflowTask children.
        """
        pass
