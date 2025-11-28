// Utility function for edge color based on latency
export const getEdgeColor = (latency) => {
    if (latency > 50) return '#ef4444'; // red
    if (latency > 30) return '#f59e0b'; // yellow
    if (latency > 15) return '#3b82f6'; // blue
    return '#10b981'; // green
};

// Check if dark mode is enabled
const isDarkMode = () => {
    if (typeof window !== 'undefined') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
};

const isDark = isDarkMode();

export let options = {
    interaction: {
        dragNodes: true,
        dragView: true,
        hover: true,
        hideEdgesOnDrag: true,
        keyboard: {
            enabled: true,
            speed: { x: 10, y: 10, zoom: 0.1 },
        },
        zoomView: true
    },
    physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
            gravitationalConstant: -500,
            centralGravity: 0.01,
            springLength: 200,
            springConstant: 0.04,
            damping: 0.3,
            avoidOverlap: 1.0
        },
        stabilization: {
            enabled: true,
            iterations: 1000,
            updateInterval: 50,
            onlyDynamicEdges: false,
            fit: true
        },
        adaptiveTimestep: true,
        timestep: 0.3,
        minVelocity: 0.2,
        maxVelocity: 20,
        wind: { x: 0, y: 0 }
    },
    nodes: {
        fixed: false,
        shape: 'circle',
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
            size: 24,
            color: isDark ? '#e5e7eb' : '#374151',
            face: 'system-ui, sans-serif',
            align: 'center',
            multi: true,
            vadjust: 0
        },
        borderWidth: 2,
        shadow: true,
        color: {
            border: isDark ? '#4b5563' : '#d1d5db',
            background: isDark ? '#1f2937' : '#ffffff',
            highlight: {
                border: '#3b82f6',
                background: '#60a5fa'
            },
            hover: {
                border: '#2563eb',
                background: '#93c5fd'
            }
        }
    },
    edges: {
        color: {
            color: isDark ? '#6b7280' : '#9ca3af',
            highlight: '#3b82f6',
            hover: '#60a5fa',
            inherit: false
        },
        smooth: {
            type: 'continuous',
            roundness: 0.2
        },
        font: {
            size: 12,
            align: 'middle',
            color: isDark ? '#e5e7eb' : '#374151',
            strokeWidth: 2,
            strokeColor: isDark ? '#111827' : '#ffffff'
        },
        width: 1,
        selectionWidth: 2,
        hoverWidth: 2
    }
}