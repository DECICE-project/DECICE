import uvicorn

from config.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "api:app",
        host=settings.PROMQL_WRAPPER_HOST,
        port=settings.PROMQL_WRAPPER_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
