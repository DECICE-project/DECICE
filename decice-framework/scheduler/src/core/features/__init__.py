import importlib
import logging
import os
import pkgutil

from .registry import FeatureRegistry

logger = logging.getLogger(__name__)

task_feature_registry = FeatureRegistry()
node_feature_registry = FeatureRegistry()
aggregate_feature_registry = FeatureRegistry()


def discover_features():
    """
    Finds and imports all modules in this 'features' package
    to trigger their respective @register() decorators.
    """
    package_path = __path__
    package_name = __name__

    logger.info(f"Starting feature discovery in package: '{package_name}'")
    logger.debug(f"Package paths: {package_path}")

    found_modules = []

    # Force manual import of known modules if pkgutil fails (common in some docker setups)
    known_modules = ["task", "cluster", "aggregate"]

    for mod in known_modules:
        full_name = f"{package_name}.{mod}"
        try:
            importlib.import_module(full_name)
            logger.info(f"Explicitly imported feature module: {full_name}")
            found_modules.append(mod)
        except ImportError as e:
            logger.warning(f"Could not explicitly import {full_name}: {e}")

    # Dynamic discovery
    for _, module_name, ispkg in pkgutil.iter_modules(package_path):
        if module_name in known_modules:
            continue  # Already imported
        if ispkg or module_name in ("__init__", "registry", "interfaces"):
            continue

        full_module_name = f".{module_name}"
        try:
            importlib.import_module(full_module_name, package_name)
            logger.info(f"Dynamically imported feature module: '{module_name}'")
            found_modules.append(module_name)
        except Exception as e:
            logger.error(
                f"Could not import feature module '{module_name}'. Error: {e}",
                exc_info=True,
            )

    logger.info(f"Feature discovery finished. Modules loaded: {found_modules}")

    # Log for debugging
    logger.info(f"Task Features Registered: {task_feature_registry.get_all_names()}")
    logger.info(f"Node Features Registered: {node_feature_registry.get_all_names()}")
