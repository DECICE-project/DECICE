/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable no-unused-vars */
import { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import Popup from 'reactjs-popup';
import 'reactjs-popup/dist/index.css';
// import data from "./try.json";
import {useSelector } from "react-redux";

function scaledSigmoid(x, steep = 1, shift = 10, min = 0, max = 200,c=2) {
    return c*(min + max / (1 + Math.exp(-steep * (x - shift))));
}

const NetworkGraph = () => {
  const serverIP = useSelector((state) => state.serverIP.value);
  const container = useRef(null);
  const innerContainer = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [popupData, setPopupData] = useState({ visible: false, x: 0, y: 0, content: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nodes, setNodes] = useState(null);
  const [edges, setEdges] = useState(null);
  const [data, setData] = useState(null);
  const [innerEdges, setInnerEdges] = useState(null); // State for inner edges

  // Fetch raw nodes
  useEffect(() => {
    const fetchNodes = async () => {
      try {
        const response = await fetch(`http://${serverIP}/telemetry/vertexpools`);
        if (!response.ok) {
          throw new Error('Failed to fetch nodes');
        }
        const data = await response.json();
        setData(data);
        //////////////////////////////////////////////////////7
        // Prepare the nodes array for vis.js
        const node_vertices = [];
        const edges = [];

        data.forEach((item) => {
            // Map nodes with circular shape
            item.nodes.forEach((node) => {
                node_vertices.push({
                id: node.name,
                label: node.name,
                shape: 'circle',
                });
            });

            // Map devices with triangular shape
            item.devices.forEach((device) => {
                node_vertices.push({
                id: device.name,
                label: device.name,
                shape: 'triangle',
                });
            });
        });
        const nodesRaw = data.map((pool) => ({
          id: pool.id, // Keep id as number
          label: '' + pool.id, // Use node labels or a default
          title: pool.id, // You can expand this to include more detailed info if needed
        }));
        setNodes(node_vertices); // Update state with the fetched nodes
        setLoading(false);
      } catch (err) {
        console.log('Error fetching nodes', err);
        setError(err.message);
        setLoading(false);
      }
    };

    const fetchEdges = async () => {
      try {
        const response2 = await fetch(`http://${serverIP}/telemetry/raw_edges`);
        if (!response2.ok) {
          throw new Error(`Failed to fetch edges: ${response2.statusText}`);
        }

        const contentType = response2.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not valid JSON');
        }

        const datalinks = await response2.json();
        const edgesPlain = datalinks
          .filter((link) => link.vertex_b !== link.vertex_a) // filter out self-links
          .map((link) => ({
            from: link.vertex_a,
            to: link.vertex_b,
            label: `${link.value.toFixed(2)} ms`,
            title: `From`,
            length: scaledSigmoid(link.value),
          }));
        console.log('edgesPlain: ', edgesPlain);
        setEdges(edgesPlain);
      } catch (err) {
        console.error('Error fetching edges:', err);
        setError(err.message);
      }
    };

    fetchNodes();
    fetchEdges();
  }, []); // Empty dependency array means this runs only once when the component mounts


  const options = {
    interaction: { dragNodes: true, dragView: true, hover: true },
    nodes: {
        widthConstraint:     { minimum: 40, maximum: 40,}
      },
    edges: {
      smooth: {
        type: 'dynamic',  // Type of smoothing
        roundness: 0.5       //
      }
    }
  };
  const innerOptions = { interaction: { dragNodes: true, dragView: true } };

  useEffect(() => {
    if (container.current && nodes && edges) {
      const network = new Network(container.current, { nodes, edges }, options);
      network.on('click', function (params) {
        if (params.nodes.length > 0) {
          setPopupData({ ...popupData, visible: false });
          const nodeId = Number(params.nodes[0]); // Convert nodeId to number
          const selected = data.find((pool) => pool.id === nodeId);
          setSelectedNode(selected); // Find the clicked vertexpool
          if (selected) {
            setIsOpen(true);
            // We no longer need renderTrigger
          }
        }
      });
      network.on('hoverNode', function (params) {
        const { pointer, node: vp } = params;
        const vertexpool = returnDeviceList(vp);
        const d_nodes = vertexpool.nodes;
        const devices = vertexpool.devices;

        setPopupData({
          visible: true,
          x: pointer.DOM.x,
          y: pointer.DOM.y,
          content: (
            <div className="">
              VertexPoolID: {vp}
              <div>
                <h1 className="font-semibold ">Labels:</h1>
                {vertexpool.vertexpool_labels.map((label) => (
                  <div key={`${label}`}>{label}</div>
                ))}
              </div>
              {d_nodes.length > 0 && (
                <div>
                  <h1 className="font-semibold ">Nodes:</h1>
                  {d_nodes.map((node) => (
                    <div key={node.name}>{node.name}</div>
                  ))}
                </div>
              )}
              {devices.length > 0 && (
                <div>
                  <h1 className="font-semibold ">Devices:</h1>
                  {devices.map((device) => (
                    <div key={device.name}>{device.name}</div>
                  ))}
                </div>
              )}
            </div>
          ),
        });
      });

      // Handle blurNode event to hide the popup
      network.on('blurNode', function () {
        setPopupData({ ...popupData, visible: false });
      });
    }
  }, [nodes, edges, data]);

  // Fetch inner edges when selectedNode changes
  useEffect(() => {
    if (selectedNode) {
      const fetchInnerEdges = async () => {
        try {
          const response = await fetch(
            `http://${server_ip}/telemetry/raw_edges?vertexpool_id=${selectedNode.id}`
          );
          if (!response.ok) {
            throw new Error('Failed to fetch inner edges');
          }
          const data = await response.json();
          setInnerEdges(data);
        } catch (err) {
          console.log('Error fetching inner edges: ', err);
          setError(err.message);
        }
      };
      fetchInnerEdges();
    } else {
      setInnerEdges(null); // Reset inner edges when no node is selected
    }
  }, [selectedNode, isOpen]);

  // Render inner network when innerEdges are fetched
  useEffect(() => {
    if (innerContainer.current && selectedNode && innerEdges && isOpen) {
      console.log('selectedNode: ', selectedNode);
      // Clear the inner container
      innerContainer.current.innerHTML = '';

      // Determine the source of inner nodes
      let innerNodesData = [];
      if (selectedNode.nodes && selectedNode.nodes.length > 0) {
        innerNodesData = selectedNode.nodes;
      } else if (selectedNode.devices && selectedNode.devices.length > 0) {
        innerNodesData = selectedNode.devices;
      } else {
        innerNodesData = [];
      }

      if (innerNodesData.length > 0) {
        const innerNodes = innerNodesData.map((node) => ({
          id: node.name, // Use node name as ID to match edge references
          label: node.name,
          title: node.name,
        }));

        const innerEdgesFormatted = innerEdges.map((edge) => ({
          from: edge.vertex_a,
          to: edge.vertex_b,
          label: `${edge.value.toFixed(2)} ms`,
          title: `From ${edge.vertex_a} to ${edge.vertex_b}`,
          length: edge.value * 50,
        }));

        const innerNetwork = new Network(
          innerContainer.current,
          { nodes: innerNodes, edges: innerEdgesFormatted },
          innerOptions
        );
      }
    }
  }, [selectedNode, innerEdges, isOpen]);

  function returnDeviceList(nodeId) {
    const selected = data.find((pool) => pool.id === nodeId);
    return selected;
  }

  return (
    <>
      <div ref={container} className="h-[70vh] white dark:black" />
      {popupData.visible && (
        <div
          style={{
            position: 'absolute',
            top: popupData.y,
            left: popupData.x,
            backgroundColor: 'white',
            border: '1px solid black',
            padding: '5px',
            zIndex: 1000,
          }}
        >
          {popupData.content}
        </div>
      )}
      <Popup open={isOpen} onClose={() => setIsOpen(false)}>
        <div className="w-[70vh] h-[70vh]">
          <div ref={innerContainer} className="w-[100vh] h-[70vh]" />
        </div>
      </Popup>
    </>
  );
};

export default NetworkGraph;
