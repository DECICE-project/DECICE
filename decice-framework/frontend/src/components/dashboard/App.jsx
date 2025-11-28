import React, {useEffect} from "react";
import {Button, ScrollShadow, Tooltip, Chip, Link, Badge} from "@nextui-org/react";
import {Icon} from "@iconify/react";
import {useMediaQuery} from "usehooks-ts";
import {sectionItems} from "./sidebar-items";
import {cn} from "./cn";
import ThemeToggle from './ThemeToggle';
import Sidebar from "./sidebar";
import JobContainer from "./job-list/JobListContainer"
import JobPost from "./job-post/JobPost"
// import Telementry from "./telemetry/TelementryPage"
import Setting from "./setting/SetPage";
import { Provider, useAtomValue, useAtom } from "jotai";
import { textAtom } from './sidebar';
import MultipleNetworkGraphs from "./nodegraph/Multiple"
import { useNavigate } from "react-router-dom";
import { useDispatch } from 'react-redux'
import { changeAuthToken } from '../../redux/authTokenSlice';
import ServerPopUp from "../serverStatus/ServerPopUp.tsx";
import LogoSection from "./sidebar/LogoSection.jsx";
import CheckTokenExpires from "../token/CheckTokenExpires.jsx"
import BottomNavigation from "./bottom-navigation/BottomNavigation.jsx";
import TelemetryNavigatePage from "./telemetry/TelemetryNavigatePage.jsx";
import WorkflowPage from "./workflow/WorkflowPage.jsx";

export default function Component() {
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const isMobile = useMediaQuery("(max-width: 768px)");
  const isCompact = isCollapsed || isMobile;
  const [selected, setSelected] = React.useState("home");
  const [text, setText] = useAtom(textAtom);
  const navigate = useNavigate();

  const onToggle = React.useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  useEffect(() => {
      setText(selected);
  }, [selected]);

  function ReturnPage(){
    let page = useAtomValue(textAtom);
    if(isMobile) page = text;
    if(page === "home") return <JobContainer/>
    if(page === "settings") return <Setting/>
    if(page === "network") return <MultipleNetworkGraphs/>
    if(page === "upload") return <JobPost/>
    if(page === "telemetry") return <TelemetryNavigatePage/>
    if(page === "workflows") return <WorkflowPage/>
  }
  const dispatch = useDispatch();

  function logOut(){
    localStorage.removeItem("access_token");
    dispatch(changeAuthToken(null));
    navigate("/signin");
  }



  return (
    <Provider>
      <CheckTokenExpires/>
      <div className="flex h-dvh w-full overflow-hidden">
        {/* Sticky Sidebar */}
        <div
          className={cn(
            "hidden relative sm:flex h-screen sticky top-0 w-72 flex-col !border-r-small border-divider transition-width",
            {
              "w-16 items-center px-2": isCompact,
            },
          )}
        >
          {/* Logo Section */}
          <LogoSection isCompact={isCompact}/>

          {/* Scrollable Navigation Area */}
          <div className="flex-1 overflow-y-auto">
            <ScrollShadow className="h-full py-6 px-6">
              <Sidebar defaultSelectedKey="home" isCompact={isCompact} items={sectionItems} />
            </ScrollShadow>
          </div>

          {/* Bottom Actions */}
          <div className="p-6">
            <div
              className={cn("flex flex-col", {
                "items-center": isCompact,
              })}
            >

              <Tooltip content="Log Out" isDisabled={!isCompact} placement="right">
                <Button
                onClick={() => logOut()}
                  className={cn("justify-start text-default-500 data-[hover=true]:text-foreground", {
                    "justify-center": isCompact,
                  })}
                  isIconOnly={isCompact}
                  startContent={
                    isCompact ? null : (
                      <Icon
                        className="flex-none rotate-180 text-default-500"
                        icon="solar:minus-circle-line-duotone"
                        width={24}
                      />
                    )
                  }
                  variant="light"
                >
                  {isCompact ? (
                    <Icon
                      className="rotate-180 text-default-500"
                      icon="solar:minus-circle-line-duotone"
                      width={24}
                    />
                  ) : (
                    "Log Out"
                  )}
                </Button>
              </Tooltip>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="w-full flex-1 flex flex-col overflow-auto">
          <header className="hidden sm:flex m-3 sticky top-0 z-10 justify-between gap-3 rounded-medium border-small border-divider p-4 bg-background">
            <Button isIconOnly size="sm" variant="light" onPress={onToggle}>
              <Icon
                className="text-default-500"
                height={24}
                icon="solar:sidebar-minimalistic-outline"
                width={24}
              />
            </Button>
            <h2 className="text-medium font-medium text-default-700">DECICE Dashboard</h2>
            <ThemeToggle />
          </header>

          <main className="flex-1 p-4">
            <div className="mb-24 sm:mb-0 p-3 flex w-full flex-col gap-4 rounded-medium border-small border-divider">
              <ReturnPage/>
            </div>
          </main>

          {/* Mobile Bottom Navigation */}
          <BottomNavigation selected={selected} setSelected={setSelected}/>
        </div>
      </div>
      <ServerPopUp/>
    </Provider>
  );
}
