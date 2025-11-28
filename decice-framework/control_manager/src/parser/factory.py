import logging

from . import argo_parser, k8s_parser, slurm_parser, snakemake_parser
from .base import AbstractWorkflowParser
from .registry import ParserRegistry

logger = logging.getLogger(__name__)


def get_parser(filename: str, file_content: bytes) -> AbstractWorkflowParser:
    """
    The parser factory. It iterates through the registry to find a suitable
    parser that can handle the given file.
    """
    logger.debug(f"Attempting to find a parser for file: {filename}")
    for parser_class in ParserRegistry.get_parsers():
        try:
            if parser_class.can_parse(filename, file_content):
                logger.info(
                    f"Found suitable parser for '{filename}': {parser_class.__name__}"
                )
                return parser_class()
        except Exception:
            logger.warning(
                f"Parser '{parser_class.__name__}' failed during can_parse check.",
                exc_info=True,
            )
            continue

    logger.error(f"No suitable parser found for file: {filename}")
    raise ValueError(f"Unsupported file type or format for {filename}")
