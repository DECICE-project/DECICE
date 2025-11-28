import React from 'react';

export const NodePopup = ({ vertexpool, onDeviceClick, onNodeClick }) => {
  if (!vertexpool) {
    return null;
  }

  console.log('Vertexpool data in NodePopup:', {
    id: vertexpool.vertexpool_id,
    nodes: vertexpool.nodes,
    devices: vertexpool.devices,
    labels: vertexpool.labels
  });

  const handleEditClick = (device, e) => {
    e.stopPropagation();
    onDeviceClick(device);
  };

  const handleNodeEditClick = (node, e) => {
    e.stopPropagation();
    onNodeClick({
      ...node,
      id: node.nodename || node.name || node.id // Try all possible name fields
    });
  };

  return (
    <div className="space-y-2">
      {vertexpool.labels?.length > 0 && (
        <div>
          <h2 className="font-semibold text-sm text-gray-600 dark:text-gray-300">Labels:</h2>
          <div className="flex flex-wrap gap-1">
            {vertexpool.labels.map((label) => (
              <span 
                key={label}
                className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100 rounded-full text-xs"
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      )}

      {vertexpool.nodes?.length > 0 && (
        <div>
          <h2 className="font-semibold text-sm text-gray-600 dark:text-gray-300">Nodes:</h2>
          <div className="space-y-1">
            {vertexpool.nodes.map((node) => {
              console.log('Rendering node:', node);
              const nodeName = node.nodename || node.name || node.id;
              return (
                <div 
                  key={nodeName}
                  className="flex items-center justify-between text-sm bg-gray-50 dark:bg-gray-800 p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <span>{nodeName}</span>
                  <button
                    onClick={(e) => handleNodeEditClick(node, e)}
                    className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                  >
                    Edit
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {vertexpool.devices?.length > 0 && (
        <div>
          <h2 className="font-semibold text-sm text-gray-600 dark:text-gray-300">Devices:</h2>
          <div className="space-y-1">
            {vertexpool.devices.map((device) => {
              console.log('Rendering device:', device);
              const deviceName = device.name || device.id;
              return (
                <div 
                  key={deviceName}
                  className="flex items-center justify-between text-sm bg-gray-50 dark:bg-gray-800 p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <span>{deviceName}</span>
                  <button
                    onClick={(e) => handleEditClick(device, e)}
                    className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                  >
                    Edit
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}; 