import logging
from typing import Type

from .base import AbstractWorkflowParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """A registry for all concrete workflow parser classes."""

    _parsers: list[Type[AbstractWorkflowParser]] = []

    @classmethod
    def register(cls, parser_class: Type[AbstractWorkflowParser]):
        """A class decorator to register a new parser."""
        if not issubclass(parser_class, AbstractWorkflowParser):
            raise TypeError(
                f"{parser_class.__name__} must inherit from AbstractWorkflowParser."
            )
        logger.debug(f"Registering parser: {parser_class.__name__}")
        cls._parsers.append(parser_class)
        return parser_class

    @classmethod
    def get_parsers(cls) -> list[Type[AbstractWorkflowParser]]:
        """Returns the list of registered parser classes."""
        return cls._parsers
