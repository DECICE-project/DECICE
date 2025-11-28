// InnerNetwork.jsx
import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network';

 const InnerNetwork = ({ selectedNode, innerEdges, resetNetwork }) => {
  const innerContainer = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!innerContainer.current || !selectedNode || !innerEdges) {
      return;
    }

    // Ensure clean container
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }
    innerContainer.current.innerHTML = '';

    const innerNodesData = [
      ...(selectedNode.nodes || []),
      ...(selectedNode.devices || [])
    ];

    if (innerNodesData.length > 0) {
      const innerNodes = innerNodesData.map((node) => ({
        id: node.name,
        label: node.name,
        title: node.name,
        shape: selectedNode.nodes.includes(node) ? 'circle' : 'triangle'
      }));

      const innerEdgesFormatted = innerEdges.map((edge) => ({
        from: edge.vertex_a,
        to: edge.vertex_b,
        label: `${edge.value.toFixed(2)} ms`,
        title: `From ${edge.vertex_a} to ${edge.vertex_b}`,
        length: edge.value * 50,
      }));

      const options = {
        interaction: { dragNodes: true, dragView: true },
        nodes: {
          size: 30,  // Fixed size for all nodes
          font: {
            size: 14,
            vadjust: -8,  // Move label up inside the node
            face: 'system-ui, sans-serif'
          },
          widthConstraint: { minimum: 40, maximum: 40 }
        },
        edges: {
          smooth: {
            type: 'dynamic',
            roundness: 0.5
          }
        }
      };

      networkRef.current = new Network(
        innerContainer.current,
        { nodes: innerNodes, edges: innerEdgesFormatted },
        options
      );
    }

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [selectedNode, innerEdges, resetNetwork]);

  return <div ref={innerContainer} className="w-full h-full" />;
};
export default InnerNetwork;
