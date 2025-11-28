import { useState, useEffect } from 'react';

function scaledSigmoid(x, steep = 1, shift = 10, min = 0, max = 200, c = 2) {
    return c * (min + max / (1 + Math.exp(-steep * (x - shift))));
}

export const useNetworkData = (serverIP) => {
    const [data, setData] = useState(null);
    const [nodes, setNodes] = useState(null);
    const [edges, setEdges] = useState(null);
    const [error, setError] = useState(null);
    const [selectedVertexpool, setSelectedVertexpool] = useState(null);

    const updateVertexpoolLabels = async(vertexpoolId, labels) => {
        try {
            const response = await fetch(`http://${serverIP}/vertexpool/${vertexpoolId}/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(labels),
            });

            if (!response.ok) {
                throw new Error('Failed to update vertexpool labels');
            }

            return true;
        } catch (err) {
            console.error('Error updating vertexpool labels:', err);
            throw err;
        }
    };

    const fetchData = async(selectedVertexpoolId = null) => {
        try {
            setError(null);

            // Construct the URL based on whether a vertexpool is selected
            const url = selectedVertexpoolId ?
                `http://${serverIP}/metric_api/expanded_graph/?vertexpool_id=${selectedVertexpoolId}` :
                `http://${serverIP}/metric_api/expanded_graph/`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('Failed to fetch network data');
            }
            const networkData = await response.json();

            // Process vertexpools data
            const vertexpools = networkData.expanded_vertices.vertexpools;

            setData(vertexpools);

            // Create nodes from vertexpools
            const nodesPlain = vertexpools.map((pool) => {
                const devices = pool.devices || [];
                const nodes = pool.nodes || [];
                const labels = pool.labels || [];
                const labelText = labels.join(', ') || 'No labels';

                return {
                    id: pool.vertexpool_id,
                    label: `${pool.vertexpool_id}`,
                    title: `VertexPool ${pool.vertexpool_id}\nLabels: ${labelText}\nDevices: ${devices.length}\nNodes: ${nodes.length}`
                };
            });

            const selectedVertexes = networkData.expanded_vertices.selected_vertexpool;
            setSelectedVertexpool(selectedVertexes);
            if (selectedVertexes) {
                if (selectedVertexes.vertexpool_id == selectedVertexpoolId) {
                    for (const node of selectedVertexes.nodes) {
                        nodesPlain.push({
                            id: node.nodename,
                            label: node.nodename,
                            title: `Node ${node.nodename}`,
                            group: 'selected',
                            type2: 'node'
                        });
                    }
                    for (const device of selectedVertexes.devices) {
                        nodesPlain.push({
                            id: device.name,
                            label: device.name,
                            title: `Device ${device.name}`,
                            group: 'selected',
                            type2: 'device'
                        });
                    }
                }
            }
            setNodes(nodesPlain);

            // Process edges
            const edgesPlain = networkData.links
                .filter((link) => link.vertexpool_a !== link.vertexpool_b)
                .map((link) => ({
                    from: link.vertexpool_a.toString(),
                    to: link.vertexpool_b.toString(),
                    label: `${link.value.toFixed(2)} ms`,
                    title: `From VertexPool ${link.vertexpool_a} to ${link.vertexpool_b}\nLast Updated: ${new Date(link.lastUpdated).toLocaleString()}`,
                    length: scaledSigmoid(link.value),
                }));
            setEdges(edgesPlain);

        } catch (err) {
            setError(err.message);
        }
    };

    return {
        data,
        nodes,
        edges,
        error,
        selectedVertexpool,
        fetchData,
        updateVertexpoolLabels
    };
};