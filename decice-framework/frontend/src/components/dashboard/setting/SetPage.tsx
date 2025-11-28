import React from "react";
import {Avatar, Button, Spacer, Tab, Tabs, Tooltip, useDisclosure} from "@nextui-org/react";
import {Icon} from "@iconify/react";
import {useMediaQuery} from "usehooks-ts";

import ProfileSetting from "./profile-setting";
import AppearanceSetting from "./appearance-setting";
import AccountSetting from "./account-setting";
import BillingSetting from "./billing-setting";
import TeamSetting from "./team-setting";
import {cn} from "./cn";
import ServerSetting from "./ServerSetting";


export default function Component() {
  const {isOpen, onOpenChange} = useDisclosure();
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const isMobile = useMediaQuery("(max-width: 768px)");

  const onToggle = React.useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  return (
      <div className="w-full max-w-full flex-1 p-4">
        {/* Title */}
        <div className="flex items-center gap-x-3">

          <h1 className="text-3xl font-bold leading-9 text-default-foreground">Settings</h1>
        </div>
        <h2 className="mt-2 text-small text-default-500">
          Customize settings, email preferences, and web appearance.
        </h2>
        {/*  Tabs */}
        <Tabs
          fullWidth
          classNames={{
            base: "mt-6",
            cursor: "bg-content1 dark:bg-content1",
            panel: "w-full p-0 pt-4",
          }}
        >
          <Tab key="profile" title="Profile">
            <AccountSetting />
          </Tab>
          <Tab key="appearance" title="Appearance">
            <AppearanceSetting />
          </Tab>
          <Tab key="account" title="Server">
          <ServerSetting/>
          </Tab>
        </Tabs>
      </div>
  );
}
