import { useEffect, useMemo, useState } from 'react';
import { useSelector } from 'react-redux';

// Polling interval in milliseconds
const POLLING_INTERVAL = 2000;

export const useJobListService = () => {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const serverIP = useSelector((state) => state.serverIP.value);
    const token = useSelector((state) => state.authToken.value);

    // Normalize server IP once to prevent refetch loops
    const normalizedServerIP = useMemo(() => {
        if (!serverIP) return null;
        return serverIP.replace(/^https?:\/\//i, '').replace(/\/$/, '');
    }, [serverIP]);

    useEffect(() => {
        const fetchJobs = async() => {
            try {
                if (!normalizedServerIP || !token) {
                    throw new Error('Missing server IP or auth token');
                }

                const response = await fetch(`http://${normalizedServerIP}/v1/workflow/task/`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });
                if (!response.ok) {
                    throw new Error('Failed to fetch jobs');
                }
                const data = await response.json();
                setJobs(data);
                setLoading(false);
            } catch (err) {
                setError(err.message);
                setLoading(false);
            }
        };

        // Initial fetch
        fetchJobs();

        // Set up polling
        const intervalId = setInterval(fetchJobs, POLLING_INTERVAL);

        // Cleanup interval on component unmount
        return () => clearInterval(intervalId);
    }, [normalizedServerIP, token]); // Fetch again if base URL or token changes

    return { jobs, loading, error };
};