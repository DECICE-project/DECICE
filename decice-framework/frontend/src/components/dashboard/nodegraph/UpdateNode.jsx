import React, { useState, useEffect } from 'react';
import { useNodeActions } from './hooks/nodeActions';
import { toast } from 'react-toastify';

const UpdateNode = ({ nodeId, currentVertexpoolId, vertexpools, selectedVertexpool, onSuccess, onClose }) => {
    const [targetVertexpool, setTargetVertexpool] = useState('');
    const [customVertexpool, setCustomVertexpool] = useState('');
    const [showCustomInput, setShowCustomInput] = useState(false);
    const { moveNode, loading, error } = useNodeActions();

    const handleMove = async () => {
        const target = showCustomInput ? customVertexpool : targetVertexpool;
        
        if (!target) {
            toast.error('Please select a vertexpool or enter a custom one');
            return;
        }

        try {
            await moveNode(nodeId, target);
            toast.success('Node moved successfully');
            onSuccess?.();
            onClose?.();
        } catch (err) {
            toast.error(err.message || 'Failed to move node');
        }
    };

    const handleVertexpoolChange = (e) => {
        const value = e.target.value;
        if (value === 'custom') {
            setShowCustomInput(true);
            setTargetVertexpool('');
        } else {
            setShowCustomInput(false);
            setTargetVertexpool(value);
        }
    };

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Move Node to Another Vertexpool</h3>
                <button
                    onClick={onClose}
                    className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div className="mb-6">
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Current Location</h4>
                    <div className="flex items-center space-x-2">
                        <span className="text-gray-900 dark:text-gray-100 font-semibold">
                            Node: {nodeId}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400">in</span>
                        <span className="text-gray-900 dark:text-gray-100 font-semibold">
                            VertexPool {selectedVertexpool?.vertexpool_id || currentVertexpoolId}
                        </span>
                    </div>
                </div>
            </div>
            
            <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Select Target Vertexpool
                </label>
                <select
                    value={targetVertexpool}
                    onChange={handleVertexpoolChange}
                    className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                    <option value="">Select a vertexpool</option>
                    <option value="custom">Create New Vertexpool</option>
                    {vertexpools
                        .filter(vp => {
                            const vpId = vp.vertexpool_id || vp.id;
                            return vpId?.toString() !== (selectedVertexpool?.vertexpool_id || currentVertexpoolId)?.toString();
                        })
                        .map(vp => {
                            const vpId = vp.vertexpool_id || vp.id;
                            return (
                                <option key={vpId} value={vpId}>
                                    VertexPool {vpId}
                                </option>
                            );
                        })}
                </select>

                {showCustomInput && (
                    <div className="mt-2">
                        <input
                            type="text"
                            value={customVertexpool}
                            onChange={(e) => setCustomVertexpool(e.target.value)}
                            placeholder="Enter new vertexpool ID"
                            className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                    </div>
                )}
            </div>

            <button
                onClick={handleMove}
                disabled={loading || (!targetVertexpool && !customVertexpool)}
                className={`w-full py-2 px-4 rounded-md text-white ${
                    loading || (!targetVertexpool && !customVertexpool)
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                }`}
            >
                {loading ? 'Moving...' : 'Move Node'}
            </button>

            {error && (
                <p className="mt-2 text-red-600 text-sm">
                    {error}
                </p>
            )}
        </div>
    );
};

export default UpdateNode;
