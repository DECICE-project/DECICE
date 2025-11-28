from typing import Optional

from pydantic import BaseModel

#########################################
# CORRESPONDING SLURM API (ASSOCIATIONS)
#########################################

# https://slurm.schedmd.com/rest_api.html#slurmdbV0043GetAssociations
# The API "get /slurmdb/v0.0.43/associations/" has the following 4 main structures:

##################
# API RETURN TYPE
##################
# associations = array[v0.0.43_user]
# meta (optional) = v0.0.43_openapi_meta
# errors (optional) = array[v0.0.43_openapi_error]
# warnings (optional) = array[v0.0.43_openapi_warning]


###############
# DATA CLASSES
###############
# The 4 fields above have so many subfields. In order to present and capture the necessary info, all the classes below were created.
# Because it is very hard to represent everything in a single class


##################
# SLURM API QUERY
##################
# The following classes represent the important fields of the API response for the following slurm query:
# curl -s -X GET "http://localhost:6820/slurmdb/v0.0.43/associations?user={username}&Include%20usage&usage_start={UNIX_TIMESTAMP}" \
#   -H "X-SLURM-USER-NAME: slurm" -H "X-SLURM-USER-TOKEN: MYTOKEN"


class Allocated(BaseModel):
    seconds: int


class TRESUsage(BaseModel):
    type: str
    name: str
    id: int
    count: int


class AccountingEntry(BaseModel):
    allocated: Allocated
    id: int
    id_alt: int
    start: int
    TRES: TRESUsage


class Association(BaseModel):
    accounting: list[AccountingEntry]
    account: str
    cluster: str
    lineage: str
    user: Optional[str]
    max: Optional[dict]  # parsed manually into TRES when needed


class SlurmAssocUserResponse(BaseModel):
    associations: list[Association]


class UserCPUHourUsage(BaseModel):
    username: str
    core_h_used: float


class UserAccountingResponse(BaseModel):
    username: str
    account_name: str
    user_cpu_quota_h: float
    account_cpu_quota_h: float
    user_core_h_used: float
