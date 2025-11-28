import importlib
import logging
import pkgutil
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class IStrategy(Protocol):
    """
    Defines the interface that all scheduling strategies must implement.
    """

    def schedule(
        self, jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> dict[str, Optional[str]]:  # Job ID (str) to Node ID (str) or None
        """Schedule jobs on nodes, returning a mapping of job_id to node_id (or None if unallocated)."""
        ...

    # Preferred method for Kairos to call for efficiency
    def calculate_throughput_from_allocations(
        self,
        allocations: dict[str, Optional[str]],
        jobs: list[dict[str, Any]],
        nodes: list[dict[str, Any]],
    ) -> float:
        """
        Calculate throughput based on prior allocations.
        This method is preferred by Kairos to avoid re-running schedule().
        """
        # Default implementation if a strategy doesn't provide this explicitly but has the old one.
        # However, FunctionStrategyAdapter will handle this based on what the module offers.
        # If this method is called on an object that only has calculate_throughput,
        # it implies calculate_throughput might be called by an adapter or Kairos.
        # For direct class implementations, if this isn't overridden, it should signal an issue
        # if only calculate_throughput (the one that re-schedules) is available.
        # A concrete strategy should implement this or Kairos should fallback gracefully.
        logger.warning(
            f"Strategy {self.__class__.__name__} using default/unoptimized throughput calculation from allocations."
        )
        if not allocations:
            return 0.0
        return float(sum(1 for node_id in allocations.values() if node_id is not None))

    def calculate_throughput(
        self, jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> float:
        """
        Calculate throughput. This method might re-run scheduling if not optimized
        or if calculate_throughput_from_allocations is not implemented/called.
        """
        # This method primarily serves as a fallback or for strategies
        # that haven't been updated to use calculate_throughput_from_allocations.
        # Individual strategy modules will provide their own implementation.
        # The adapter will call what's available in the wrapped module.
        ...


class FunctionStrategyAdapter:
    """
    Adapter to wrap a strategy module that provides standalone functions (schedule, calculate_throughput)
    and make it conform to the IStrategy interface.
    """

    def __init__(self, module: Any, module_name: str) -> None:
        self.module = module
        self.module_name = module_name
        if not hasattr(module, "schedule"):
            raise AttributeError(
                f"Strategy module {module_name} must have a 'schedule' function."
            )
        # Throughput calculation is optional but preferred
        if not hasattr(module, "calculate_throughput") and not hasattr(
            module, "calculate_throughput_from_allocations"
        ):
            logger.warning(
                f"Strategy module {module_name} has no 'calculate_throughput' or 'calculate_throughput_from_allocations' function."
            )

    def schedule(
        self, jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> dict[str, Optional[str]]:
        return self.module.schedule(jobs, nodes)

    def calculate_throughput_from_allocations(
        self,
        allocations: dict[str, Optional[str]],
        jobs: list[dict[str, Any]],
        nodes: list[dict[str, Any]],
    ) -> float:
        # If the adapted module has the optimized version, use it
        if hasattr(self.module, "calculate_throughput_from_allocations"):
            return self.module.calculate_throughput_from_allocations(
                allocations, jobs, nodes
            )
        # Otherwise, if it has the old one, call that (it will re-schedule)
        elif hasattr(self.module, "calculate_throughput"):
            logger.debug(
                f"Adapter for {self.module_name} falling back to calculate_throughput (may re-schedule)."
            )
            return self.module.calculate_throughput(jobs, nodes)
        logger.warning(
            f"Adapter for {self.module_name}: No suitable throughput method found. Returning 0.0."
        )
        return 0.0

    def calculate_throughput(
        self, jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> float:
        if hasattr(self.module, "calculate_throughput"):
            return self.module.calculate_throughput(jobs, nodes)
        # If only the optimized one exists, we can't directly call it without allocations.
        # This situation implies Kairos should have used calculate_throughput_from_allocations.
        # For direct calls to this method on the adapter when only the optimized one exists,
        # it means the original scheduling must happen.
        elif hasattr(self.module, "calculate_throughput_from_allocations"):
            logger.debug(
                f"Adapter for {self.module_name} re-scheduling to use calculate_throughput_from_allocations via fallback."
            )
            allocs = self.schedule(jobs, nodes)  # Re-schedule to get allocations
            return self.module.calculate_throughput_from_allocations(
                allocs, jobs, nodes
            )
        logger.warning(
            f"Adapter for {self.module_name}: No calculate_throughput method found. Returning 0.0."
        )
        return 0.0


class StrategyFactory:
    """
    StrategyFactory dynamically discovers and loads all strategy modules from the specified package.
    It uses pkgutil.iter_modules to scan the package and imports each module.
    If a module defines a 'Strategy' class conforming to IStrategy, it's instantiated.
    Otherwise, module-level 'schedule' and 'calculate_throughput' functions are wrapped.
    """

    def __init__(self, strategies_pkg_path: str = "strategies") -> None:
        self.strategies_pkg_path = strategies_pkg_path
        self._registry: dict[str, IStrategy] = {}
        self._load_strategies()

    def _load_strategies(self) -> None:
        try:
            package = importlib.import_module(self.strategies_pkg_path)
            logger.info(
                f"Loading strategies from package: '{self.strategies_pkg_path}' using path: {package.__path__}"
            )
        except ImportError:
            logger.error(
                f"Could not import strategies package: '{self.strategies_pkg_path}'. Is it a valid package with __init__.py and in PYTHONPATH?"
            )
            return

        for finder, module_name_suffix, ispkg in pkgutil.iter_modules(
            package.__path__, package.__name__ + "."
        ):
            if ispkg:  # Skip sub-packages for now, unless strategies are nested
                continue

            try:
                module = importlib.import_module(module_name_suffix)
                # Use the final part of the module name as the strategy's registered name
                strategy_key_name = module_name_suffix.split(".")[-1]

                if strategy_key_name.startswith(
                    "_"
                ):  # Skip private/utility modules like __init__ or list_strategies__
                    logger.debug(f"Skipping module: {module_name_suffix}")
                    continue

                if hasattr(module, "Strategy") and isinstance(
                    getattr(module, "Strategy")(), IStrategy
                ):
                    self._registry[strategy_key_name] = module.Strategy()
                    logger.info(
                        f"Registered class-based strategy: '{strategy_key_name}' from module {module_name_suffix}"
                    )
                elif hasattr(module, "schedule"):  # Check for function-based strategy
                    self._registry[strategy_key_name] = FunctionStrategyAdapter(
                        module, module_name_suffix
                    )
                    logger.info(
                        f"Registered function-based strategy (via adapter): '{strategy_key_name}' from module {module_name_suffix}"
                    )
                else:
                    logger.warning(
                        f"Module {module_name_suffix} does not conform to IStrategy (no 'Strategy' class or 'schedule' function). Skipping."
                    )
            except Exception as e:
                logger.error(
                    f"Failed to load or register strategy from module {module_name_suffix}: {e}",
                    exc_info=True,
                )

    def get_strategy(self, name: str) -> Optional[IStrategy]:
        strategy_instance = self._registry.get(name)
        if not strategy_instance:
            logger.warning(
                f"Strategy '{name}' not found in registry. Available: {list(self._registry.keys())}"
            )
        return strategy_instance

    def list_strategies(self) -> list[str]:
        return list(self._registry.keys())
