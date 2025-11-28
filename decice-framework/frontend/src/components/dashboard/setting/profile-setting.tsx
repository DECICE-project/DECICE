"use client";

import * as React from "react";
import {Card, CardBody} from "@nextui-org/card";
import {Avatar} from "@nextui-org/avatar";
import {Icon} from "@iconify/react";
import {Button, Badge, Input, Spacer, Textarea} from "@nextui-org/react";

import {cn} from "./cn";

interface ProfileSettingCardProps {
  className?: string;
}

const ProfileSetting = React.forwardRef<HTMLDivElement, ProfileSettingCardProps>(
  ({className, ...props}, ref) => (
    <div ref={ref} className={cn("p-2", className)} {...props}>
      {/* Profile */}
      <div>
        <p className="text-base font-medium text-default-700">Profile</p>
        <p className="mt-1 text-sm font-normal text-default-400">
          This displays your public profile on the site.
        </p>
        <Card className="mt-4 bg-default-100" shadow="none">
          <CardBody>
            <div className="flex items-center gap-4">
              <Badge
                disableOutline
                classNames={{
                  badge: "w-5 h-5",
                }}
                content={
                  <Button
                    isIconOnly
                    className="h-5 w-5 min-w-5 bg-background p-0 text-default-500"
                    radius="full"
                    size="sm"
                    variant="bordered"
                  >
                    <Icon className="h-[9px] w-[9px]" icon="solar:pen-linear" />
                  </Button>
                }
                placement="bottom-right"
                shape="circle"
              >
                <Avatar
                  className="h-16 w-16"
                  src="https://www.venit.org/venit-website/static/img/venit.png"
                />
              </Badge>
              <div>
                <p className="text-sm font-medium text-default-600">user</p>
                <p className="text-xs text-default-400">user2</p>
                <p className="mt-1 text-xs text-default-400">user@decice.eu</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
      <Spacer y={4} />
      {/* Title */}
      <div>
        <p className="text-base font-medium text-default-700">Title</p>
        <p className="mt-1 text-sm font-normal text-default-400">Set your current role.</p>
        <Input className="mt-2" placeholder="e.g Frontend Developer" />
      </div>
      <Spacer y={2} />
      {/* Location */}
      <div>
        <p className="text-base font-medium text-default-700">Location</p>
        <p className="mt-1 text-sm font-normal text-default-400">Set your current location.</p>
        <Input className="mt-2" placeholder="e.g Istanbul, Turkey" />
      </div>
      <Spacer y={4} />
      {/* Biography */}
      <div>
        <p className="text-base font-medium text-default-700">Task Description</p>
        <p className="mt-1 text-sm font-normal text-default-400">
          Specify your present tasks.
        </p>
        <Textarea
          className="mt-2"
          classNames={{
            input: cn("min-h-[115px]"),
          }}
          placeholder="e.g., 'Adam Smith - venit.org Backend developer. solving backend issues, implementing decice api."
        />
      </div>
      <Button className="mt-4 bg-default-foreground text-background" size="sm">
        Update Profile
      </Button>
    </div>
  ),
);

ProfileSetting.displayName = "ProfileSetting";

export default ProfileSetting;
