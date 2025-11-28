from fastapi import Request

from core.ai_scheduler import AIScheduler
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos


def get_ai_scheduler(request: Request) -> AIScheduler:
    """Dependency provider to get the singleton AIScheduler instance."""
    instance = getattr(request.app.state, "ai_scheduler_instance", None)
    if not instance:
        raise RuntimeError("AIScheduler instance not initialized in app.state")
    return instance


def get_kairos(request: Request) -> Kairos:
    instance = getattr(request.app.state, "kairos_instance", None)
    if not instance:
        raise RuntimeError("Kairos instance not initialized")
    return instance


def get_fuzzy_gate(request: Request) -> FuzzyStorageResourcesAccessGate:
    instance = getattr(request.app.state, "fuzzy_gate_instance", None)
    if not instance:
        raise RuntimeError("FuzzyGate instance not initialized")
    return instance
