from watmon_exporter.metrics import POST_VERTEXPOOLS_REQUEST_COUNT
from watmon_exporter.schema import VertexpoolsPost
from watmon_exporter.core import Exporter
from fastapi import FastAPI
from prometheus_client import make_asgi_app
import os

nodename = os.environ.get("NODENAME")
exporter = Exporter(nodename)
app = FastAPI(docs_url="/", title="Network Exporter")
metrics_app = make_asgi_app()
app.mount("/metrics/", metrics_app)


@app.post("/vertexpools/")
async def update_vertex_pool(vertex_pool: VertexpoolsPost):
    POST_VERTEXPOOLS_REQUEST_COUNT.labels(nodename).inc()
    exporter.update_vertexpools(vertex_pool)
    return {
        "message": "VertexPool updated successfully",
        "data:": vertex_pool.model_dump(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7987)
