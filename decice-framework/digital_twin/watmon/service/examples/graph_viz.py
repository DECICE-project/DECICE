import networkx as nx
from watmon_service.graph import NetworkxEdge, NetworkxNode, TypedGraph
from matplotlib import pyplot as plt


def visualize_graph(
    tg: TypedGraph, title: str = "Graph Visualization by ICMP Distance"
):
    G = tg.graph

    # Normalize weights between 0 and 1, then invert
    max_icmp = 300
    edge_weights = {
        (u, v): 1 - min(d.get("weight", 1.0), max_icmp) / max_icmp
        for u, v, d in G.edges(data=True)
    }

    for u, v in G.edges():
        G[u][v]["weight_for_layout"] = edge_weights[(u, v)]

    pos = nx.spring_layout(G, weight="weight_for_layout", seed=42)

    device_nodes = [node for node in G.nodes() if node.type == "device"]
    other_nodes = [node for node in G.nodes() if node.type != "device"]

    plt.figure(figsize=(10, 8))
    plt.title(title)

    device_node_size = 300
    other_node_size = 200

    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=device_nodes,
        node_shape="^",
        node_color="orange",
        node_size=device_node_size,
        label="Device",
    )

    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=other_nodes,
        node_shape="o",
        node_color="skyblue",
        node_size=other_node_size,
        label="Node",
    )

    nx.draw_networkx_edges(
        G, pos, arrowstyle="->", arrowsize=15, width=2, edge_color="gray"
    )

    labels = {node: node.name for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=9)

    plt.legend(scatterpoints=1)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


def main():
    tg = TypedGraph()

    # Create nodes
    d1 = NetworkxNode("device1", "device")
    n1 = NetworkxNode("node1", "node")
    d2 = NetworkxNode("device2", "device")
    n2 = NetworkxNode("node2", "node")
    n3 = NetworkxNode("node3", "node")
    # n4 = NetworkxNode("node4", "node")
    nodes = [n1, n2, n3]
    con_devices = [d1, d2]
    # Add nodes
    for n in nodes:
        tg.add_node(n)
        tg.add_edge(n, n, NetworkxEdge(label="self-loop", weight=0.1))
        for d in con_devices:
            tg.add_edge(n, d, NetworkxEdge())

    tg.add_edge(n1, n2)
    tg.add_edge(n2, n1)
    d3 = NetworkxNode("device3", "device")
    tg.add_edge(n1, d3)
    tg.add_edge(n3, d3)
    tg.add_edge(n1, n3)
    tg.add_edge(n3, n1)
    tg.add_edge(n3, n2)
    tg.add_edge(n2, n3)
    # tg.add_edge(n3,n4)
    # tg.add_edge(n4,n3)
    # tg.add_edge(n1,n3,)
    # tg.add_edge(n3,n1)

    # Visualize initial graph
    visualize_graph(tg, "Initial Graph")

    # Print structurally equivalent nodes groups (at least 2 members)
    groups = tg.get_structural_equivalence()
    print("Structurally equivalent groups:")
    for group in groups:
        print(group)


if __name__ == "__main__":
    main()
