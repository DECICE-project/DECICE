from pydantic import BaseModel, model_validator, Field
from datetime import datetime, timedelta
from datetime import timezone

import re
import pytimeparse
from dateutil.parser import isoparse


relative_time_re = re.compile(r"^-(\d+)([smhdwMy])$")


class TimeSeriesPointWrite(BaseModel):
    timetamp: datetime | int | None
    tags: dict | None = {}
    fields: dict | None = {}
    measurement: str


class TimeRange(BaseModel):
    start: datetime | str = Field(
        "-30m",
        description="Start time as ISO8601 datetime or relative time string (e.g. '-30m' for 30 minutes ago)",
        example="-30m",
    )
    stop: datetime | str | None = Field(
        None,
        description="Stop time as ISO8601 datetime or relative time string (defaults to now if omitted)",
        examples=[None],
    )

    @model_validator(mode="before")
    def parse_and_validate_times(cls, values: dict) -> dict:
        start = values.get("start")
        stop = values.get("stop")

        # Parse start
        if isinstance(start, str):
            values["start"] = parse_flexible_time(start)
        elif isinstance(start, datetime):
            values["start"] = start.astimezone(timezone.utc)
        else:
            raise ValueError("start must be datetime or str")

        # Parse stop if given
        if stop is not None:
            if isinstance(stop, str):
                values["stop"] = parse_flexible_time(stop)
            elif isinstance(stop, datetime):
                values["stop"] = stop.astimezone(timezone.utc)
            else:
                raise ValueError("stop must be datetime, str or None")

            if values["stop"] < values["start"]:
                raise ValueError("stop must be after or equal to start")
        else:
            values["stop"] = datetime.now(timezone.utc)

        return values


class TimeSeriesPointRead(BaseModel):
    time_range: TimeRange
    measurement: str
    bucket: str
    tags: dict = {}


def parse_flexible_time(value: str) -> datetime:
    try:
        dt = isoparse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        pass
    if relative_time_re.match(value):
        seconds = pytimeparse.timeparse.timeparse(value[1:])
        if seconds is None:
            raise ValueError(f"Invalid relative time format: {value}")
        return datetime.now(timezone.utc) - timedelta(seconds=seconds)
    raise ValueError(f"Invalid datetime or relative time format: {value}")
