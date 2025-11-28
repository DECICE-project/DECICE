from enum import StrEnum


class APIVersion(StrEnum):
    v1 = "/v1"


class Tags(StrEnum):
    config = "config"
    workflow = "workflow"
    user = "user"
    auth = "auth"
    schedule = "schedule"
    internal = "internal"
