import uvicorn

from config import get_settings


def main():
    settings = get_settings()

    uvicorn.run(
        "api:app",
        host=settings.PSGC_HOST,
        port=settings.PSGC_PORT,
        log_level="debug",
        reload=False,
    )


if __name__ == "__main__":
    main()
