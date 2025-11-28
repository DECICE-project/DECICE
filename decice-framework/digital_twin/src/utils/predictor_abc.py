from digital_twin.core.data_model import DeciceDigitalTwin
from abc import ABC, abstractmethod


class PredictorBase(ABC):
    @abstractmethod
    def check_triggering_conditions(self, digital_twin: DeciceDigitalTwin) -> bool:
        pass

    @abstractmethod
    def process(self, digital_twin: DeciceDigitalTwin):
        pass
