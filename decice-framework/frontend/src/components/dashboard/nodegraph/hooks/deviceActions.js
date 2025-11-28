import { useState } from 'react';
import { useSelector } from 'react-redux';

export const useDeviceActions = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const serverIP = useSelector((state) => state.serverIP.watmon_api_ip);

    const addDevice = async(deviceData) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`http://${serverIP}/devices/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(deviceData),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || ` ${response} Failed to add device`);
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    const deleteDevice = async(deviceId) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`http://${serverIP}/devices/${deviceId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to delete device');
            }

            return null;
        } catch (error) {
            setError(error.detail);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    const moveDevice = async(deviceId, newVertexpoolId) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`http://${serverIP}/devices/${deviceId}/move?new_vertexpool_id=${newVertexpoolId}`, {
                method: 'PATCH',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to move device');
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    const updateDevice = async(deviceId, deviceData) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`http://${serverIP}/devices/${deviceId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(deviceData),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to update device');
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    const addLabel = async(deviceId, labelData) => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`http://${serverIP}/devices/${deviceId}/add_label`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(labelData),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to add label');
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
        addDevice,
        deleteDevice,
        moveDevice,
        updateDevice,
        addLabel,
        loading,
        error
    };
};