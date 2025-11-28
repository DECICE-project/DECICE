import uvicorn

from api.api import create_app
from config.config import get_settings
from config.setup_logging import setup_opentelemetry_logging

app = create_app()


def main():
    settings = get_settings()
    setup_opentelemetry_logging(settings=settings)

    uvicorn.run(
        "main:app",
        host=settings.CM_HOST,
        port=settings.CM_PORT,
        log_config=None,
        reload=settings.ENVIRONMENT == "local",
    )


if __name__ == "__main__":
    main()
