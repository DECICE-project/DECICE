import React, { useState } from 'react';
import { useDeviceActions } from './hooks/deviceActions';
import { toast } from 'react-toastify';

export const DevicePopup = ({ device, onClose, onSuccess, vertexPools }) => {
  const [formData, setFormData] = useState({
    name: device.name,
    ip: device.ip,
    labels: device.labels ? device.labels.map(label => {
      const [key, value] = label.split(':');
      return { label_key: key, label_value: value };
    }) : []
  });
  const [showAddLabel, setShowAddLabel] = useState(false);
  const [newLabel, setNewLabel] = useState({ label_key: '', label_value: '' });
  const [targetVertexpool, setTargetVertexpool] = useState('');
  const [customVertexPoolId, setCustomVertexPoolId] = useState('');
  const { deleteDevice, moveDevice, updateDevice, loading, error, addLabel } = useDeviceActions();

  // Toast notification helper function
  const showToast = (message, type = 'success', duration = 3000) => {
    const options = {
      position: "bottom-right",
      autoClose: duration,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    };

    if (type === 'success') {
      toast.success(message, options);
    } else {
      toast.error(message, options);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this device?')) {
      try {
        await deleteDevice(device.id);
        showToast('Device deleted successfully!');
        onSuccess();
        onClose();
      } catch (err) {
        console.error('Failed to delete device:', err);
        showToast(`Failed to delete device: ${err.message}`, 'error', 5000);
      }
    }
  };

  const handleMove = async (poolId) => {
    if (!poolId) return;
    try {
      await moveDevice(device.id, poolId);
      showToast('Device moved successfully!');
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to move device:', err);
      showToast(`Failed to move device: ${err.message}`, 'error', 5000);
    }
  };

  const handleAddLabel = async () => {
    if (newLabel.label_key && newLabel.label_value) {
      try {
        await addLabel(device.id, newLabel);
        setFormData({
          ...formData,
          labels: [...formData.labels, newLabel]
        });
        setNewLabel({ label_key: '', label_value: '' });
        showToast('Label added successfully!');
      } catch (err) {
        console.error('Failed to add label:', err);
        showToast(`Failed to add label: ${err.message}`, 'error', 5000);
      }
    }
  };

  const handleRemoveLabel = (index) => {
    setFormData({
      ...formData,
      labels: formData.labels.filter((_, i) => i !== index)
    });
  };

  const handleUpdate = async () => {
    try {
      const deviceData = {
        name: formData.name,
        ip: formData.ip,
        labels: formData.labels
      };
      await updateDevice(device.id, deviceData);
      showToast('Device updated successfully!');
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to update device:', err);
      showToast(`Failed to update device: ${err.message}`, 'error', 5000);
    }
  };

  return (
    <div className="p-4 space-y-4 bg-white dark:bg-gray-800">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Device Management
        </h2>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          ✕
        </button>
      </div>

      {error && (
        <div className="bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Device Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">IP Address</label>
          <input
            type="text"
            value={formData.ip}
            onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
          />
        </div>

        <div>
          {formData.labels.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Labels</label>
              <div className="mt-2 space-y-2">
                {formData.labels.map((label, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-900 dark:text-gray-100">
                      {label.label_key}:{label.label_value}
                    </span>
                    <button
                      onClick={() => handleRemoveLabel(index)}
                      className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {(showAddLabel || formData.labels.length > 0) && (
            <div className="mt-4">
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Key"
                  value={newLabel.label_key}
                  onChange={(e) => setNewLabel({ ...newLabel, label_key: e.target.value })}
                  className="block w-1/2 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
                />
                <input
                  type="text"
                  placeholder="Value"
                  value={newLabel.label_value}
                  onChange={(e) => setNewLabel({ ...newLabel, label_value: e.target.value })}
                  className="block w-1/2 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
                />
                <button
                  onClick={handleAddLabel}
                  className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
                >
                  Add
                </button>
              </div>
            </div>
          )}
          
          {!showAddLabel && formData.labels.length === 0 && (
            <button
              onClick={() => setShowAddLabel(true)}
              className="mt-2 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            >
              + Add Label
            </button>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Move to VertexPool</label>
          <div className="mt-2">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Current VertexPool: {device.vertexpool_id} 
              {vertexPools.find(p => p.vertexpool_id === device.vertexpool_id)?.name && 
                ` (${vertexPools.find(p => p.vertexpool_id === device.vertexpool_id).name})`
              }
            </p>
            <div className="flex flex-col space-y-4">
              <select
                value={targetVertexpool}
                onChange={(e) => setTargetVertexpool(e.target.value)}
                className="block w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
              >
                <option value="">Select VertexPool</option>
                <option value="custom">Enter Custom ID</option>
                {vertexPools
                  .filter(pool => pool.vertexpool_id !== device.vertexpool_id)
                  .map(pool => (
                    <option key={pool.vertexpool_id} value={pool.vertexpool_id}>
                      VertexPool {pool.vertexpool_id} {pool.name ? `(${pool.name})` : ''}
                    </option>
                  ))}
              </select>

              {targetVertexpool === 'custom' && (
                <input
                  type="text"
                  placeholder="Enter VertexPool ID"
                  value={customVertexPoolId}
                  onChange={(e) => setCustomVertexPoolId(e.target.value)}
                  className="block w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
                />
              )}

              <button
                onClick={() => handleMove(targetVertexpool === 'custom' ? customVertexPoolId : targetVertexpool)}
                disabled={loading || (!targetVertexpool || (targetVertexpool === 'custom' && !customVertexPoolId))}
                className="w-full px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-green-600 dark:hover:bg-green-700"
              >
                Move Device
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end space-x-2">
        <button
          onClick={handleUpdate}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
        >
          Update Device
        </button>
        <button
          onClick={handleDelete}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
        >
          Delete Device
        </button>
      </div>
    </div>
  );
}; 