import logging

import uvicorn

from config.config import get_settings

logger = logging.getLogger(__name__)


def main():
    settings = get_settings()
    logger.info(
        f"Starting Uvicorn server on host: {settings.SCHEDULER_HOST}, port: {settings.SCHEDULER_PORT}"
    )
    logger.info(f"Application environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level set to: {settings.LOG_LEVEL.value}")

    app_module = "api.api:app"

    uvicorn.run(
        app_module,
        host=settings.SCHEDULER_HOST,
        port=settings.SCHEDULER_PORT,
        log_level=settings.LOG_LEVEL.value.lower(),
    )


if __name__ == "__main__":
    main()
