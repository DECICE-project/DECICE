from pydantic import BaseModel


class TresItem(BaseModel):
    type: str
    name: str
    id: int
    count: int


class TresGroup(BaseModel):
    minutes: list[TresItem]
    active: list[TresItem]


class TresMinutesPer(BaseModel):
    job: list[TresItem]


class TresMinutes(BaseModel):
    total: list[TresItem]
    per: TresMinutesPer


class TresPer(BaseModel):
    job: list[TresItem]
    node: list[TresItem]


# Unified model for both user and account responses coming from /associations api of Slurm
class TRES(BaseModel):
    total: list[TresItem]
    group: TresGroup
    minutes: TresMinutes
    per: TresPer
