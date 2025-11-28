/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable no-unused-vars */
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Network } from 'vis-network';
import Popup from 'reactjs-popup';
import 'reactjs-popup/dist/index.css';
// import data from "./try.json";
import {useSelector } from "react-redux";
import { LoadingSpinner } from '../../../common/LoadingSpinner';
import { ErrorMessage } from '../../../common/ErrorMessage';
import { scaledSigmoid, getNetworkOptions, getEdgeColor } from './networkConfig';

const NetworkGraph = () => {
  const serverIP = useSelector((state) => state.serverIP.watmon_api_ip);
  const container = useRef(null);
  const innerContainer = useRef(null);
  const networkRef = useRef(null);
  const searchInputRef = useRef(null);
  const [state, setState] = useState({
    isOpen: false,
    selectedNode: null,
    popupData: { visible: false, x: 0, y: 0, content: '' },
    loading: true,
    error: null,
    nodes: null,
    edges: null,
    data: null,
    innerEdges: null
  });

  // Use system preference for dark mode
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = (e) => setIsDark(e.matches);
      mediaQuery.addListener(handler);
      return () => mediaQuery.removeListener(handler);
    }
  }, []);

  const options = useMemo(() => getNetworkOptions(isDark), [isDark]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSearchNode, setSelectedSearchNode] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [groupingEnabled, setGroupingEnabled] = useState(false);
  const [showLatencyStats, setShowLatencyStats] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [animationEnabled, setAnimationEnabled] = useState(true);
  const [selectedNodeDetails, setSelectedNodeDetails] = useState(null);
  const [showNodeDetails, setShowNodeDetails] = useState(false);
  const [isControlsVisible, setIsControlsVisible] = useState(true);

  // Calculate latency statistics
  const latencyStats = useMemo(() => {
    if (!state.edges) return null;
    
    const latencies = state.edges.map(edge => parseFloat(edge.label.replace(' ms', '')));
    return {
      min: Math.min(...latencies),
      max: Math.max(...latencies),
      avg: latencies.reduce((a, b) => a + b, 0) / latencies.length,
      highLatency: latencies.filter(l => l > 100).length,
      totalConnections: latencies.length
    };
  }, [state.edges]);


  // Memoize filtered edges based on selected node
  const filteredEdges = useMemo(() => {
    if (!state.edges) return state.edges;
    
    let edges = state.edges;
    
    // Filter by selected node
    if (selectedSearchNode) {
      edges = edges.filter(edge => 
        edge.from === selectedSearchNode.id || edge.to === selectedSearchNode.id
      );
    }
    
    // Add color based on latency
    return edges.map(edge => ({
      ...edge,
      color: getEdgeColor(parseFloat(edge.label.replace(' ms', ''))),
      title: `Latency: ${edge.label}\nRoot: ${edge.from}\nTarget: ${edge.to}`
    }));
  }, [state.edges, selectedSearchNode]);

  // Memoize filtered nodes based on search
  const filteredNodes = useMemo(() => {
    if (!state.nodes) return state.nodes;
    
    if (searchTerm) {
      const results = state.nodes.filter(node => 
        node.label.toLowerCase().includes(searchTerm.toLowerCase())
      ).map(node => ({
        ...node,
        connectionCount: state.edges?.filter(edge => 
          edge.from === node.id || edge.to === node.id
        ).length || 0
      }));
      
      setSearchResults(results);
      setShowResults(true);
      return results;
    }
    
    if (selectedSearchNode) {
      // Show only the selected node and its connected nodes
      const connectedNodeIds = new Set();
      connectedNodeIds.add(selectedSearchNode.id);
      
      state.edges?.forEach(edge => {
        if (edge.from === selectedSearchNode.id) {
          connectedNodeIds.add(edge.to);
        }
        if (edge.to === selectedSearchNode.id) {
          connectedNodeIds.add(edge.from);
        }
      });
      
      return state.nodes.filter(node => connectedNodeIds.has(node.id));
    }
    
    setSearchResults([]);
    setShowResults(false);
    return state.nodes;
  }, [state.nodes, searchTerm, selectedSearchNode, state.edges]);

  // Group nodes by type
  const groupedNodes = useMemo(() => {
    if (!state.nodes || !groupingEnabled) return state.nodes;
    
    return state.nodes.map(node => ({
      ...node,
      group: node.shape === 'triangle' ? 'devices' : 'nodes'
    }));
  }, [state.nodes, groupingEnabled]);

  // Animation settings
  const animationOptions = useMemo(() => ({
    animation: animationEnabled ? {
      enabled: true,
      duration: 1000,
      easingFunction: 'easeInOutQuad'
    } : false
  }), [animationEnabled]);

  // Fetch functions
  const fetchNodes = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      const response = await fetch(`http://${serverIP}/metric_api/vertexpools`);
      if (!response.ok) {
        throw new Error('Failed to fetch nodes');
      }
      const data = await response.json();
      setState(prev => ({ ...prev, data }));
      
      const node_vertices = [];
      const nodeConfig = {
        size: 30,
        widthConstraint: {
          minimum: 100,
          maximum: 100
        },
        heightConstraint: {
          minimum: 100,
          maximum: 100
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

      const triangleConfig = {
        ...nodeConfig,
        font: {
          ...nodeConfig.font,
          vadjust: -70
        },
        widthConstraint: {
          minimum: 100,
          maximum: 100
        },
        heightConstraint: {
          minimum: 100,
          maximum: 100
        }
      };

      data.forEach((item) => {
        item.nodes.forEach((node) => {
          node_vertices.push({
            id: node.name,
            label: node.name,
            shape: 'circle',
            ...nodeConfig
          });
        });

        item.devices.forEach((device) => {
          node_vertices.push({
            id: device.name,
            label: device.name,
            shape: 'triangle',
            ...triangleConfig
          });
        });
      });
      
      setState(prev => ({ ...prev, nodes: node_vertices, loading: false }));
      return true;
    } catch (err) {
      console.error('Error fetching nodes:', err);
      setState(prev => ({ ...prev, error: err.message, loading: false }));
      return false;
    }
  }, [serverIP]);

  const fetchEdges = useCallback(async () => {
    try {
      const response = await fetch(`http://${serverIP}/metric_api/raw_edges`);
      if (!response.ok) {
        throw new Error(`Failed to fetch edges: ${response.statusText}`);
      }

      const datalinks = await response.json();
      const edgesPlain = datalinks
        .filter((link) => link.vertex_b !== link.vertex_a)
        .map((link) => ({
          from: link.vertex_a,
          to: link.vertex_b,
          label: `${link.value.toFixed(2)} ms`,
          title: `From`,
          length: scaledSigmoid(link.value),
        }));
      setState(prev => ({ ...prev, edges: edgesPlain, loading: false }));
      return true;
    } catch (err) {
      console.error('Error fetching edges:', err);
      setState(prev => ({ ...prev, error: err.message, loading: false }));
      return false;
    }
  }, [serverIP]);

  const refreshNetwork = useCallback(async () => {
    const nodesSuccess = await fetchNodes();
    if (nodesSuccess) {
      await fetchEdges();
    }
  }, [fetchNodes, fetchEdges]);

  // Initial data fetch
  useEffect(() => {
    refreshNetwork();
  }, [refreshNetwork]);

  useEffect(() => {
    if (container.current && state.nodes && state.edges) {
      const network = new Network(container.current, { nodes: state.nodes, edges: state.edges }, options);
      network.on('click', function (params) {
        if (params.nodes.length > 0) {
          setState(prev => ({ ...prev, popupData: { ...prev.popupData, visible: false } }));
          const nodeId = Number(params.nodes[0]); // Convert nodeId to number
          const selected = state.data.find((pool) => pool.id === nodeId);
          setState(prev => ({ ...prev, selectedNode: selected }));
          if (selected) {
            setState(prev => ({ ...prev, isOpen: true }));
          }
        }
      });
      network.on('hoverNode', function (params) {
        const { pointer, node: vp } = params;
        const vertexpool = returnDeviceList(vp);
        const d_nodes = vertexpool.nodes;
        const devices = vertexpool.devices;

        setState(prev => ({
          ...prev,
          popupData: {
            ...prev.popupData,
            visible: true,
            x: pointer.DOM.x,
            y: pointer.DOM.y,
            content: (
              <div className="">
                VertexPoolID: {vp}
                <div>
                  <h1 className="font-semibold ">Labels:</h1>
                  {vertexpool.labels.map((label) => (
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
          },
        }));
      });

      // Handle blurNode event to hide the popup
      network.on('blurNode', function () {
        setState(prev => ({ ...prev, popupData: { ...prev.popupData, visible: false } }));
      });
    }
  }, [state.nodes, state.edges, state.data]);

  // Fetch inner edges when selectedNode changes
  useEffect(() => {
    if (state.selectedNode) {
      const fetchInnerEdges = async () => {
        try {
          const response = await fetch(
            `http://${serverIP}/metric_api/raw_edges?vertexpool_id=${state.selectedNode.id}`
          );
          if (!response.ok) {
            throw new Error('Failed to fetch inner edges');
          }
          const data = await response.json();
          setState(prev => ({ ...prev, innerEdges: data }));
        } catch (err) {
          console.log('Error fetching inner edges: ', err);
          setState(prev => ({ ...prev, error: err.message }));
        }
      };
      fetchInnerEdges();
    } else {
      setState(prev => ({ ...prev, innerEdges: null })); // Reset inner edges when no node is selected
    }
  }, [state.selectedNode, state.isOpen]);

  // Render inner network when innerEdges are fetched
  useEffect(() => {
    if (innerContainer.current && state.selectedNode && state.innerEdges && state.isOpen) {
      console.log('selectedNode: ', state.selectedNode);
      // Clear the inner container
      innerContainer.current.innerHTML = '';

      // Determine the source of inner nodes
      let innerNodesData = [];
      if (state.selectedNode.nodes && state.selectedNode.nodes.length > 0) {
        innerNodesData = state.selectedNode.nodes;
      } else if (state.selectedNode.devices && state.selectedNode.devices.length > 0) {
        innerNodesData = state.selectedNode.devices;
      } else {
        innerNodesData = [];
      }

    }
  }, [state.selectedNode, state.innerEdges, state.isOpen]);

  function returnDeviceList(nodeId) {
    const selected = state.data.find((pool) => pool.id === nodeId);
    return selected;
  }

  const renderPopupContent = useMemo(() => {
    if (!state.popupData.visible) return null;
    
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 max-w-sm">
        <div className="text-lg font-bold mb-2 text-gray-900 dark:text-white">
          VertexPool ID: {state.popupData.content.props.children[0]}
        </div>
        <div className="space-y-4">
          {state.popupData.content.props.children.slice(1).map((section, idx) => {
            if (!section) return null;
            return (
              <div key={idx} className="border-t pt-2 first:border-t-0 first:pt-0">
                {section}
              </div>
            );
          })}
        </div>
      </div>
    );
  }, [state.popupData]);

  const renderInnerNetwork = useCallback(() => {
    return (
      <Popup
        open={state.isOpen}
        onClose={() => setState(prev => ({ ...prev, isOpen: false }))}
        modal
        closeOnDocumentClick
        className="inner-network-popup"
      >
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 w-[80vw] h-[80vh] max-w-7xl max-h-[800px]">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              {state.selectedNode?.id ? `VertexPool ${state.selectedNode.id} Details` : 'Network Details'}
            </h2>
            <button
              onClick={() => setState(prev => ({ ...prev, isOpen: false }))}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div ref={innerContainer} className="w-full h-[calc(100%-3rem)]" />
        </div>
      </Popup>
    );
  }, [state.isOpen, state.selectedNode]);

  // Node details panel component
  const NodeDetailsPanel = () => {
    if (!selectedNodeDetails) return null;

    return (
      <div className="absolute bottom-0 right-0 z-10 p-4 m-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Details
          </h3>
          <button
            onClick={() => setShowNodeDetails(false)}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">ID:</label>
            <div className="mt-1 text-gray-900 dark:text-white">{selectedNodeDetails.id}</div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Type:</label>
            <div className="mt-1 text-gray-900 dark:text-white">
              {selectedNodeDetails.shape === 'triangle' ? 'Device' : 'Node'}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Connections:</label>
            <div className="mt-1 text-gray-900 dark:text-white">
              {state.edges?.filter(edge => 
                edge.from === selectedNodeDetails.id || edge.to === selectedNodeDetails.id
              ).length || 0}
            </div>
          </div>
          {selectedNodeDetails.labels && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Labels:</label>
              <div className="mt-1 flex flex-wrap gap-2">
                {selectedNodeDetails.labels.map((label, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 text-xs rounded-full bg-blue-100 dark:bg-blue-900 
                             text-blue-800 dark:text-blue-100"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Network controls component
  const NetworkControls = () => {
    if (!isControlsVisible) {
      return (
        <div className="absolute top-0 left-0 z-10 p-4">
          <button
            onClick={() => setIsControlsVisible(true)}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
            </svg>
          </button>
        </div>
      );
    }

    return (
      <div className="absolute top-0 left-0 z-10 p-4 space-y-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 space-y-4">
          <div className="flex justify-between items-start -mt-1">
            <div className="flex-1 pr-2">
              {/* Search */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Search
                  </label>
                  <button
                    onClick={() => setIsControlsVisible(false)}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                    title="Kontrol Panelini Gizle"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <div className="relative w-full">
                  <div className="relative w-full">
                    <input
                      ref={searchInputRef}
                      type="text"
                      value={searchTerm}
                      onChange={(e) => {
                        const input = e.target;
                        const cursorPosition = input.selectionStart;
                        setSearchTerm(e.target.value);
                        setSelectedSearchNode(null);
                        // Restore cursor position after state update
                        setTimeout(() => {
                          if (searchInputRef.current) {
                            searchInputRef.current.focus();
                            searchInputRef.current.setSelectionRange(cursorPosition, cursorPosition);
                          }
                        }, 0);
                      }}
                      placeholder="Enter node or device name..."
                      className="w-full px-3 py-1.5 pl-10 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg 
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-white 
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                  </div>
                </div>
                {selectedSearchNode && (
                  <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg text-sm w-full">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-blue-700 dark:text-blue-300">
                          Selected {selectedSearchNode.shape === 'triangle' ? 'Device' : 'Node'}:
                        </span>
                        <span className="text-blue-600 dark:text-blue-200">
                          {selectedSearchNode.label}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedSearchNode(null);
                          if (networkRef.current) {
                            networkRef.current.fit();
                          }
                        }}
                        className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-200"
                        title="Clear selection"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}
                {showResults && searchResults.length > 0 && (
                  <div className="absolute z-10 w-full max-w-[calc(100%-20%)] mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {searchResults.map((result, index) => (
                      <div
                        key={index}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
                        onClick={() => {
                          setSelectedSearchNode(result);
                          setSearchTerm('');
                          setShowResults(false);
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {result.label}
                          </div>
                          <div className="text-xs px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100">
                            {result.shape === 'triangle' ? 'Device' : 'Node'}
                          </div>
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          Connections: {result.connectionCount}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
           
          </div>

          {/* Latency Statistics */}
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Latency Statictics
              </h3>
              <button
                onClick={() => setShowLatencyStats(!showLatencyStats)}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                {showLatencyStats ? 'Hide Statictics' : 'Show Statictics'}
              </button>
            </div>
            
            {showLatencyStats && latencyStats && (
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-gray-500 dark:text-gray-400">Min Latency</div>
                  <div className="font-medium">{latencyStats.min.toFixed(2)}ms</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-gray-500 dark:text-gray-400">Max Latency</div>
                  <div className="font-medium">{latencyStats.max.toFixed(2)}ms</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-gray-500 dark:text-gray-400">Average</div>
                  <div className="font-medium">{latencyStats.avg.toFixed(2)}ms</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="text-gray-500 dark:text-gray-400">High Latency</div>
                  <div className="font-medium text-red-500">{latencyStats.highLatency}</div>
                </div>
              </div>
            )}
          </div>

          {/* Latency Legend */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Delay Colors
            </h3>
            <div className="space-y-1 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-[#10b981]"></div>
                <span className="text-gray-600 dark:text-gray-400">0-15ms</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-[#3b82f6]"></div>
                <span className="text-gray-600 dark:text-gray-400">15-30ms</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-[#f59e0b]"></div>
                <span className="text-gray-600 dark:text-gray-400">30-50ms</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-[#ef4444]"></div>
                <span className="text-gray-600 dark:text-gray-400">{'>'}50ms</span>
              </div>
            </div>
          </div>

          {/* Zoom Controls */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Zoom
            </label>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  if (networkRef.current) {
                    const newZoom = networkRef.current.getScale() * 0.8;
                    networkRef.current.moveTo({ scale: newZoom });
                    setZoomLevel(newZoom);
                  }
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                title="Zoom Out"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              </button>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {Math.round(zoomLevel * 100)}%
              </div>
              <button
                onClick={() => {
                  if (networkRef.current) {
                    const newZoom = networkRef.current.getScale() * 1.2;
                    networkRef.current.moveTo({ scale: newZoom });
                    setZoomLevel(newZoom);
                  }
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                title="Zoom In"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>

          {/* Node Statistics */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Network Statistics
            </h3>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <div>Total Node: {state.nodes?.length || 0}</div>
              <div>Total Connection: {state.edges?.length || 0}</div>
              <div>Devices: {state.nodes?.filter(n => n.shape === 'triangle').length || 0}</div>
              <div>Nodes: {state.nodes?.filter(n => n.shape !== 'triangle').length || 0}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Update network when nodes are filtered or grouped
  useEffect(() => {
    if (container.current && (filteredNodes || groupedNodes) && filteredEdges) {
        const nodes = groupingEnabled ? groupedNodes : filteredNodes;
        const network = new Network(
            container.current,
            { nodes, edges: filteredEdges },
            {
                ...options,
                ...animationOptions,
                groups: groupingEnabled ? {
                    devices: {
                        color: { background: '#ef4444', border: '#dc2626' },
                        shape: 'triangle',
                        size: 30,
                        widthConstraint: {
                            minimum: 40,
                            maximum: 40
                        },
                        heightConstraint: {
                            minimum: 40,
                            maximum: 40
                        },
                        margin: 5,
                        fixed: {
                            size: true
                        },
                        font: {
                            size: 12,
                            align: 'center',
                            multi: true,
                            vadjust: -30
                        }
                    },
                    nodes: {
                        color: { background: '#3b82f6', border: '#2563eb' },
                        shape: 'circle',
                        size: 30,
                        widthConstraint: {
                            minimum: 30,
                            maximum: 30
                        },
                        heightConstraint: {
                            minimum: 30,
                            maximum: 30
                        },
                        margin: 5,
                        fixed: {
                            size: true
                        },
                        font: {
                            size: 12,
                            align: 'center',
                            multi: true,
                            vadjust: 0
                        }
                    }
                } : undefined
            }
        );

        networkRef.current = network;

        // Set zoom level initially
        setTimeout(() => {
            network.moveTo({
                scale: 0.5,
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
            
            network.startSimulation();
            setTimeout(() => {
                network.stopSimulation();
            }, 5000);  
        }, 1000);

        // Event listeners
        network.on('zoom', () => {
            setZoomLevel(network.getScale());
        });

        network.on('stabilizationIterationsDone', () => {
            network.setOptions({ physics: { enabled: false } });
        });

        network.on('selectNode', (params) => {
            const nodeId = params.nodes[0];
            const selectedNode = nodes.find(n => n.id === nodeId);
            if (selectedNode) {
                setSelectedNodeDetails(selectedNode);
                setShowNodeDetails(true);
            }
        });

        network.on('deselectNode', () => {
            setShowNodeDetails(false);
        });

        return () => {
            network.destroy();
        };
    }
  }, [filteredNodes, groupedNodes, filteredEdges, groupingEnabled, options, animationOptions]);

  // Add loading and error states
  if (state.loading) {
    return <LoadingSpinner />;
  }

  if (state.error) {
    return <ErrorMessage message={state.error} />;
  }

  return (
    <div className="relative w-full h-full">
      <NetworkControls />
      <div className="absolute top-0 right-0 z-10 p-4 flex flex-col gap-2">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-2 flex flex-col gap-2">
          <button
            onClick={refreshNetwork}
            className="p-2 w-40 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg tooltip flex items-center justify-start gap-2 text-sm"
            title="Refresh Network"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
            </svg>
            <span>Refresh Network</span>
          </button>
          <button
            onClick={() => networkRef.current?.fit()}
            className="p-2 w-40 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg tooltip flex items-center justify-start gap-2 text-sm"
            title="Reset View"
          >
            <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
            <span>Reset View</span>
          </button>
        </div>
      </div>
      <div ref={container} className="h-[70vh] bg-white dark:bg-gray-900" />
      {state.popupData.visible && (
        <div
          style={{
            position: 'absolute',
            top: state.popupData.y,
            left: state.popupData.x,
            zIndex: 1000,
          }}
        >
          {renderPopupContent}
        </div>
      )}
      {showNodeDetails && <NodeDetailsPanel />}
      {renderInnerNetwork()}
    </div>
  );
};

export default NetworkGraph;
// Add this CSS to your styles file
const styles = `
.inner-network-popup {
    &-content {
        padding: 0;
        border: none;
        background: transparent;
        width: auto;
        max-width: none;
    }

    &-overlay {
        background: rgba(0, 0, 0, 0.5);
    }
}
`;

