from digital_twin.core.json_validation import DTCJsonValidation
from digital_twin.core.time_series import DTCTimeSeries, TimeSeriesClient
from digital_twin.core.data_model import DeciceDigitalTwin

# from core.json_validation import DTCJsonValidation

# from core.time_series import DTCTimeSeries, TimeSeriesClient
# from core.data_model import DeciceDigitalTwin
# from core.config import DTConfig

import json
from typing import Union
import argparse
from digital_twin.config.config import service_settings


class DTCController:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        time_series_client: TimeSeriesClient | None = None,
    ) -> None:
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        self.digital_twin: DeciceDigitalTwin = None
        self.time_series_client = None 
        
        if time_series_client:
            self.time_series_client = time_series_client
        elif service_settings.influxdb:
            self.time_series_client = DTCTimeSeries(
                service_settings.influxdb.url,
                service_settings.influxdb.org,
                service_settings.influxdb.token,
                service_settings.influxdb.bucket,
            )
        else:
            self.time_series_client = None

    def update_digital_twin(self, data: Union[str | DeciceDigitalTwin]) -> None:
        if isinstance(data, DeciceDigitalTwin):
            self.digital_twin = data
        else:
            validator = DTCJsonValidation(data)
            self.digital_twin = validator.digital_twin

        if self.digital_twin and self.time_series_client:
            self._save_point()

    def _save_point(self):
        self.time_series_client.write(self.digital_twin)


def get_dtc_controller() -> DTCController:
    return DTCController()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--json_path",
        type=str,
        default="./configs/output.json",
        help="Path of persisted DigitalTwin json data",
    )

    args = parser.parse_args()
    json_path = args.json_path

    dtc_controller = DTCController()

    with open(json_path, "r") as f:
        data = json.load(f)
    dtc_controller.update_digital_twin(json.dumps(data))


if __name__ == "__main__":
    main()
