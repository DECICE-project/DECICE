import asyncio
import logging
import json
import traceback
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.db.db import AsyncSessionLocal
from core.features.factory import create_data_transformer, create_feature_engineer
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos
from core.schemas import ScheduleRequest
from repositories.evaluation_repository import EvaluationJobRepository
from strategy_loader import StrategyFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EvaluationWorker")


async def _update_db(job_id: str, status: str, metrics: dict = None, error: str = None):
    try:
        async with AsyncSessionLocal() as session:
            repo = EvaluationJobRepository(session)
            await repo.update_results(job_id, status, metrics, error)
    except Exception as e:
        logger.error(f"Failed to update eval job {job_id}: {e}")


def run_evaluation_task(job_id: str, scheduler_name: str, dataset_name: str):
    """
    Isolated process to benchmark a model against a dataset.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    settings = get_settings()

    logger.info(
        f"Eval Worker {job_id} started. Model: {scheduler_name} vs Data: {dataset_name}"
    )
    loop.run_until_complete(_update_db(job_id, "running"))

    try:
        # Paths
        model_path = settings.MODELS_BASE_DIR / scheduler_name
        dataset_path = settings.DATA_BASE_DIR / "datasets" / dataset_name

        if not model_path.exists():
            raise FileNotFoundError(f"Model {scheduler_name} not found")
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset {dataset_name} not found")

        # Init Components
        strategy_factory = StrategyFactory(settings.STRATEGIES_PACKAGE_PATH)
        kairos = Kairos(strategy_factory)

        # Load Scalers (Essential for valid evaluation)
        if not settings.ALL_SCALERS_FILE_PATH.exists():
            raise RuntimeError("Scalers file missing. Cannot evaluate model.")

        feature_engineer = create_feature_engineer(settings.ALL_SCALERS_FILE_PATH)
        transformer = create_data_transformer()

        # Load AI
        # We assume hyperparameters (LR, etc.) don't matter for *Inference*,
        # so we use defaults, but we MUST load the weights.
        ai_scheduler = AIScheduler(
            kairos_instance=kairos,
            data_transformer=transformer,
            feature_engineer=feature_engineer,
            model_base_dir=model_path,
        )

        # Force weight loading (AIScheduler init does this, but double check)
        if not ai_scheduler.load_models():
            raise RuntimeError("Failed to load model weights.")

        # Evaluation Loop
        scenarios = list(dataset_path.glob("*.json"))
        results = []

        fuzzy_gate = FuzzyStorageResourcesAccessGate(
            cpu_weight=settings.FUZZY_CPU_WEIGHT,
            memory_weight=settings.FUZZY_MEMORY_WEIGHT,
            storage_weight=settings.FUZZY_STORAGE_WEIGHT,
            network_weight=settings.FUZZY_NETWORK_WEIGHT,
            suitability_threshold=settings.FUZZY_THRESHOLD,
        )

        for sc_file in scenarios:
            try:
                with open(sc_file, "r") as f:
                    data = json.load(f)
                req = ScheduleRequest(**data)

                # A. Transform & Fuzzy Gate
                tasks_df, nodes_df, _ = transformer.transform(req)
                tasks_dicts = tasks_df.fillna(0).to_dict(orient="records")
                nodes_dicts = nodes_df.fillna(0).to_dict(orient="records")

                suitable = fuzzy_gate.determine_suitable_nodes(tasks_dicts, nodes_dicts)
                for t in tasks_dicts:
                    t["suitable_node_ids"] = suitable.get(str(t.get("task_id")), [])

                # B. AI Prediction
                ai_choice = ai_scheduler.predict_best_strategy_name(
                    req, deterministic=True
                )
                if not ai_choice:
                    ai_choice = "round_robin"  # Fallback

                # C. Oracle Calculation (Run ALL strategies)
                perfs = kairos.evaluate_all_strategies(tasks_dicts, nodes_dicts)

                # Find Best Reward
                best_reward = -float("inf")
                best_strat = None
                ai_reward = -float("inf")

                for strat, runtime, thru in perfs:
                    # Use AI Scheduler's own reward function for consistency
                    r = ai_scheduler.calculate_reward(runtime, thru or 0.0)
                    if r > best_reward:
                        best_reward = r
                        best_strat = strat

                    if strat == ai_choice:
                        ai_reward = r

                results.append(
                    {
                        "file": sc_file.name,
                        "ai_choice": ai_choice,
                        "oracle_choice": best_strat,
                        "ai_reward": ai_reward,
                        "best_reward": best_reward,
                        "regret": best_reward - ai_reward,
                        "is_optimal": (ai_choice == best_strat),
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to evaluate {sc_file.name}: {e}")

        # Aggregate Metrics
        df = pd.DataFrame(results)
        if df.empty:
            raise RuntimeError("No valid results generated.")

        metrics = {
            "optimality_rate": float(df["is_optimal"].mean()),
            "avg_regret": float(df["regret"].mean()),
            "avg_ai_reward": float(df["ai_reward"].mean()),
            "details": {
                "total_scenarios": len(df),
                "strategy_distribution": df["ai_choice"].value_counts().to_dict(),
            },
        }

        loop.run_until_complete(_update_db(job_id, "completed", metrics))

    except Exception as e:
        logger.error(traceback.format_exc())
        loop.run_until_complete(_update_db(job_id, "failed", error=str(e)))
    finally:
        loop.close()
