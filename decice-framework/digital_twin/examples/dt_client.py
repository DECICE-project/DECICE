from digital_twin.core.data_model import DeciceDigitalTwin
from digital_twin.core.model_utils import get_all_nodes
import requests

# Fetch JSON data from URL
url = "http://localhost:8010/api/model_core/"
response = requests.get(
    url,
).json()
dt = DeciceDigitalTwin(**response)

nodes = get_all_nodes(dt, include_vertexpool_id=True)
print(nodes)
