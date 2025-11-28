import { useCallback, useEffect, useState } from "react";
import {
    FALLBACK_CONSORTIUM,
    FALLBACK_EVENTS,
    FALLBACK_NEWS,
} from "./staticContent";

const CONTENT_API_BASE_URL =
    import.meta.env.VITE_CONTENT_API_BASE_URL || "http://0.0.0.0:8000";

/**
 * Generic hook to load static content served by the DECICE content API.
 * Keeps the fetching logic consistent across consortium, events and news widgets.
 */
export function useContentFeed(path) {
    const [data, setData] = useState(null);
    const [status, setStatus] = useState("idle");
    const [error, setError] = useState(null);

    const fallbackData =
        path === "events" ?
        FALLBACK_EVENTS :
        path === "consortium" ?
        FALLBACK_CONSORTIUM :
        path === "news" ?
        FALLBACK_NEWS :
        null;

    const fetchFeed = useCallback(
        async(signal) => {
            setStatus("loading");
            setError(null);
            try {
                const response = await fetch(`${CONTENT_API_BASE_URL}/${path}`, {
                    signal,
                });
                if (!response.ok) {
                    throw new Error(`Unable to load ${path}`);
                }
                const json = await response.json();
                setData(json);
                setStatus("success");
            } catch (err) {
                if (err.name === "AbortError") return;

                // When the remote endpoint is not reachable, fall back to our
                // locally bundled static content so that the homepage remains
                // populated instead of showing an error state.
                if (fallbackData) {
                    setData(fallbackData);
                    setStatus("success");
                    setError(null);
                    return;
                }

                setError(err.message || "Unexpected error");
                setStatus("error");
            }
        }, [path]
    );

    useEffect(() => {
        const controller = new AbortController();
        fetchFeed(controller.signal);
        return () => controller.abort();
    }, [fetchFeed]);

    const refetch = useCallback(() => fetchFeed(), [fetchFeed]);

    return { data, status, error, refetch };
}

export { CONTENT_API_BASE_URL };