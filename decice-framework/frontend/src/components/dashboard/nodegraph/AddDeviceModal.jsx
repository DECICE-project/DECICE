import React, { useState } from 'react';
import Popup from 'reactjs-popup';
import { useDeviceActions } from './hooks/deviceActions';

const initialFormState = {
  name: '',
  ip: '',
  labels: [],
  vertexpool_id: null
};

export const AddDeviceModal = ({ isOpen, onClose, onSuccess }) => {
  const [deviceForm, setDeviceForm] = useState(initialFormState);
  const { addDevice, loading, error } = useDeviceActions();

  const handleAddDevice = async (e) => {
    e.preventDefault();
    
    // Create a copy of deviceForm without vertexpool_id if it's null
    const deviceData = { ...deviceForm };
    if (deviceData.vertexpool_id === null) {
      delete deviceData.vertexpool_id;
    }
    
    try {
      await addDevice(deviceData);
      setDeviceForm(initialFormState);
      if (onSuccess) onSuccess();
      onClose();
    } catch (error) {
      // Error is already handled by the hook
    }
  };

  const addLabel = () => {
    setDeviceForm({
      ...deviceForm,
      labels: [...deviceForm.labels, { label_key: '', label_value: '' }]
    });
  };

  const removeLabel = (index) => {
    const newLabels = deviceForm.labels.filter((_, i) => i !== index);
    setDeviceForm({
      ...deviceForm,
      labels: newLabels
    });
  };

  const updateLabel = (index, field, value) => {
    const newLabels = [...deviceForm.labels];
    newLabels[index][field] = value;
    setDeviceForm({
      ...deviceForm,
      labels: newLabels
    });
  };

  return (
    <Popup
      open={isOpen}
      onClose={onClose}
      modal
      className="rounded-lg overflow-hidden"
      contentStyle={{ width: 'auto', maxWidth: '400px', minWidth: '400px', padding: '0', background: 'none', border: 'none' }}
      overlayStyle={{ background: 'rgba(0, 0, 0, 0.5)' }}
    >
      <div className="bg-white dark:bg-gray-900 p-3 rounded-lg shadow-xl max-w-full max-h-[80vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">Add New Device</h2>
        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}
        <form onSubmit={handleAddDevice} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
            <input
              type="text"
              value={deviceForm.name}
              onChange={(e) => setDeviceForm({...deviceForm, name: e.target.value})}
              className="mt-1 block w-full rounded-md bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">IP Address</label>
            <input
              type="text"
              value={deviceForm.ip}
              onChange={(e) => setDeviceForm({...deviceForm, ip: e.target.value})}
              className="mt-1 block w-full rounded-md bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Vertexpool ID</label>
            <input
              type="number"
              value={deviceForm.vertexpool_id}
              onChange={(e) => setDeviceForm({...deviceForm, vertexpool_id: parseInt(e.target.value)})}
              className="mt-1 block w-full rounded-md bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Labels</label>
              <button
                type="button"
                onClick={addLabel}
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                + Add Label
              </button>
            </div>
            {deviceForm.labels.map((label, index) => (
              <div key={index} className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={label.label_key}
                  onChange={(e) => updateLabel(index, 'label_key', e.target.value)}
                  placeholder="Key"
                  className="mt-1 block w-full rounded-md bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500"
                />
                <input
                  type="text"
                  value={label.label_value}
                  onChange={(e) => updateLabel(index, 'label_value', e.target.value)}
                  placeholder="Value"
                  className="mt-1 block w-full rounded-md bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500"
                />
                {index > 0 && (
                  <button
                    type="button"
                    onClick={() => removeLabel(index)}
                    className="mt-1 text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Adding...
                </>
              ) : (
                'Add Device'
              )}
            </button>
          </div>
        </form>
      </div>
    </Popup>
  );
}; 