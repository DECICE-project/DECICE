"""
This module runs a FastAPI HTTP server to manage metric data.

"""

from copy import deepcopy
from fastapi import FastAPI
import uvicorn

# from core_model_router import router as model_router
from digital_twin.api.v1 import router as v1_router
from digital_twin.api.v2 import router as v2_router
from digital_twin.config.config import service_settings

app = FastAPI(docs_url="/", title="Digital-Twin API", version="0.2.0")

# API version v1
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

# API version v2
app.include_router(v2_router, prefix="/api/v2", tags=["v2"])

# API version default (v1)
v1_router_copy = deepcopy(v1_router)
app.include_router(v1_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=service_settings.host,
        port=service_settings.port,
    )
