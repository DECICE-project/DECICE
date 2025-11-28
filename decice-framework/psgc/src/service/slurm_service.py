from uuid import UUID

from clients.slurm_client import SlurmClient


class SlurmService:
    def __init__(self, slurm_client: SlurmClient):
        self.slurm_client = slurm_client

    async def submit_job(
        self, sbatch_file: str, username: str, work_dir: str, task_id: UUID
    ):
        return await self.slurm_client.submit_job(
            sbatch_file=sbatch_file,
            username=username,
            work_dir=work_dir,
            task_id=task_id,
        )

    async def get_job_info():
        pass

    async def get_user_accounting():
        pass
