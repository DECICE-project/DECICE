/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react/prop-types */
import React,{useEffect, useState} from 'react'
import {Upload2, Clipboard,  Nodes} from "../Icons";
import {Tabs, Tab, Badge, Button, Link} from "@nextui-org/react";
import {Avatar} from "@nextui-org/react";
import { useSelector, useDispatch } from "react-redux";
import { changeAuthToken } from '../../../redux/authTokenSlice';
import { useNavigate } from "react-router-dom";
import {Icon} from "@iconify/react";
const grafana_url = import.meta.env.VITE_GRAFANA_URL;
function BottomNavigation({selected, setSelected}) {

  const authToken = useSelector((state) => state.authToken.value);
  const serverIP = useSelector((state) => state.serverIP.value);
  const [bottomSelection, setBottomSelection] = useState(null);

  const [userData, setUserData] = React.useState({
    full_name: "",
    username: "",
    email: "",
    active: false,
  });

 useEffect(() => {
    const fetchUserData = async () => {
      if (!authToken) {
        console.log("User is not authenticated.");

        return;
      }

      try {
        const response = await fetch(`http://${serverIP}/v1/user/me/`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch user data. Your token has expired. you need to log in again.");
        }

        const data = await response.json();
        console.log("data: ", data)
        setUserData({
          full_name: data.full_name || "",
          username: data.username || "",
          email: data.email || "",
          active: data.active || false,
        });
      } catch (err) {
        console.log((err).message);
      }
    };

    fetchUserData();
  }, [authToken]);



  useEffect(() => {
    if(bottomSelection === "more")
      return;
    setSelected(bottomSelection);
  }, [bottomSelection])


  const navigate = useNavigate();
  const dispatch = useDispatch();
  function logOut(){
    localStorage.removeItem("access_token");
    dispatch(changeAuthToken(null));
    navigate("/signin");
  }

  return (
    <div className="overflow-x-auto -px-3 fixed bottom-0 left-0 right-0 border-t border-gray-300 shadow-md sm:hidden z-10 bg-background">
    <div className="flex w-full flex-col ml-3">
      <Tabs
        aria-label="Options"
        color="primary"
        variant="underlined"
        selectedKey={bottomSelection}
        onSelectionChange={setBottomSelection}
        classNames={{
          tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
          cursor: "w-full",
          tab: "max-w-fit px-0 h-16",
        }}
      >
        <Tab
          key="home"
          title={
            <div className="flex items-center space-x-2">
              <Clipboard/>
              <span>Overview</span>
            </div>
          }
        />
        <Tab
          key="network"
          title={
            <div className="flex items-center space-x-2">
              <Nodes/>
              <span>Network</span>
            </div>
          }
        />
        <Tab
          key="upload"
          title={
            <div className="flex items-center space-x-2">
              <Upload2/>
              <span>Job</span>
            </div>
          }
        />
        <Tab
          key="more"
          title={
            <div className="flex items-center space-x-2 mr-3">
               <Badge size="sm" content="" color={userData.active ? "success" : "danger"} shape="circle" placement="bottom-right">
                            <Avatar
                            className="w-5 h-5 text-tiny bg-white dark:bg-black text-red"
      />
        </Badge>
              <span>More</span>
            </div>
          }
        />
      </Tabs>
    </div>

{(bottomSelection === "more") ?
    <div className="fixed bottom-20 right-4 flex flex-col gap-3">
      {/* Menu Item 1 */}
      <Button size="sm" radius="full" color="primary" variant="shadow" as={Link} target="_blank" href={`${grafana_url}`}>
        Telemetry       <Icon
     icon="fluent-mdl2:open-in-new-tab"

     />
      </Button>
      {/* Menu Item 2 */}
      <Button size="sm" radius="full" color="primary" variant={(selected === "tracker") ? "flat": "shadow"} onClick={() => setSelected("tracker")}>
        Settings
      </Button>
      {/* Menu Item 3 */}
      <Button size="sm" radius="full" color="danger" variant="shadow" onClick={() => logOut()}>
        Logout                      <Icon
                        className="flex-none rotate-180"
                        icon="solar:minus-circle-line-duotone"
                        width={24}
                      />
      </Button>
    </div>
: null}

  </div>

  )
}

export default BottomNavigation
