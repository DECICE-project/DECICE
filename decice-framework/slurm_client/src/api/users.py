from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from schemas.users import UserAccountingResponse
from services.slurm_service import SlurmService, get_slurm_service
from services.token_service import TokenService, get_token_service

router = APIRouter()


@router.get(
    "/users/{username}",
    response_model=UserAccountingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_resources(
    username: str,
    usage_start: str,
    slurm_service: SlurmService = Depends(get_slurm_service),
    token_service: TokenService = Depends(get_token_service),
):
    # Convert string date to UNIX timestamp
    try:
        dt = datetime.strptime(usage_start, "%Y-%m-%d")
        usage_start_ts = int(dt.timestamp())
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Get token from token generator
    # Since this is a SlurmDB query, we should use "slurm" user instead of normal username
    try:
        token = token_service.request_token("slurm")
        # print("Created token:", token)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error while creating token: {str(e)}"
        )

    try:
        return await slurm_service.get_user_accounting_info(
            username, token, usage_start_ts
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
