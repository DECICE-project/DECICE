import { useState, useEffect, useRef } from 'react';
import { Network } from 'vis-network';

const innerOptions = {
    interaction: { dragNodes: true, dragView: true },
    nodes: {
        shape: 'box',
        margin: 10,
        font: {
            size: 14,
            face: 'arial'
        }
    },
    edges: {
        arrows: 'to',
        smooth: {
            type: 'continuous'
        },
        font: {
            size: 12,
            face: 'arial'
        }
    },
    physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
            gravitationalConstant: -100,
            centralGravity: 0.01,
            springLength: 200,
            springConstant: 0.08
        },
        maxVelocity: 50,
        stabilization: {
            enabled: true,
            iterations: 1000,
            updateInterval: 50
        }
    }
};

export const useInnerNetwork = (serverIP, selectedNode, containerRef) => {
    const [innerEdges, setInnerEdges] = useState(null);
    const [innerNodes, setInnerNodes] = useState(null);
    const [error, setError] = useState(null);
    const networkRef = useRef(null);
    const fetchTimeoutRef = useRef(null);

    const fetchInnerEdges = async() => {
        if (!selectedNode) {
            setInnerEdges(null);
            setInnerNodes(null);
            return;
        }

        // Clear existing timeout
        if (fetchTimeoutRef.current) {
            clearTimeout(fetchTimeoutRef.current);
        }

        // Set a new timeout
        fetchTimeoutRef.current = setTimeout(async() => {
            try {
                setError(null);
                const response = await fetch(
                    `http://${serverIP}/metric_api/raw_edges?vertexpool_id=${selectedNode.vertexpool_id}`
                );

                if (!response.ok) {
                    throw new Error('Failed to fetch inner edges');
                }

                const data = await response.json();
                setInnerEdges(data);

                // İç düğümleri oluştur
                let nodesData = [];
                if (selectedNode.nodes && selectedNode.nodes.length > 0) {
                    nodesData = selectedNode.nodes;
                } else if (selectedNode.devices && selectedNode.devices.length > 0) {
                    nodesData = selectedNode.devices;
                }

                const nodes = nodesData.map((node) => ({
                    id: node.name,
                    label: node.name,
                    title: node.name,
                }));

                setInnerNodes(nodes);
            } catch (err) {
                console.error('Error fetching inner edges:', err);
                setError(err.message);
            }
        }, 300); // 300ms debounce delay
    };

    // İç ağı oluştur ve yönet
    useEffect(() => {
        if (containerRef.current && innerNodes && innerEdges) {
            // Önceki ağı temizle
            if (networkRef.current) {
                networkRef.current.destroy();
            }

            // Yeni ağı oluştur
            const network = new Network(
                containerRef.current, { nodes: innerNodes, edges: innerEdges },
                innerOptions
            );

            networkRef.current = network;

            // Cleanup
            return () => {
                if (networkRef.current) {
                    networkRef.current.destroy();
                }
            };
        }
    }, [innerNodes, innerEdges, containerRef]);

    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (fetchTimeoutRef.current) {
                clearTimeout(fetchTimeoutRef.current);
            }
        };
    }, []);

    return {
        innerEdges,
        innerNodes,
        error,
        fetchInnerEdges
    };
};