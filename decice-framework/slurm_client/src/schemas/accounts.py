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
# The 4 fields above have so many subfields. Necessary classes are divided into tres.py and users.py


##################
# SLURM API QUERY
##################
# curl -s -X GET "http://localhost:6820/slurmdb/v0.0.43/associations?account={account_name}" \
#   -H "X-SLURM-USER-NAME: slurm" -H "X-SLURM-USER-TOKEN: MYTOKEN"


# Account Response Model
class AccountCPUHourQuota(BaseModel):
    account_name: str
    cpu_quota_h: Optional[float]  # can be None if not found
