import asyncio
import time
from logging import getLogger

from fastapi import Depends

from clients.digital_twin import DigitalTwinClient, get_digital_twin_client
from config.config import get_settings
from models.models import DeciceDigitalTwin
from prometheus.prom_service import (
    CLusterInfoService,
    LinkService,
    NodeService,
    VertexPoolService,
)

logger = getLogger(__name__)


class SnapshotService:
    """Orchestrates the creation of a Digital Twin snapshot and posts it."""

    def __init__(self, dt_client: DigitalTwinClient):
        self.dt_client = dt_client
        self.settings = get_settings()
        self.prometheus_url = str(self.settings.PROMETHEUS_BASE_URL)
        logger.info(
            f"SnapshotService initialized to connect to Prometheus at {self.prometheus_url}"
        )

    async def create_and_post_snapshot(self):
        """
        Extracts data from Prometheus, transforms it into the Digital Twin model,
        and posts it to the Digital Twin service.
        """
        # Overall timer for the entire operation for performance monitoring.
        overall_start_time = time.perf_counter()
        logger.info("Starting new Digital Twin snapshot creation process...")

        try:
            # fetch data
            nodes = NodeService(self.prometheus_url)
            vp_service = VertexPoolService(self.prometheus_url, nodes=nodes)
            link_service = LinkService(self.prometheus_url)
            cluster_info_service = CLusterInfoService(self.prometheus_url)

            logger.debug("Beginning parallel data fetch from Prometheus...")
            fetch_start_time = time.perf_counter()
            await asyncio.gather(
                nodes.pull_metrics(),
                vp_service.fetch_metrics(),
                link_service.fetch_metrics(),
                cluster_info_service.fetch_cluster_info(),
            )
            fetch_duration = (time.perf_counter() - fetch_start_time) * 1000
            logger.debug(f"Prometheus data fetch completed in {fetch_duration:.2f} ms.")

            # process data
            logger.debug("Processing raw metrics into Digital Twin model...")
            vertexpools = list(vp_service.finalize_vertexpools())
            links = link_service.process()
            cluster_info = cluster_info_service.process()
            logger.debug(
                f"Processed {len(vertexpools)} vertexpools and {len(links)} links."
            )

            digital_twin_snapshot = DeciceDigitalTwin(
                lastUpdated=time.time(),
                vertexpools=vertexpools,
                links=links,
                cluster_info=cluster_info,
            )

            # data posting
            logger.debug("Posting complete snapshot to Digital Twin service...")
            post_start_time = time.perf_counter()
            await self.dt_client.post_model_core(digital_twin_snapshot)
            post_duration = (time.perf_counter() - post_start_time) * 1000
            logger.debug(f"POST to Digital Twin service took {post_duration:.2f} ms.")

            overall_duration = (time.perf_counter() - overall_start_time) * 1000
            logger.info(
                f"Snapshot created and posted successfully. "
                f"Vertexpools: {len(vertexpools)}, Links: {len(links)}. "
                f"Total time: {overall_duration:.2f} ms."
            )

        except Exception:
            logger.exception(
                "A failure occurred during the snapshot creation and posting process."
            )
            raise


# Dependency Provider Function
def get_snapshot_service(
    dt_client: DigitalTwinClient = Depends(get_digital_twin_client),
) -> SnapshotService:
    return SnapshotService(dt_client=dt_client)
