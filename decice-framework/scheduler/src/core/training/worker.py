import asyncio

import logging
import traceback
from typing import Any, Dict

from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.db.db import AsyncSessionLocal
from core.features.factory import (create_data_transformer,
                                   create_feature_engineer)
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos
from core.preprocessing.scaler_manager import ScalerManager
from core.schemas import SchedulerDefinition, TrainingRunRequest
from core.training.training_simulator import TrainingSimulator
from repositories.training_repository import TrainingJobRepository
from strategy_loader import StrategyFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainingWorker")


async def _worker_update_status(
    job_id: str, status: str, message: str = None, metrics: dict = None
):
    """Helper to update DB status from within the isolated worker process."""
    try:
        async with AsyncSessionLocal() as session:
            repo = TrainingJobRepository(session)
            # We fetch and update.
            # Note: repository methods should be robust enough to handle re-attaching if needed.
            job = await repo.get(job_id)
            if job:
                job.status = status
                if message:
                    job.error_message = message
                if metrics:
                    job.metrics = metrics
                session.add(job)
                await session.commit()
    except Exception as e:
        logger.error(f"Worker failed to update DB status for {job_id}: {e}")


async def _check_cancellation(job_id: str) -> bool:
    """Checks if the user requested a stop."""
    try:
        async with AsyncSessionLocal() as session:
            repo = TrainingJobRepository(session)
            job = await repo.get(job_id)
            if job and job.status in ("canceling", "canceled"):
                return True
    except Exception:
        pass
    return False


def run_training_task(
    job_id: str, run_request: TrainingRunRequest, model_config_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Entry point for the isolated process.
    """
    # Create a new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    settings = get_settings()
    model_config = SchedulerDefinition(**model_config_dict)

    logger.info(f"Worker {job_id} started. Model: {model_config.name}")

    # Mark as Running
    loop.run_until_complete(_worker_update_status(job_id, "running"))

    try:
        # 1. Paths
        base_model_dir = settings.MODELS_BASE_DIR / model_config.name
        base_model_dir.mkdir(parents=True, exist_ok=True)

        dataset_dir = settings.DATA_BASE_DIR / "datasets" / run_request.dataset_name
        if not dataset_dir.exists():
            raise FileNotFoundError(
                f"Dataset {run_request.dataset_name} not found at {dataset_dir}"
            )

        scalers_path = settings.ALL_SCALERS_FILE_PATH
        if not scalers_path.exists():
            logger.warning(
                f"Scalers not found at {scalers_path}. Starting Auto-Calibration..."
            )
            ScalerManager.fit_and_save_scalers(
                dataset_path=dataset_dir, output_path=scalers_path
            )

        # 2. Initialize Components
        strategy_factory = StrategyFactory(
            strategies_pkg_path=settings.STRATEGIES_PACKAGE_PATH
        )
        kairos = Kairos(strategy_factory_instance=strategy_factory)

        fuzzy_gate = FuzzyStorageResourcesAccessGate(
            cpu_weight=settings.FUZZY_CPU_WEIGHT,
            memory_weight=settings.FUZZY_MEMORY_WEIGHT,
            storage_weight=settings.FUZZY_STORAGE_WEIGHT,
            network_weight=settings.FUZZY_NETWORK_WEIGHT,
            suitability_threshold=settings.FUZZY_THRESHOLD,
        )

        # 3. Initialize AI (Using params from Model Config)
        ai_scheduler = AIScheduler(
            kairos_instance=kairos,
            data_transformer=create_data_transformer(),
            feature_engineer=create_feature_engineer(),
            model_base_dir=base_model_dir,
            actor_lr=model_config.actor_lr,
            critic_lr=model_config.critic_lr,
            gamma=model_config.gamma,
            gae_lambda=model_config.gae_lambda,
            policy_clip=model_config.policy_clip,
            entropy_coefficient=model_config.entropy_coefficient,
            epochs_per_update=settings.AI_EPOCHS_PER_UPDATE,
            ppo_batch_size=model_config.ppo_batch_size,
            replay_buffer_capacity=settings.AI_REPLAY_BUFFER_CAPACITY,
        )

        if run_request.resume_from_checkpoint:
            ai_scheduler.load_models()

        # 4. Initialize Simulator
        simulator = TrainingSimulator(ai_scheduler, kairos, fuzzy_gate)

        # Inject Dataset Path into Simulator (Assuming Simulator is updated to handle this)
        # Or, we can monkey-patch or subclass here if strict code changes aren't possible.
        # For now, we assume TrainingSimulator checks this attribute.
        simulator.dataset_path = dataset_dir

        # 5. Define Cancellation Callback
        async def stop_callback():
            return await _check_cancellation(job_id)

        # 6. Run Loop
        results = loop.run_until_complete(
            simulator.run_training_session(
                cycles=run_request.cycles,
                episodes_per_cycle=run_request.episodes_per_cycle,
                should_stop_callback=stop_callback,
            )
        )

        final_status = results.get("status", "completed")
        message = f"Training finished. Model saved to {base_model_dir}"

        loop.run_until_complete(
            _worker_update_status(job_id, final_status, message, results)
        )

        return {
            "status": final_status,
            "metrics": results,
            "model_path": str(base_model_dir),
        }

    except Exception as e:
        error_msg = f"Training crashed: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        loop.run_until_complete(_worker_update_status(job_id, "failed", error_msg))

        return {"status": "failed", "error": str(e)}
    finally:
        loop.close()
