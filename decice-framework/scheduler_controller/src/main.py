import uvicorn

from config.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "api:app",
        host=settings.SC_HOST,
        port=settings.SC_PORT,
    )
