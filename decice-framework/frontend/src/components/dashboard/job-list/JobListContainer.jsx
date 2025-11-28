import { useState } from 'react';
import { Card, CardHeader, CardBody, Chip, Button, Spinner } from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { useJobListService } from "./JobListData/jobListService";

const normalizeStatus = (status) => {
  if (typeof status !== "string") return "UNKNOWN";
  return status.trim().toUpperCase();
};

const formatStatusLabel = (status) => {
  if (!status || typeof status !== "string") return "Unknown";
  return status
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
};

const formatDateTime = (value) => {
  if (!value) return "Not available";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

const formatArray = (values) =>
  Array.isArray(values) && values.length > 0 ? values.join(", ") : "Not assigned";

const requiredStatuses = [
  "WAITING",
  "READY",
  "SCHEDULING",
  "PENDING",
  "RUNNING",
  "SUCCEEDED",
  "FAILED",
  "CANCELLED"
];

const optionalStatuses = ["UNKNOWN"];
const stackedStatuses = ["READY", "SCHEDULING", "PENDING"];
const bottomStatuses = ["FAILED", "CANCELLED"];

const statusConfig = {
  WAITING: {
    icon: "mdi:progress-clock",
    iconColor: "text-amber-500",
    chipColor: "warning",
    bgColor: "bg-amber-100",
    emptyStateIcon: "mdi:progress-clock",
    emptyStateMessage: "No Waiting DECICE tasks"
  },
  READY: {
    icon: "material-symbols:schedule-rounded",
    iconColor: "text-indigo-500",
    chipColor: "secondary",
    bgColor: "bg-indigo-100",
    emptyStateIcon: "material-symbols:schedule-rounded",
    emptyStateMessage: "No Ready DECICE tasks"
  },
  SCHEDULING: {
    icon: "mdi:calendar-clock",
    iconColor: "text-blue-500",
    chipColor: "primary",
    bgColor: "bg-blue-100",
    emptyStateIcon: "mdi:calendar-clock",
    emptyStateMessage: "No Scheduling DECICE tasks"
  },
  PENDING: {
    icon: "material-symbols:pending-actions-sharp",
    iconColor: "text-yellow-500",
    chipColor: "warning",
    bgColor: "bg-yellow-100",
    emptyStateIcon: "material-symbols:pending-actions",
    emptyStateMessage: "No Pending DECICE tasks"
  },
  RUNNING: {
    icon: "mdi:play-circle-outline",
    iconColor: "text-blue-500",
    chipColor: "primary",
    bgColor: "bg-blue-100",
    emptyStateIcon: "mdi:play-circle-outline",
    emptyStateMessage: "No Running DECICE tasks"
  },
  SUCCEEDED: {
    icon: "icon-park-outline:doc-success",
    iconColor: "text-green-500",
    chipColor: "success",
    bgColor: "bg-green-100",
    emptyStateIcon: "material-symbols:task",
    emptyStateMessage: "No Succeeded DECICE tasks"
  },
  FAILED: {
    icon: "ep:failed",
    iconColor: "text-red-500",
    chipColor: "danger",
    bgColor: "bg-red-100",
    emptyStateIcon: "material-symbols:running-with-errors",
    emptyStateMessage: "No Failed DECICE tasks"
  },
  CANCELLED: {
    icon: "mdi:close-octagon-outline",
    iconColor: "text-rose-500",
    chipColor: "danger",
    bgColor: "bg-rose-100",
    emptyStateIcon: "mdi:close-circle-outline",
    emptyStateMessage: "No Cancelled DECICE tasks"
  },
  UNKNOWN: {
    icon: "ant-design:file-unknown-outlined",
    iconColor: "text-default-500",
    chipColor: "default",
    bgColor: "bg-default-100",
    emptyStateIcon: "material-symbols:question-mark",
    emptyStateMessage: "No DECICE tasks in unknown state"
  }
};

export default function App() {
  const { jobs, loading, error } = useJobListService();
  const [selectedStatus, setSelectedStatus] = useState("ALL");

  const rawTasks = Array.isArray(jobs) ? jobs : jobs?.tasks || [];
  const transformedTasks = rawTasks.map((taskEntry, index) => {
    const taskInfo = taskEntry?.task || {};
    const normalizedStatus = normalizeStatus(taskInfo.status);
    return {
      ...taskEntry,
      normalizedStatus,
      key: taskInfo.id || taskEntry?.workflow_id || `task-${index}`
    };
  });

  const groupedJobs = transformedTasks.reduce((acc, task) => {
    const normalizedStatus = task.normalizedStatus || "UNKNOWN";
    acc[normalizedStatus] = acc[normalizedStatus] || [];
    acc[normalizedStatus].push(task);
    return acc;
  }, {});

  const deciderOfIconType = (status) => statusConfig[status]?.icon || "mdi:progress-question";
  const deciderOfIconColor = (status) => statusConfig[status]?.iconColor || "text-default-500";
  const deciderOfChipColor = (status) => statusConfig[status]?.chipColor || "default";
  const deciderOfBgColor = (status) => {
    const baseClasses = "border-1 border-gray-200 dark:border-gray-600 flex-1 min-w-[320px] bg-opacity-60 p-2 rounded-2xl max-h-[calc(100vh-128px)] sm:max-h-[calc(100vh-200px)] overflow-y-auto ";
    return baseClasses + (statusConfig[status]?.bgColor || "bg-default-100");
  };

  if (loading) return (
    <div className="w-full min-h-[400px] flex flex-col items-center justify-center p-6">
      <Card className="w-[300px] bg-default-50">
        <CardBody className="py-8 flex flex-col items-center gap-4">
          <Spinner size="lg" color="primary"/>
          <div className="text-center">
            <h3 className="text-lg font-medium text-default-700">Loading Jobs</h3>
            <p className="text-small text-default-500 mt-1">Please wait while we fetch the DECICE Jobs</p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
  if (error) return (
    <div className="w-full p-6">
      <Card className="max-w-[800px] mx-auto bg-default-50">
        <CardHeader className="flex items-center border-b border-default-200 pb-4">
          <div className="flex items-center gap-2">
            <Icon icon="system-uicons:warning" className="w-6 h-6 text-default-600"/>
            <h3 className="text-lg font-medium">System Notification</h3>
          </div>
        </CardHeader>
        <CardBody className="py-6">
          <div className="space-y-4">
            <div>
              <h4 className="text-base font-medium mb-2">Error Details</h4>
              <p className="text-default-600">The system encountered an issue while attempting to retrieve DECICE Jobs.</p>
            </div>
            <div className="bg-default-100 p-4 rounded-lg">
              <p className="font-mono text-sm text-default-700">{error}</p>
            </div>
            <div className="flex justify-end pt-4">
              <Button 
                color="default"
                variant="flat"
                size="sm"
                onClick={() => window.location.reload()}
                startContent={<Icon icon="system-uicons:refresh" />}
              >
                Refresh Page
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );

  const allStatusesForFilter = [...requiredStatuses, ...optionalStatuses];

  const renderJobCard = (jobEntry) => {
    const { task, scheduling, workflow_id, normalizedStatus, key } = jobEntry;
    const iconType = deciderOfIconType(normalizedStatus);
    const iconColor = deciderOfIconColor(normalizedStatus);
    const targetNodes = formatArray(scheduling?.target_nodes);
    const strategy = scheduling?.strategy_used || "Unknown";
    const scheduledAt = formatDateTime(scheduling?.created_at);
    const cpu = task?.required_cpu || "Not specified";
    const memory = task?.required_memory || "Not specified";
    const gpu = task?.required_gpu || "Not specified";
    const dependencies = task?.dependencies?.length || 0;
    const envCount = task?.env?.length || 0;
    const parentWorkflowId = task?.parent_id || workflow_id || "N/A";
    const taskType = task?.type || "N/A";
    const statusLabel = formatStatusLabel(normalizedStatus);

    return (
      <Card className="mb-2 pb-2 shadow-md dark:bg-gray-800 group" key={key}>
        <CardHeader className="justify-between">
          <div className="flex gap-5">
            <Icon
              icon={iconType}
              className={`w-10 h-10 ${iconColor}`}
            />
            <div>
              <h4 className="dark:text-zinc-200 text-sm font-semibold">
                Task Name: {task?.name || "Unnamed Task"}
              </h4>
              <h5 className="dark:text-zinc-300 text-xs">Task ID: {task?.id || "N/A"}</h5>
            </div>
          </div>
        </CardHeader>
        <CardBody className="dark:text-zinc-300 text-xs space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <p className="text-[11px] uppercase text-default-500">Status</p>
              <p className="font-semibold dark:text-zinc-50">{statusLabel}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase text-default-500">Type</p>
              <p className="font-semibold dark:text-zinc-50">{taskType}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase text-default-500">Parent / Workflow</p>
              <p className="font-semibold dark:text-zinc-50">{parentWorkflowId}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase text-default-500">Target Nodes</p>
              <p className="font-semibold dark:text-zinc-50">{targetNodes}</p>
            </div>
          </div>
          <p className="text-[11px] text-default-400 italic group-hover:hidden">
            Hover to see scheduling and resource details
          </p>
          <div className="hidden group-hover:grid grid-cols-1 sm:grid-cols-2 gap-2 pt-3 border-t border-default-200 dark:border-default-100">
            <p>Workflow ID: {workflow_id || "N/A"}</p>
            <p>Scheduling Strategy: {strategy}</p>
            <p>Scheduled At: {scheduledAt}</p>
            <p>Required CPU: {cpu}</p>
            <p>Required Memory: {memory}</p>
            <p>Required GPU: {gpu}</p>
            <p>Dependencies: {dependencies}</p>
            <p>Environment Vars: {envCount}</p>
            <p>Command: {task?.command_str || "Not provided"}</p>
            <p>Image: {task?.image || "Not provided"}</p>
          </div>
        </CardBody>
      </Card>
    );
  };

  return (
    <div>
      <div className="flex flex-col gap-3 mb-3">
        <div className="flex flex-wrap gap-2 items-center">
          <Chip
            variant={selectedStatus === "ALL" ? "solid" : "bordered"}
            color={selectedStatus === "ALL" ? "primary" : "default"}
            onClick={() => setSelectedStatus("ALL")}
            className="cursor-pointer text-xs"
            size="sm"
          >
            All Statuses
          </Chip>
          {allStatusesForFilter.map((status) => {
            const count = groupedJobs[status]?.length || 0;
            if (count === 0) return null;
            const isActive = selectedStatus === status;
            return (
              <Chip
                key={status}
                variant={isActive ? "solid" : "bordered"}
                color={deciderOfChipColor(status)}
                onClick={() => setSelectedStatus(status)}
                className="cursor-pointer text-xs"
                size="sm"
              >
                {formatStatusLabel(status)} ({count})
              </Chip>
            );
          })}
        </div>
      </div>

      <div className="flex gap-5 overflow-x-auto ">
        {(() => {
          const filterStatuses = (statuses) =>
            statuses.filter((status) => selectedStatus === "ALL" || selectedStatus === status);
          const renderStatusSection = (status) => (
            <div key={status} className={deciderOfBgColor(status)}>
              <Chip size="lg" className="mb-3" color={deciderOfChipColor(status)}>
                {formatStatusLabel(status)} ({groupedJobs[status]?.length || 0})
              </Chip>
              {groupedJobs[status]?.length > 0 ? (
                groupedJobs[status].map(renderJobCard)
              ) : (
                <Card className="mb-2 pb-2 shadow-md dark:bg-gray-800 opacity-60">
                  <CardBody className="py-5 flex flex-col items-center justify-center gap-2">
                    <Icon
                      icon={statusConfig[status]?.emptyStateIcon}
                      className="w-12 h-12 text-gray-400"
                    />
                    <p className="text-gray-500 text-sm text-center">
                      {statusConfig[status]?.emptyStateMessage}
                    </p>
                  </CardBody>
                </Card>
              )}
            </div>
          );
          const stackedList = filterStatuses(
            requiredStatuses.filter((status) => stackedStatuses.includes(status))
          );
          const waitingList = filterStatuses(["WAITING"]);
          const bottomList = filterStatuses(bottomStatuses);
          const remainingList = filterStatuses(
            requiredStatuses.filter(
              (status) =>
                !stackedStatuses.includes(status) &&
                status !== "WAITING" &&
                !bottomStatuses.includes(status)
            )
          );

          return (
            <>
              {waitingList.map(renderStatusSection)}
              {stackedList.length > 0 && (
                <div className="flex flex-col gap-5">
                  {stackedList.map(renderStatusSection)}
                </div>
              )}
              {remainingList.map(renderStatusSection)}
              {bottomList.length > 0 && (
                <div className="flex flex-col gap-5 justify-end">
                  {bottomList.map(renderStatusSection)}
                </div>
              )}
            </>
          );
        })()}

        {/* Show optional statuses only if they have jobs */}
        {optionalStatuses
          .filter((status) => selectedStatus === "ALL" || selectedStatus === status)
          .map((status) => 
          groupedJobs[status]?.length > 0 && (
            <div key={status} className={deciderOfBgColor(status)}>
              <Chip size="lg" className="mb-3" color={deciderOfChipColor(status)}>
                {formatStatusLabel(status)} ({groupedJobs[status].length})
              </Chip>
              {groupedJobs[status].map(renderJobCard)}
            </div>
          )
        )}
      </div>
    </div>
  );
}
