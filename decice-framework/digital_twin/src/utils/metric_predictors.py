from digital_twin.utils.predictor_abc import PredictorBase
from digital_twin.core.data_model import DeciceDigitalTwin
import random


# TODO update
class MemoryPredictor(PredictorBase):
    def check_triggering_conditions(self, digital_twin: DeciceDigitalTwin) -> bool:
        return digital_twin.nodepools[0].nodes[0].metrics.memory_usage_percent <= 10

    def process(self, digital_twin: DeciceDigitalTwin):
        digital_twin.nodepools[0].nodes[0].metrics.memory_usage_percent = random.randint(0, 100)


class CPUPredictor(PredictorBase):
    def check_triggering_conditions(self, digital_twin: DeciceDigitalTwin) -> bool:
        return digital_twin.nodepools[0].nodes[0].metrics.cpu_usage_percent <= 10

    def process(self, digital_twin: DeciceDigitalTwin):
        digital_twin.nodepools[0].nodes[0].metrics.cpu_usage_percent = random.randint(0, 100)
