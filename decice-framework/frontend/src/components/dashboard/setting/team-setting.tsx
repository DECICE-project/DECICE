"use client";

import * as React from "react";
import {
  Button,
  Card,
  CardBody,
  Divider,
  Input,
  Select,
  SelectItem,
  Spacer,
} from "@nextui-org/react";
import {Icon} from "@iconify/react";

import {cn} from "./cn";
import TeamManageTable from "./team-manage-table";

interface TeamSettingCardProps {
  className?: string;
}

const roleOptions = [
  {label: "Team Member", value: "member", description: "team member"},
  {label: "Team Ceo", value: "admin", description: "team admin"},
  {label: "Team Leader", value: "owner", description: "team owner"},
];

const TeamSetting = React.forwardRef<HTMLDivElement, TeamSettingCardProps>(
  ({className, ...rest}, ref) => (
    <div {...rest} ref={ref} className={cn("p-2", className)}>
      {/* Title */}
      <p className="text-base font-medium text-default-700">Team</p>
      <p className="mt-1 text-sm font-normal text-default-400">Manage and invite Team Members.</p>
      {/* Invite */}
      <Card className="mt-4 bg-default-100" shadow="none">
        <CardBody className="px-4">
          <div className="flex items-start justify-between pb-3">
            <p className="mt-1.5 text-sm font-medium text-default-700">
              Invite new members by email address
            </p>
            <Button
              className="bg-default-foreground text-background"
              endContent={<Icon className="h-3 w-3" icon="solar:link-linear" />}
              radius="md"
              size="sm"
            >
              Invite Link
            </Button>
          </div>
          <Divider />
          <Spacer y={3} />
          <div className="py-2">
            {/* Email Address */}
            <div className="flex items-center justify-between gap-3 ">
              <div className="flex-1">
                <p className="text-sm font-normal text-default-500">Email Address</p>
                <Input
                  className="mt-2"
                  classNames={{
                    inputWrapper: "bg-default-200",
                  }}
                  placeholder="e.g user@decice.com"
                />
              </div>
              <div className="flex-1">
                <p className="text-sm font-normal text-default-500">Role</p>
                <Select
                  className="mt-2"
                  classNames={{
                    trigger: "bg-default-200",
                  }}
                  defaultSelectedKeys={["member"]}
                >
                  {roleOptions.map((roleOption) => (
                    <SelectItem key={roleOption.value} value={roleOption.value}>
                      {roleOption.label}
                    </SelectItem>
                  ))}
                </Select>
              </div>
            </div>
            <Button
              className="mt-3 bg-default-200 text-default-700"
              endContent={<Icon className="h-[18px] w-[18px]" icon="solar:add-circle-linear" />}
              radius="md"
              size="sm"
            >
              Add more
            </Button>
          </div>
          <Spacer y={3} />
          <Divider />
          <div>
            <div className="flex items-end justify-between pt-3">
              <p className="relative mb-2 text-xs text-default-500">
                Learn more about <span className="text-default-foreground">Team Members</span>
                <Icon
                  className={
                    "absolute right-0 top-0 h-2.5 w-2.5 translate-x-[8px] translate-y-[-2px] text-default-foreground"
                  }
                  icon="material-symbols-light:arrow-outward-rounded"
                />
              </p>
              <Button className="bg-default-foreground text-background" radius="md" size="sm">
                Send Invite
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
      <Spacer y={4} />
      {/* Team management table */}
      <TeamManageTable />
    </div>
  ),
);

TeamSetting.displayName = "TeamSetting";

export default TeamSetting;
