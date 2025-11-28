import { useState } from 'react';
import { useSelector } from 'react-redux';

export const useNodeActions = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const serverIP = useSelector((state) => state.serverIP.watmon_api_ip);

    const moveNode = async(nodeId, newVertexpoolId) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`http://${serverIP}/nodes/${nodeId}/move?new_vertexpool_id=${newVertexpoolId}`, {
                method: 'PATCH',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to move node');
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    return {
        moveNode,
        loading,
        error
    };
};