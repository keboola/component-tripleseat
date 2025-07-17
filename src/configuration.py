import logging
from typing import Dict, Literal
from datetime import datetime

import pytz
from pydantic import BaseModel, Field, ValidationError, field_validator
from dateparser import parse as parse_natural_date
from keboola.component.exceptions import UserException


class Authorization(BaseModel):
    client_id: str = Field(alias="#client_id")
    client_secret: str = Field(alias="#client_secret")

    @field_validator("client_id", "client_secret")
    def must_not_be_empty(cls, value: str, info) -> str:
        if not value.strip():
            raise ValueError(f"Field '{info.field_name}' cannot be empty")
        return value


class Endpoints(BaseModel):
    bookings: bool = Field(default=False, description="Export bookings")

    @property
    def as_dict(self) -> Dict[str, bool]:
        return self.model_dump()


class SyncOptions(BaseModel):
    sync_mode: Literal["full_sync", "incremental_sync"] = Field(default="full_sync")
    date_from: str = Field(default="1 month ago")
    date_to: str | None = Field(default=None)

    def _parse_natural_date(self, input_str: str) -> datetime:
        date_obj = parse_natural_date(input_str, settings={"TIMEZONE": "UTC"})
        if date_obj is None:
            raise UserException(f"Invalid date string: '{input_str}'")
        return date_obj.replace(tzinfo=pytz.UTC)

    def resolved_date_from(self, state: Dict[str, str]) -> datetime:
        input_value = self.date_from.strip().lower()

        if input_value in {"last", "lastrun", "last_run", "last run"}:
            last_run = state.get("last_successful_run")
            if not last_run:
                raise UserException(
                    "You used 'last run' as date_from, but no previous run state was found."
                )
            return self._parse_natural_date(last_run)

        return self._parse_natural_date(input_value)

    def resolved_date_to(self) -> datetime:
        return self._parse_natural_date(self.date_to.strip().lower()) if self.date_to else datetime.now(pytz.UTC)


class Configuration(BaseModel):
    authorization: Authorization
    endpoints: Endpoints
    sync_options: SyncOptions
    debug: bool = False

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

        if self.debug:
            logging.debug("Component will run in Debug mode")
