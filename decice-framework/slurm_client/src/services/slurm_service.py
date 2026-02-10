import httpx
from fastapi import Depends

from config.settings import get_settings
from core.dependencies import get_http_client
from schemas.accounts import AccountCPUHourQuota
from schemas.jobs import (
    SlurmJobSpec,
    SlurmJobSubmitRequest,
    SlurmJobSubmitResponse,
    SlurmResponse,
)
from schemas.tres import TRES
from schemas.users import UserAccountingResponse


class SlurmService:
    def __init__(self, slurm_api: str, slurm_db_api: str, client: httpx.AsyncClient):
        self.slurm_api_url = slurm_api
        self.slurm_db_api_url = slurm_db_api
        self.client = client

    async def submit_job(
        self,
        username: str,
        token: str,
        script_content: str,
        job_name: str,
        work_dir: str,
    ) -> SlurmJobSubmitResponse:
        """
        Builds the Slurm job request from raw data and submits it.
        """
        job_spec = SlurmJobSpec(
            script=script_content,
            name=job_name,
            current_working_directory=work_dir,
            environment=[f"USER={username}"],
        )

        job_request = SlurmJobSubmitRequest(jobs=[job_spec])
        headers = {
            "X-SLURM-USER-NAME": username,
            "X-SLURM-USER-TOKEN": token,
            "Content-Type": "application/json",
        }
        url = f"{self.slurm_api_url}/job/submit"
        response = await self.client.post(
            url, headers=headers, json=job_request.model_dump()
        )
        response.raise_for_status()
        data = response.json()
        return SlurmJobSubmitResponse(**data)

    async def get_account_cpu_hour_quota(
        self, account_name: str, token: str
    ) -> AccountCPUHourQuota:
        headers = {
            "X-SLURM-USER-NAME": "slurm",
            "X-SLURM-USER-TOKEN": token,
            "Content-Type": "application/json",
        }
        params = {"account": account_name}
        url = f"{self.slurm_db_api_url}/associations"
        response = await self.client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        for assoc in data.get("associations", []):
            if assoc.get("lineage") == f"/{account_name}/":
                tres_obj = TRES(**assoc["max"]["tres"])
                cpu_item = None
                for item in tres_obj.group.minutes:
                    if item.type == "cpu":
                        cpu_item = item
                        break
                cpu_hours = round(cpu_item.count / 60, 2) if cpu_item else 0.0
                return AccountCPUHourQuota(
                    account_name=account_name, cpu_quota_h=cpu_hours
                )

        raise ValueError(f"Main account association not found for {account_name}")

    async def get_user_accounting_info(
        self, username: str, token: str, usage_start: int
    ) -> UserAccountingResponse:
        headers = {
            "X-SLURM-USER-NAME": "slurm",
            "X-SLURM-USER-TOKEN": token,
            "Content-Type": "application/json",
        }
        url = f"{self.slurm_db_api_url}/associations?user={username}&Include%20usage&usage_start={usage_start}"
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data.get("associations"):
            raise ValueError(f"No associations found for user {username}")

        assoc = data["associations"][0]
        account_name = assoc["account"]

        # CPU usage of the user
        total_cpu_seconds = sum(
            entry["allocated"]["seconds"]
            for entry in assoc["accounting"]
            if entry["TRES"]["type"] == "cpu"
        )
        user_core_h_used = round(total_cpu_seconds / 3600, 2)

        # User quota of the user
        tres_obj = TRES(**assoc["max"]["tres"])
        user_cpu_item = None
        for item in tres_obj.group.minutes:
            if item.type == "cpu":
                user_cpu_item = item
                break
        user_cpu_quota_h = round(user_cpu_item.count / 60, 2) if user_cpu_item else None

        # Inherit account quota if user quota missing
        account_info = await self.get_account_cpu_hour_quota(account_name, token)
        if user_cpu_quota_h is None:
            user_cpu_quota_h = account_info.cpu_quota_h

        return UserAccountingResponse(
            username=username,
            account_name=account_name,
            user_cpu_quota_h=user_cpu_quota_h,
            account_cpu_quota_h=account_info.cpu_quota_h,
            user_core_h_used=user_core_h_used,
        )

    async def get_slurm_job_info(self, job_id: int, token: str) -> SlurmResponse:
        headers = {
            "X-SLURM-USER-NAME": "slurm",
            "X-SLURM-USER-TOKEN": token,
            "Content-Type": "application/json",
        }
        url = f"{self.slurm_api_url}/job/{job_id}"
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return SlurmResponse(**data)


# Dependency Provider Function
def get_slurm_service(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SlurmService:
    """
    FastAPI dependency provider for SlurmService.
    Injects the base URL from settings and a shared HTTP client.
    """
    settings = get_settings()
    if not settings.SLURM_API_BASE:
        raise ValueError("SLURM_API_BASE is not configured correctly in settings.")
    if not settings.SLURMDB_API_BASE:
        raise ValueError("SLURMDB_API_BASE is not configured correctly in settings.")

    return SlurmService(
        slurm_api=settings.SLURM_API_BASE,
        slurm_db_api=settings.SLURMDB_API_BASE,
        client=client,
    )
