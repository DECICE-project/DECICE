import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSelector } from "react-redux";
import {
  Button,
  Spinner,
  Tooltip,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure
} from "@nextui-org/react";
import { Icon } from "@iconify/react";
import ReactFlow, { Background, Controls, MiniMap, useEdgesState, useNodesState, BaseEdge, getSmoothStepPath, Handle, Position } from "reactflow";
import "reactflow/dist/style.css";
import "./workflow.css";
import { toast } from "react-toastify";

const normalizeStatus = (status) => {
  if (status == null) return "UNKNOWN";
  return String(status).trim().toUpperCase();
};

const EDGE_STYLE = { stroke: "#2c384d", strokeWidth: 2 };
const EDGE_STYLE_BY_STATUS = {
  RUNNING: { stroke: "#2563eb", strokeWidth: 2.5 },
  SUCCEEDED: { stroke: "#16a34a", strokeWidth: 2.5 },
  FAILED: { stroke: "#ef4444", strokeWidth: 2.5 },
  CANCELLED: { stroke: "#6b7280", strokeWidth: 2.5 },
};
const DEFAULT_PATH_OPTIONS = { borderRadius: 24, offset: 24 };
const TASK_TYPE_META = {
  job: { label: "Job", icon: "mdi:briefcase-outline" },
  deployment: { label: "Deployment", icon: "mdi:rocket-launch-outline" },
  hpc_job: { label: "HPC Job", icon: "mdi:chip" },
};
const DEFAULT_TASK_META = { label: "Task", icon: "mdi:cube-outline" };

const STATUS_META = {
  SUCCEEDED: {
    label: "Succeeded",
    dot: "bg-emerald-500",
    badge: "border border-emerald-300/60 bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:border-emerald-400/40 dark:text-emerald-100",
  },
  RUNNING: {
    label: "Running",
    dot: "bg-blue-500",
    badge: "border border-blue-300/60 bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:border-blue-400/40 dark:text-blue-100",
  },
  PROGRESSING: {
    label: "Progressing",
    dot: "bg-sky-500",
    badge: "border border-sky-300/60 bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:border-sky-400/40 dark:text-sky-100",
  },
  FAILED: {
    label: "Failed",
    dot: "bg-rose-500",
    badge: "border border-rose-300/60 bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:border-rose-400/40 dark:text-rose-100",
  },
  CANCELLED: {
    label: "Cancelled",
    dot: "bg-zinc-500",
    badge: "border border-zinc-300/60 bg-zinc-100 text-zinc-600 dark:bg-zinc-500/20 dark:border-zinc-400/40 dark:text-zinc-100",
  },
  PENDING: {
    label: "Pending",
    dot: "bg-amber-500",
    badge: "border border-amber-300/60 bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:border-amber-400/40 dark:text-amber-100",
  },
  QUEUED: {
    label: "Queued",
    dot: "bg-amber-500",
    badge: "border border-amber-300/60 bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:border-amber-400/40 dark:text-amber-100",
  },
  PENDING_DATA: {
    label: "Pending Data",
    dot: "bg-orange-500",
    badge: "border border-orange-300/60 bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:border-orange-400/40 dark:text-orange-100",
  },
  WAITING: {
    label: "Waiting",
    dot: "bg-orange-400",
    badge: "border border-orange-200/70 bg-orange-50 text-orange-600 dark:bg-orange-500/15 dark:border-orange-400/40 dark:text-orange-100",
  },
  READY: {
    label: "Ready",
    dot: "bg-cyan-500",
    badge: "border border-cyan-300/60 bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:border-cyan-400/40 dark:text-cyan-100",
  },
  SCHEDULING: {
    label: "Scheduling",
    dot: "bg-indigo-500",
    badge: "border border-indigo-300/60 bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:border-indigo-400/40 dark:text-indigo-100",
  },
  UNKNOWN: {
    label: "Unknown",
    dot: "bg-gray-400",
    badge: "border border-gray-300/70 bg-gray-100 text-gray-600 dark:bg-gray-500/15 dark:border-gray-400/40 dark:text-gray-200",
  },
};

function getStatusMeta(status) {
  const key = normalizeStatus(status);
  return STATUS_META[key] || STATUS_META.UNKNOWN;
}

function getTaskTypeMeta(type) {
  const key = String(type || "").toLowerCase();
  return TASK_TYPE_META[key] || DEFAULT_TASK_META;
}

function DefaultNode({ data }) {
  const statusMeta = getStatusMeta(data?.status);
  const typeMeta = getTaskTypeMeta(data?.type);
  return (
    <Tooltip
      placement="top"
      content={
        <div className="text-xs max-w-xs">
          <div className="font-semibold mb-1">{data?.name}</div>
          {typeMeta ? (
            <div className="flex items-center gap-1">
              <span>Type:</span>
              <Icon icon={typeMeta.icon} className="w-3.5 h-3.5 text-default-500" />
              <span>{typeMeta.label}</span>
            </div>
          ) : null}
          {data?.status ? <div>Status: {statusMeta.label}</div> : null}
          {data?.image ? <div>Image: {data.image}</div> : null}
          {data?.command_str ? <div>Cmd: {String(data.command_str)}</div> : null}
          {(data?.required_cpu || data?.required_memory) ? (
            <div>Resources: {data.required_cpu || "-"} / {data.required_memory || "-"}</div>
          ) : null}
          {Array.isArray(data?.env) && data.env.length ? (
            <div className="mt-1">Env: {data.env.map((e) => e.name).join(", ")}</div>
          ) : null}
        </div>
      }
    >
      <div className="rounded-md border border-default-200 bg-white px-2 py-1 min-w-[160px] relative">
        <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-default-400" />
        <div className="flex items-center justify-between gap-2 w-full min-w-0">
          <div className="flex items-center gap-2 min-w-0 overflow-hidden">
            <div className={`h-2 w-2 rounded-full flex-shrink-0 ${statusMeta.dot}`} />
            {typeMeta ? <Icon icon={typeMeta.icon} className="w-4 h-4 text-default-500 flex-shrink-0" /> : null}
            <div className="font-medium text-xs truncate">{data?.name}</div>
          </div>
          <span className={`workflow-status-badge text-[10px] font-semibold whitespace-nowrap px-1.5 py-0.5 rounded-full ${statusMeta.badge}`}>
            {statusMeta.label}
          </span>
        </div>
        <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-default-400" />
      </div>
    </Tooltip>
  );
}

const nodeTypes = { default: DefaultNode };

const buildEdgeCollection = (tasks, taskById, prevEdgesMap = new Map()) => {
  const edges = [];

  tasks.forEach((w) => {
    (w.dependencies || []).forEach((dep) => {
      const id = `${dep}-${w.id}`;
      const previous = prevEdgesMap.get(id);
      const status = normalizeStatus(taskById.get(dep)?.status);
      const statusStyle = EDGE_STYLE_BY_STATUS[status];

      edges.push({
        id,
        source: dep,
        target: w.id,
        type: "arrow",
        data: {
          ...(previous?.data || {}),
          pathOptions: {
            ...DEFAULT_PATH_OPTIONS,
            ...(previous?.data?.pathOptions || {}),
          },
        },
        style: {
          ...(statusStyle ? statusStyle : EDGE_STYLE),
        },
      });
    });
  });

  return edges;
};
const AnimatedArrowEdge = ({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  selected,
  style = {},
  data,
}) => {
  const pathOptions = data?.pathOptions ?? {};
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: pathOptions.borderRadius ?? 24,
    offset: pathOptions.offset ?? 24,
  });

  const stroke = style.stroke || "#374151";
  const markerId = `workflow-arrow-${id}`;

  return (
    <>
      <defs>
        <marker
          id={markerId}
          markerWidth="8"
          markerHeight="8"
          viewBox="0 0 10 10"
          orient="auto"
          refX="9"
          refY="5"
          markerUnits="strokeWidth"
        >
          <path d="M1 1L9 5L1 9L3.2 5Z" fill={stroke} />
        </marker>
      </defs>
      <BaseEdge
        id={id}
        path={edgePath}
        selected={selected}
        markerEnd={`url(#${markerId})`}
        interactionWidth={24}
        style={{ ...style, strokeLinecap: "round" }}
        className="workflow-arrow-edge"
      />
    </>
  );
};

export default function WorkflowPage() {
  const token = useSelector((state) => state.authToken.value);
  const baseUrl = useSelector((state) => state.serverIP.value);

  const [view, setView] = useState("list"); // "list" | "dag"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [workflowToDelete, setWorkflowToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const {
    isOpen: isDeleteModalOpen,
    onOpen: onOpenDeleteModal,
    onClose: internalCloseDeleteModal,
    onOpenChange: disclosureOnOpenChange,
  } = useDisclosure();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const pollRef = useRef(null);
  const listPollRef = useRef(null);
  const edgeTypes = useMemo(() => ({ arrow: AnimatedArrowEdge }), []);
  const normalizedBaseUrl = useMemo(() => {
    if (!baseUrl) return "";
    return baseUrl.startsWith("http") ? baseUrl : `http://${baseUrl}`;
  }, [baseUrl]);
  const closeDeleteModal = useCallback(() => {
    setDeleteLoading(false);
    setWorkflowToDelete(null);
    internalCloseDeleteModal();
  }, [internalCloseDeleteModal]);

  const headers = useMemo(
    () => ({
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : undefined,
    }),
    [token]
  );

  const fetchList = useCallback(async (silent = false) => {
    if (!normalizedBaseUrl) return;
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const res = await fetch(`${normalizedBaseUrl}/v1/workflow/?offset=0&limit=100`, { headers });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || `Failed to load workflows (${res.status})`);
      }
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      const data = ct.includes("application/json")
        ? await res.json().catch(async () => {
            const txt = await res.text().catch(() => "");
            throw new Error(txt || "Invalid JSON response");
          })
        : (() => {
            throw new Error("Server returned non-JSON response");
          })();
      const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
      setWorkflows(items);
    } catch (e) {
      if (!silent) {
        setError(e.message || "Unknown error");
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [normalizedBaseUrl, headers]);

  const buildGraph = useCallback((wf) => {
    const tasks = Array.isArray(wf?.tasks) ? wf.tasks : [];
    setWorkflowStatus(wf?.status || null);

    const spacingX = 300;
    const spacingY = 120;

    // Kahn's algorithm to compute layers left->right 
    const idToTask = new Map(tasks.map((w) => [w.id, w]));
    const indegree = new Map();
    const adj = new Map();
    const taskOrder = new Map(tasks.map((w, i) => [w.id, i])); // Preserve original task order

    tasks.forEach((w) => {
      indegree.set(w.id, 0);
      adj.set(w.id, []);
    });
    tasks.forEach((w) => {
      (w.dependencies || []).forEach((dep) => {
        indegree.set(w.id, (indegree.get(w.id) || 0) + 1);
        adj.get(dep)?.push(w.id);
      });
    });

    const remaining = new Set(tasks.map((w) => w.id));
    const layers = [];
    while (remaining.size) {
      const zero = Array.from(remaining).filter((id) => (indegree.get(id) || 0) === 0);
      if (zero.length === 0) {
        // cycle fallback: place all remaining in one layer
        layers.push(Array.from(remaining));
        break;
      }
      // Keep order stable using original task order
      zero.sort((a, b) => {
        const oa = taskOrder.get(a) ?? 0;
        const ob = taskOrder.get(b) ?? 0;
        if (oa !== ob) return oa - ob;
        const an = idToTask.get(a)?.name || "";
        const bn = idToTask.get(b)?.name || "";
        return an.localeCompare(bn);
      });
      layers.push(zero);
      zero.forEach((id) => {
        remaining.delete(id);
        (adj.get(id) || []).forEach((nbr) => indegree.set(nbr, (indegree.get(nbr) || 1) - 1));
      });
    }

    // Compute row (y) positions trying to align children with their parents
    const nodeRow = new Map();
    layers.forEach((layer, layerIndex) => {
      const occupied = new Set();
      layer.forEach((id) => {
        const task = idToTask.get(id);
        const deps = Array.isArray(task?.dependencies) ? task.dependencies : [];
        const parentRows = deps
          .map((depId) => nodeRow.get(depId))
          .filter((v) => typeof v === "number");

        let desiredRow;
        if (parentRows.length === 0) {
          // No parents with rows yet: stack vertically in this column
          desiredRow = occupied.size;
        } else if (parentRows.length === 1) {
          // Single parent: align with parent row
          desiredRow = parentRows[0];
        } else {
          // Multiple parents: use the rounded average of parent rows
          const avg = parentRows.reduce((sum, r) => sum + r, 0) / parentRows.length;
          desiredRow = Math.round(avg);
        }

        // If desired row is already used in this column, push it down until free
        while (occupied.has(desiredRow)) {
          desiredRow += 1;
        }

        occupied.add(desiredRow);
        nodeRow.set(id, desiredRow);
      });
    });

    // Refine vertical order inside each column so nodes with similar parent/child rows stay closer
    layers.forEach((layer, layerIndex) => {
      if (!layer.length) return;

      const scored = layer.map((id) => {
        const task = idToTask.get(id);
        const deps = Array.isArray(task?.dependencies) ? task.dependencies : [];
        const parentRows = deps
          .map((depId) => nodeRow.get(depId))
          .filter((v) => typeof v === "number");
        const children = adj.get(id) || [];
        const childRows = children
          .map((childId) => nodeRow.get(childId))
          .filter((v) => typeof v === "number");
        const allRows = [...parentRows, ...childRows];

        const avgRow = allRows.length
          ? allRows.reduce((sum, r) => sum + r, 0) / allRows.length
          : (nodeRow.get(id) ?? 0);

        return { id, avgRow };
      });

      scored.sort((a, b) => {
        if (a.avgRow !== b.avgRow) return a.avgRow - b.avgRow;
        const oa = taskOrder.get(a.id) ?? 0;
        const ob = taskOrder.get(b.id) ?? 0;
        if (oa !== ob) return oa - ob;
        const an = idToTask.get(a.id)?.name || "";
        const bn = idToTask.get(b.id)?.name || "";
        return an.localeCompare(bn);
      });

      scored.forEach((item, index) => {
        nodeRow.set(item.id, index);
      });
    });

    const builtNodes = [];
    layers.forEach((layer, layerIndex) => {
      // For the last column, remove any empty space at the top
      let rowOffset = 0;
      if (layerIndex === layers.length - 1) {
        let minRow = Infinity;
        layer.forEach((id) => {
          const r = nodeRow.get(id) ?? 0;
          if (r < minRow) minRow = r;
        });
        if (Number.isFinite(minRow) && minRow > 0) {
          rowOffset = minRow;
        }
      }

      layer.forEach((id) => {
        const w = idToTask.get(id);
        const baseRow = nodeRow.get(id) ?? 0;
        const row = baseRow - rowOffset;
        const position = { x: layerIndex * spacingX, y: row * spacingY };
        builtNodes.push({
          id,
          type: "default",
          data: { ...w },
          position,
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
        });
      });
    });

    const builtEdges = buildEdgeCollection(tasks, idToTask);

    setNodes(builtNodes);
    setEdges(builtEdges);
  }, [setEdges, setNodes]);

  const updateStatusesOnly = useCallback((wf) => {
    const tasks = Array.isArray(wf?.tasks) ? wf.tasks : [];
    const byId = new Map(tasks.map((w) => [w.id, w]));

    setNodes((prev) =>
      prev.map((n) => {
        const w = byId.get(n.id);
        if (!w) return n;
        if (n.data?.status === w.status) return n;
        return { ...n, data: { ...n.data, status: w.status } };
      })
    );

    setEdges((prevEdges) => {
      const prevMap = new Map(prevEdges.map((edge) => [edge.id, edge]));
      return buildEdgeCollection(tasks, byId, prevMap);
    });
  }, [setNodes, setEdges]);

  const fetchWorkflowDetail = useCallback(async (id, initialBuild = false) => {
    if (!normalizedBaseUrl) return;
    try {
      const res = await fetch(`${normalizedBaseUrl}/v1/workflow/${id}`, { headers });
      if (!res.ok) {
        // Do not break polling entirely; just log
        const txt = await res.text().catch(() => "");
        throw new Error(txt || `Failed to load workflow (${res.status})`);
      }
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      const data = ct.includes("application/json")
        ? await res.json().catch(async () => {
            const txt = await res.text().catch(() => "");
            throw new Error(txt || "Invalid JSON response");
          })
        : (() => {
            throw new Error("Server returned non-JSON response");
          })();
      if (initialBuild) {
        buildGraph(data);
      } else {
        updateStatusesOnly(data);
        setWorkflowStatus(data?.status || null);
      }
    } catch (e) {
      console.error(e);
    }
  }, [normalizedBaseUrl, headers, buildGraph, updateStatusesOnly]);

  useEffect(() => {
    if (view === "list" && normalizedBaseUrl) {
      fetchList();
      listPollRef.current = setInterval(() => {
        fetchList(true).catch(() => {});
      }, 1000);
    }
    return () => {
      if (listPollRef.current) {
        clearInterval(listPollRef.current);
        listPollRef.current = null;
      }
    };
  }, [view, normalizedBaseUrl, fetchList]);

  useEffect(() => {
    if (!selectedWorkflow || view !== "dag") return;
    fetchWorkflowDetail(selectedWorkflow.id, true);
    pollRef.current = setInterval(() => {
      fetchWorkflowDetail(selectedWorkflow.id, false);
    }, 1000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [selectedWorkflow, view, fetchWorkflowDetail]);

  const onClickWorkflow = (wf) => {
    setSelectedWorkflow(wf);
    setWorkflowStatus(wf?.status || null);
    setView("dag");
  };

  const backToList = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
    setSelectedWorkflow(null);
    setNodes([]);
    setEdges([]);
    setWorkflowStatus(null);
    setView("list");
  };

  const confirmDelete = useCallback(async () => {
    if (!workflowToDelete || !normalizedBaseUrl || !token) return;
    setDeleteLoading(true);
    try {
      const res = await fetch(`${normalizedBaseUrl}/v1/workflow/${workflowToDelete.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "*/*",
        },
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || `Failed to delete workflow (${res.status})`);
      }

      setWorkflows((prev) => prev.filter((wf) => wf.id !== workflowToDelete.id));
      if (selectedWorkflow?.id === workflowToDelete.id) {
        backToList();
      }
      fetchList(true).catch(() => {});
      toast.success("Workflow deleted successfully.", { position: "bottom-right" });
    } catch (error) {
      console.error("Delete workflow failed:", error);
      toast.error(error.message || "Failed to delete workflow.", { position: "bottom-right" });
    } finally {
      setDeleteLoading(false);
      closeDeleteModal();
    }
  }, [workflowToDelete, normalizedBaseUrl, token, selectedWorkflow, backToList, closeDeleteModal, fetchList]);

  if (view === "dag") {
    const statusMeta = workflowStatus ? getStatusMeta(workflowStatus) : null;
    return (
      <div className="flex flex-col gap-4 h-[calc(100dvh-200px)]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="text-lg font-semibold">Workflow: {selectedWorkflow?.name}</div>
            {statusMeta ? (
              <span className={`workflow-status-badge text-xs font-semibold px-2 py-0.5 rounded-full ${statusMeta.badge}`}>
                {statusMeta.label}
              </span>
            ) : null}
          </div>
          <Button color="default" variant="flat" onPress={backToList}>
            Back to Workflows
          </Button>
        </div>
        <div className="flex-1 min-h-[400px] rounded-medium border-small border-divider overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            defaultEdgeOptions={{
              type: "arrow",
              data: { pathOptions: { ...DEFAULT_PATH_OPTIONS } },
              style: { ...EDGE_STYLE },
            }}
            fitView
          >
            <MiniMap />
            <Controls />
            <Background gap={16} />
          </ReactFlow>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Workflows</h3>
        <Button variant="flat" onPress={fetchList}>Refresh</Button>
      </div>
      {loading ? (
        <div className="flex items-center gap-2 text-default-500"><Spinner size="sm" /> Loading...</div>
      ) : error ? (
        <div className="text-red-500 text-sm">{error}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left">
              <tr className="border-b border-default-200">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">ID</th>
                <th className="py-2 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((wf) => {
                const meta = getStatusMeta(wf.status);
                return (
                  <tr key={wf.id} className="border-b border-default-100">
                    <td className="py-2 pr-4 font-medium">{wf.name}</td>
                    <td className="py-2 pr-4">
                      <span className="inline-flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                        <span className={`workflow-status-badge text-xs font-semibold px-2 py-0.5 rounded-full ${meta.badge}`}>
                          {meta.label}
                        </span>
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-default-500">{wf.id}</td>
                    <td className="py-2 pr-4">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" color="primary" onPress={() => onClickWorkflow(wf)}>
                          View DAG
                        </Button>
                        <Button
                          size="sm"
                          color="danger"
                          variant="light"
                          onPress={() => {
                            setWorkflowToDelete(wf);
                            onOpenDeleteModal();
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <Modal
        isOpen={isDeleteModalOpen}
        onOpenChange={(open) => {
          disclosureOnOpenChange(open);
          if (!open) {
            setDeleteLoading(false);
            setWorkflowToDelete(null);
          }
        }}
        placement="center"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">Delete Workflow</ModalHeader>
              <ModalBody>
                <p>
                  Are you sure you want to delete workflow {" "}
                  <span className="font-semibold">{workflowToDelete?.name}</span>? This action cannot be undone.
                </p>
              </ModalBody>
              <ModalFooter>
                <Button
                  variant="light"
                  onPress={closeDeleteModal}
                  disabled={deleteLoading}
                >
                  Cancel
                </Button>
                <Button
                  color="danger"
                  isLoading={deleteLoading}
                  onPress={confirmDelete}
                >
                  Delete
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}
