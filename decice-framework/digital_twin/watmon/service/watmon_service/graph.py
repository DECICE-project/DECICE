from typing import Literal
import networkx as nx
from collections import defaultdict


class NetworkxNode:
    def __init__(
        self,
        name: str,
        type: str = Literal["device", "node"],
        device_id: int | None = None,
    ):
        self.name = name
        self.type = type
        self.device_id = device_id

    def __hash__(self):
        return hash((self.name, self.type, self.device_id))

    def __eq__(self, other):
        if not isinstance(other, NetworkxNode):
            return False
        return (self.name, self.type, self.device_id) == (
            other.name,
            other.type,
            other.device_id,
        )

    def __repr__(self):
        return f"NetworkxNode(name={self.name}, type={self.type}, device_id={self.device_id})"

    def key(self) -> tuple[str, str]:
        return (self.name, self.type)


class NetworkxEdge:
    def __init__(self, label: str = "", weight: float = 1.0, metadata: dict = None):
        self.label = label
        self.weight = weight
        self.metadata = metadata or {}

    def __repr__(self):
        return f"NetworkxEdge(label={self.label}, weight={self.weight}, metadata={self.metadata})"


class TypedGraph:
    def __init__(self, directed: bool = True):
        self.graph = nx.DiGraph() if directed else nx.Graph()
        self.node_index = {}

    def add_node(self, node: NetworkxNode):
        self.graph.add_node(node)
        self.node_index[node.key()] = node

    def add_edge(self, src: NetworkxNode, dst: NetworkxNode, edge: NetworkxEdge = None):
        if edge is None:
            edge = NetworkxEdge()  # create default edge object
        self.graph.add_edge(src, dst, **edge.__dict__)

    def to_adjacency_dict(self):
        # For structural equivalence algo
        adj = {}
        for node in self.graph.nodes:
            adj[node] = list(self.graph.neighbors(node))
        return adj

    def to_node_key_index(self) -> dict[tuple[str, str], NetworkxNode]:
        """Returns a dictionary mapping node keys to NetworkxNode objects.
        Node keys are tuples of (name, type).
        """
        return self.node_index

    def add_edge_from_key(
        self,
        src_key: tuple[str, str],
        dst_key: tuple[str, str],
        edge: NetworkxEdge = None,
    ):
        """Adds an edge between nodes identified by their keys."""
        src_node = self.node_index[src_key]
        dst_node = self.node_index[dst_key]
        self.add_edge(src_node, dst_node, edge)

    def get_structural_equivalence(
        self, at_least_one_member: bool = False
    ) -> list[list[NetworkxNode]]:
        """Finds structurally equivalent nodes in the graph."""
        # graph: dict {node: [outgoing_neighbors]}
        in_neighbors = defaultdict(set)
        out_neighbors = defaultdict(set)
        graph = self.to_adjacency_dict()

        for u in graph:
            for v in graph[u]:
                out_neighbors[u].add(v)
                in_neighbors[v].add(u)

        # fingerprint each node as a tuple of sorted in/out neighbors
        fingerprints = defaultdict(list)
        for node in graph:
            key = (frozenset(in_neighbors[node]), frozenset(out_neighbors[node]))
            fingerprints[key].append(node)

        # return groups of structurally equivalent nodes
        if at_least_one_member:
            return [group for group in fingerprints.values() if len(group) > 1]
        else:
            return [group for group in fingerprints.values()]

    def remove_edge_from_key(
        self,
        src_key: tuple[str, str],
        dst_key: tuple[str, str],
    ):
        """Removes an edge between nodes identified by their keys."""
        src_node = self.node_index.get(src_key)
        dst_node = self.node_index.get(dst_key)
        if src_node is None or dst_node is None:
            raise KeyError(f"One or both keys not found: {src_key}, {dst_key}")
        if self.graph.has_edge(src_node, dst_node):
            self.graph.remove_edge(src_node, dst_node)
        else:
            raise ValueError(f"No edge exists between {src_key} and {dst_key}")

    def remove_node_from_key(self, key: tuple[str, str]):
        node = self.node_index.get(key)
        if node is None:
            raise KeyError(f"Node with key {key} not found")
        self.graph.remove_node(node)  # removes node and all connected edges
        del self.node_index[key]  # remove from your index
