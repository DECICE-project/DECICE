/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable no-unused-vars */
import { useEffect, useRef, useState, useMemo } from 'react';
import { Network } from 'vis-network';
import Popup from 'reactjs-popup';
import 'reactjs-popup/dist/index.css';
import { options, getEdgeColor } from "./visOptions";
import { useSelector } from "react-redux";
import { ErrorMessage } from '../../common/ErrorMessage';
import { NodePopup } from './NodePopup';
import { SearchField } from './SearchField';
import { useNetworkData } from './hooks/useNetworkData';
import { useInnerNetwork } from './hooks/useInnerNetwork';
import { AddDeviceModal } from './AddDeviceModal';
import { DevicePopup } from './DevicePopup';
import { VertexPoolDetailsPopup } from './VertexPoolDetailsPopup';
import UpdateNode from './UpdateNode';
import { toast } from 'react-toastify';
// import data from "./try.json";

const Graph = () => {
  const serverIP = useSelector((state) => state.serverIP.watmon_api_ip);
  const container = useRef(null);
  const innerContainer = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [popupData, setPopupData] = useState({ visible: false, x: 0, y: 0, content: '' });
  const [network, setNetwork] = useState(null);
  const [isAddDeviceOpen, setIsAddDeviceOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [selectedNodeForEdit, setSelectedNodeForEdit] = useState(null);
  const popupRef = useRef(null);
  const hoverTimeoutRef = useRef(null);
  
  const { 
    data, 
    nodes, 
    edges, 
    error, 
    selectedVertexpool,
    updateVertexpoolLabels,
    fetchData 
  } = useNetworkData(serverIP);

  const {
    innerEdges,
    innerNodes,
    error: innerError,
    fetchInnerEdges
  } = useInnerNetwork(serverIP, selectedNode, innerContainer);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      fetchInnerEdges();
    }
  }, [selectedNode]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (popupRef.current && !popupRef.current.contains(event.target)) {
        setPopupData(prev => ({ ...prev, visible: false }));
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleNodeEditClick = (node) => {
    let targetVertexpool = selectedNode;
    let targetType = node.type2 || "node";
    if (!targetVertexpool) {
      // If no vertexpool is selected, try to find it from the data
      targetVertexpool = data.find(pool => {
        // For nodes
        if (node.type2 === 'node') {
          targetType = 'node';
          return selectedVertexpool.nodes?.some(n => n.nodename === node.id || n.nodename === node.label);
        }
        // For devices
        if (node.type2 === 'device') {
          targetType = 'device';
          return selectedVertexpool.devices?.some(d => d.name === node.id || d.name === node.label);
        } 
        // For other cases (vertexpools)
        return (pool.nodes?.some(n => n.nodename === node.nodename))
  
      });
      
      if (!targetVertexpool) {
        console.error('No vertexpool found for the node:', node);
        toast.error('Could not determine the current vertexpool');
        return;
      }
      
      setSelectedNode(targetVertexpool);
    }
    if (targetType === 'node') {
      setSelectedNodeForEdit({
        ...node,
        id: node.nodename || node.name || node.id,
        currentVertexpoolId: targetVertexpool?.vertexpool_id || targetVertexpool?.id
      });
    } else if (targetType === 'device') {
      setSelectedDevice({
        ...selectedVertexpool.devices?.find(d => d.name === node.id || d.name === node.label),
        id: selectedVertexpool.devices?.find(d => d.name === node.id || d.name === node.label)?.id,
      });
    }
  };

  const handleNodeEditSuccess = () => {
    fetchData();
    setSelectedNodeForEdit(null);
  };

  const showNodePopup = (params, isClick = false) => {
    if (params.nodes?.length > 0 || params.node) {
      const vp_id = params.node;
      const vertexpool = returnDeviceList(vp_id);
      const { pointer } = params;
      
      // Clear existing timeout
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }

      setPopupData({
        visible: true,
        x: pointer.DOM.x,
        y: pointer.DOM.y,
        content: (
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">VertexPool ID: {vertexpool.vertexpool_id}</h2>
              <button
                onClick={() => {
                  setPopupData({ ...popupData, visible: false });
                  setSelectedNode(vertexpool);
                  setIsOpen(true);
                }}
                className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Details
              </button>
            </div>
            <NodePopup 
              vertexpool={vertexpool} 
              onDeviceClick={handleDeviceClick}
              onNodeClick={handleNodeEditClick}
            />
          </div>
        )
      });
    }
  };

  const handleNodeHover = (params) => {
    if (params.nodes?.length > 0 || params.node) {
      const nodeId = params.nodes?.[0] || params.node;
      const node = nodes.find(n => n.id === nodeId);
      
      // For nodes with type2='node', show a different popup
      if (node?.type2 === 'node') {
        const { pointer } = params;
        setPopupData({
          visible: true,
          x: pointer.DOM.x,
          y: pointer.DOM.y,
          content: (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold">Node: {node.label}</h2>
                <button
                  onClick={() => handleNodeEditClick(node)}
                  className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Edit
                </button>
              </div>
              <div className="text-sm">
                <p>Type: Node</p>
                <p>ID: {node.id}</p>
              </div>
            </div>
          )
        });
      } else if (node?.type2 === 'device') {
        const { pointer } = params;
        setPopupData({
          visible: true,
          x: pointer.DOM.x,
          y: pointer.DOM.y,
          content: (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold">Device: {node.label}</h2>
                <button
                  onClick={() => handleNodeEditClick(node)}
                  className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Edit
                </button>
              </div>
              <div className="text-sm">
                <p>Type: Device</p>
                <p>ID: {node.id}</p>
              </div>
            </div>
          )
        });
      } else {
        // For other nodes, use the existing showNodePopup function
        showNodePopup(params);
      }
    } else {
      // Clear popup when mouse leaves node
      setPopupData(prev => ({ ...prev, visible: false }));
    }
  };

  const handleSearch = async (result) => {
    const { poolId, selectedItem } = result;
    
    const selected = data.find((pool) => pool.id === poolId);
    if (!selected) return;

    setSelectedNode(selected);
    setIsOpen(true);
    
  };

  const handleDeviceClick = (device) => {
    // Find which vertexpool this device belongs to
    const vertexpool = data.find(pool => 
      pool.devices?.some(d => d.id === device.id || d.name === device.name)
    );
    setSelectedDevice({
      ...device,
      vertexpool_id: vertexpool?.id
    });
  };

  const handleDevicePopupClose = () => {
    setSelectedDevice(null);
  };

  const handleDeviceActionSuccess = () => {
    fetchData();
  };

  const networkData = useMemo(() => {
    if (!nodes || !edges) return null;
    
    // Add vertexpoolId and style to each node based on type
    const nodesWithClusterInfo = nodes.map(node => {
      // Get vertexpool info
      const vertexpool = data.find(vp => 
        vp.devices?.some(d => d.id === node.id || d.name === node.name)
      );

      let nodeStyle = options.nodes;

      if (node.type2) {
        switch (node.type2) {
          case 'device':
            nodeStyle = {
              color: { 
                  background: '#ef4444', border: '#dc2626' ,                
                  highlight: { background: '#ef4444', border: '#dc2626' },
                  hover: { background: '#ef4444', border: '#dc2626' },
              },
              shape: 'triangle',
              size: 30,             
              margin: 5,
              fixed: {
                  size: true
              },
              font: {
                  size: 12,
                  align: 'center',
                  multi: true,
                  vadjust: -70
              },
              widthConstraint: {
                minimum: 60,
                maximum: 60
              },
              heightConstraint: {
                minimum: 60,
                maximum: 60
              }
                           
            };
            break;
          case 'node':
            nodeStyle = {
              size: 30,
              color: { 
                background: '#3b82f6', border: '#2563eb',      
                highlight: { background: '#3b82f6', border: '#2563eb' },
                hover: { background: '#3b82f6', border: '#2563eb' },
              },
              widthConstraint: {
                minimum: 60,
                maximum: 60
              },
              heightConstraint: {
                minimum: 60,
                maximum: 60
              },
              margin: 5,
              font: {
                size: 12,
                align: 'center',
                multi: true,
                vadjust: 0
              },
              fixed: {
                size: true
              }
            };
            break;
          default:
            break;
        }
      }

      return {
        ...node,
        vertexpoolId: vertexpool?.vertexpool_id,
        ...nodeStyle
      };
    });

    // Add color to edges based on latency
    const edgesWithColor = edges.map(edge => {
      const latency = parseFloat(edge.label?.replace(' ms', '') || '0');
      return {
        ...edge,
        color: getEdgeColor(latency),
        title: `Latency: ${edge.label}\nRoot: ${edge.from}\nTarget: ${edge.to}`
      };
    });

    return {
      nodes: nodesWithClusterInfo,
      edges: edgesWithColor
    };
  }, [nodes, edges, data]);

  useEffect(() => {
    if (container.current && networkData) {
      const networkInstance = new Network(container.current, networkData, options);
      setNetwork(networkInstance);
      
      // Set zoom level initially and start simulation
      setTimeout(() => {
        networkInstance.moveTo({
          scale: 0.5,
          animation: {
            duration: 1000,
            easingFunction: 'easeInOutQuad'
          }
        });
        
        networkInstance.startSimulation();
        setTimeout(() => {
          networkInstance.stopSimulation();
        }, 5000);  
      }, 1000);

      // Stabilization event
      networkInstance.on('stabilizationIterationsDone', () => {
        networkInstance.setOptions({ physics: { enabled: false } });
      });
      
      networkInstance.on('click', async (params) => {
        if (params.nodes.length) {
          const nodeId = params.nodes[0];
          const vertexpool = data.find(vp => vp.vertexpool_id.toString() === nodeId.toString());
          
          if (vertexpool) {
            await fetchData(nodeId);
          }
        }
      });

      networkInstance.on('hoverNode', handleNodeHover);
      networkInstance.on('blurNode', () => {
        setPopupData(prev => ({ ...prev, visible: false }));
      });
    }
  }, [networkData, data, edges]);

  function returnDeviceList(vp_id) {
    // Try to find the vertexpool by different ID formats
    const vertexpool = data.find((pool) => {
      // Check if nodeId matches vertexpool_id
      if (pool.vertexpool_id?.toString() === vp_id?.toString()) {
        return true;
      }
      
      // // Check if nodeId matches any device name or id
      // if (pool.devices?.some(d => d.id?.toString() === vp_id?.toString() || d.name?.toString() === vp_id?.toString())) {
      //   return true;
      // }
      
      // // Check if nodeId matches any node name
      // if (pool.nodes?.some(n => n.name?.toString() === vp_id?.toString())) {
      //   return true;
      // }
      
      return false;
    });
    
    return vertexpool;
  }

  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="relative w-full h-full">
      {/* Centered selected vertexpool ID at the top */}
      {selectedVertexpool && selectedVertexpool.vertexpool_id && (
        <div className="absolute left-1/2 top-4 transform -translate-x-1/2 z-20 flex items-center gap-2">
          <div className="p-2 bg-blue-100 dark:bg-blue-900 border border-blue-300 dark:border-blue-700 rounded-lg text-blue-900 dark:text-blue-100 text-center text-sm font-semibold shadow min-w-[220px]">
            Selected Vertexpool ID: {selectedVertexpool.vertexpool_id}
          </div>
          {/* Undo button for selected vertexpool */}
          <button
            onClick={() => {
              setSelectedNode(null); // Clear selected vertexpool
              fetchData(); // Refresh network
            }}
            className="ml-2 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center"
            title="Undo Selection"
          >
            {/* Undo icon */}
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M7.707 14.707a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414l4-4a1 1 0 111.414 1.414L5.414 9H11a4 4 0 110 8h-1a1 1 0 110-2h1a2 2 0 100-4H5.414l2.293 2.293a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}
      <div className="absolute top-4 left-4 z-10">
        <div className="w-[220px]">
          <SearchField 
            onSearch={handleSearch} 
            data={data} 
          />
          <button
            onClick={() => setIsAddDeviceOpen(true)}
            className="mt-2 p-2 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
            title="Add New Device"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            Add New Device
          </button>
        </div>
      </div>

      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={() => fetchData()}
          className="p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Refresh Network"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
          </svg>
          Refresh Network
        </button>
      </div>
      
      <div 
        ref={container} 
        className="h-[70vh] bg-white dark:bg-gray-900 rounded-lg shadow-lg" 
      />
      
      {popupData.visible && (
        <div
          ref={popupRef}
          className="absolute bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl p-4 z-50 min-w-[300px]"
          style={{
            top: popupData.y,
            left: popupData.x,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {popupData.content}
        </div>
      )}

      <VertexPoolDetailsPopup
        isOpen={isOpen}
        onClose={() => {
          setIsOpen(false);
          setSelectedNode(null);
        }}
        selectedNode={selectedNode}
        updateVertexpoolLabels={updateVertexpoolLabels}
        innerError={innerError}
        innerNodes={innerNodes}
        innerEdges={innerEdges}
        innerContainerRef={innerContainer}
      />

      <AddDeviceModal 
        isOpen={isAddDeviceOpen} 
        onClose={() => setIsAddDeviceOpen(false)} 
        onSuccess={() => {
          fetchData();
          setIsAddDeviceOpen(false);
        }}
      />

      {selectedDevice && (
        <Popup
          open={!!selectedDevice}
          onClose={handleDevicePopupClose}
          modal
          className="rounded-lg overflow-hidden p-0 w-full max-w-2xl mx-auto shadow-xl"
          overlayStyle={{ background: 'rgba(0, 0, 0, 0.5)' }}
          contentStyle={{ background: 'transparent', border: 'none', padding: 0 }}
        >
          <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl">
            <DevicePopup
              device={selectedDevice}
              onClose={handleDevicePopupClose}
              onSuccess={handleDeviceActionSuccess}
              vertexPools={data}
            />
          </div>
        </Popup>
      )}

      {selectedNodeForEdit && (
        <Popup
          open={!!selectedNodeForEdit}
          onClose={() => setSelectedNodeForEdit(null)}
          modal
          className="rounded-lg overflow-hidden p-0 w-full max-w-2xl mx-auto shadow-xl"
          overlayStyle={{ background: 'rgba(0, 0, 0, 0.5)' }}
          contentStyle={{ background: 'transparent', border: 'none', padding: 0 }}
        >
          <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl">
            <UpdateNode
              nodeId={selectedNodeForEdit.id}
              currentVertexpoolId={selectedNodeForEdit.currentVertexpoolId}
              vertexpools={data}
              selectedVertexpool={selectedVertexpool}
              onSuccess={handleNodeEditSuccess}
              onClose={() => setSelectedNodeForEdit(null)}
            />
          </div>
        </Popup>
      )}
    </div>
  );
};

export default Graph;
