import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.db import db as db_module
from core.db.models import Base
from core.features.factory import create_data_transformer, create_feature_engineer
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos
from strategy_loader import StrategyFactory

from .data import data_router
from .models import models_router
from .root import root_router
from .scheduling import schedule_router
from .training import training_router
from .evaluation import evaluation_router

settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL.value,
    format="%(asctime)s - %(levelname)s - %(name)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initializes and stores heavyweight, singleton components (like AI models and
    strategy factories) on app.state at application startup. This ensures they
    are created only once, saving memory and startup time for each request.
    """
    logger.info(f"AI Scheduler API starting up in '{settings.ENVIRONMENT}' mode...")
    app.state.settings = settings
    app.state.startup_healthy = False

    # Use SQLite for now, but ready for Postgres
    # DATABASE_URL = "postgresql://user:password@localhost/dbname"
    DATABASE_URL = f"sqlite+aiosqlite:///{settings.DATA_BASE_DIR}/scheduler.db"
    logger.info("Creating database engine", extra={"db.url": str(DATABASE_URL)})
    db_module.engine = create_async_engine(DATABASE_URL)

    logger.info("Creating async session maker")
    session_factory = async_sessionmaker(bind=db_module.engine, expire_on_commit=False)
    app.state.db_session_factory = session_factory
    logger.info("Async session maker setup complete")

    # TODO: For production,use a migration tool like Alembic.
    # For testing and development, this creates the schema.
    logger.info("Connecting to DB to create tables")
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")

    try:
        # Initialize and store singleton components
        strategy_factory = StrategyFactory(
            strategies_pkg_path=settings.STRATEGIES_PACKAGE_PATH
        )
        app.state.kairos_instance = Kairos(strategy_factory_instance=strategy_factory)

        app.state.fuzzy_gate_instance = FuzzyStorageResourcesAccessGate(
            cpu_weight=settings.FUZZY_CPU_WEIGHT,
            memory_weight=settings.FUZZY_MEMORY_WEIGHT,
            storage_weight=settings.FUZZY_STORAGE_WEIGHT,
            network_weight=settings.FUZZY_NETWORK_WEIGHT,
            suitability_threshold=settings.FUZZY_THRESHOLD,
        )

        app.state.ai_scheduler_instance = AIScheduler(
            kairos_instance=app.state.kairos_instance,
            data_transformer=create_data_transformer(),
            feature_engineer=create_feature_engineer(),
            actor_lr=settings.AI_ACTOR_LR,
            critic_lr=settings.AI_CRITIC_LR,
            gamma=settings.AI_GAMMA,
            gae_lambda=settings.AI_GAE_LAMBDA,
            policy_clip=settings.AI_POLICY_CLIP,
            entropy_coefficient=settings.AI_ENTROPY_COEFFICIENT,
            epochs_per_update=settings.AI_EPOCHS_PER_UPDATE,
            ppo_batch_size=settings.AI_PPO_BATCH_SIZE,
            replay_buffer_capacity=settings.AI_REPLAY_BUFFER_CAPACITY,
        )

        app.state.startup_healthy = True
        logger.info("Application startup complete. All core components initialized.")
    except Exception as e:
        logger.critical(
            f"A critical error occurred during application startup: {e}", exc_info=True
        )
        # startup_healthy remains False
        raise

    yield

    logger.info("Application shutdown complete.")


# FastAPI Application Initialization
app = FastAPI(
    title="AI Scheduler API",
    description="An API for scheduling jobs on nodes using AI-driven strategy selection.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(schedule_router, tags=["schedule"])
app.include_router(training_router, tags=["training"])
app.include_router(models_router, tags=["model registry"])
app.include_router(data_router, tags=["data management"])
app.include_router(evaluation_router, tags=["evaluation"])
app.include_router(root_router)
