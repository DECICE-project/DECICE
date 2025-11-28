import inspect
from typing import Callable, Type

from .interfaces import IFeatureExtractor


class FeatureRegistry:
    """
    Holds a registry mapping feature names to their extractor *classes*.
    This mechanism is generic and reusable.
    """

    def __init__(self):
        self._registry: dict[str, Type[IFeatureExtractor]] = {}

    def register(self) -> Callable[[Type[IFeatureExtractor]], Type[IFeatureExtractor]]:
        """A decorator factory that registers an extractor class."""

        def decorator(cls: Type[IFeatureExtractor]) -> Type[IFeatureExtractor]:
            if inspect.isabstract(cls):
                return cls
            if not issubclass(cls, IFeatureExtractor):
                raise TypeError(
                    f"Class {cls.__name__} must inherit from IFeatureExtractor"
                )
            name = getattr(cls, "name", None)
            if not name:
                raise ValueError(
                    f"Extractor class {cls.__name__} must define a 'name' class attribute."
                )
            if name in self._registry:
                raise ValueError(f"Feature name '{name}' is already registered.")
            self._registry[name] = cls
            return cls

        return decorator

    def get_extractor_class(self, name: str) -> Type[IFeatureExtractor]:
        cls = self._registry.get(name)
        if cls is None:
            raise KeyError(f"No feature registered with name: '{name}'")
        return cls

    def get_all_names(self) -> list[str]:
        return sorted(list(self._registry.keys()))
