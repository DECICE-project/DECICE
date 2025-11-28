import json
from core.data_model import DeciceDigitalTwin
from pydantic import ValidationError


class DTCJsonValidation:
    _dt: DeciceDigitalTwin

    def __init__(self, json_data_serialized: str) -> None:
        self._json_data = json.loads(json_data_serialized)
        self._instantiate_dt()

    @property
    def json_data(self):
        return self._json_data

    @property
    def digital_twin(self):
        return self._dt

    def is_valid(self) -> bool:
        return self._dt is not None

    def _instantiate_dt(self) -> None:
        try:
            self._dt = DeciceDigitalTwin(**self.json_data)
        except ValidationError as e:
            print(f"JSON data is not valid: {e}")
            self._dt = None
