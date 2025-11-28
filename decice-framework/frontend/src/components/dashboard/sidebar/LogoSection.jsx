/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react/prop-types */

import React, {useEffect} from "react";
import {Avatar, Spacer, Badge, Tooltip} from "@nextui-org/react";
import {cn} from "../cn";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";


export default function LogoSection({isCompact}) {
    const authToken = useSelector((state) => state.authToken.value);
    const serverIP = useSelector((state) => state.serverIP.value);

    const [userData, setUserData] = React.useState({
      full_name: "",
      username: "",
      email: "",
      active: false,
    });

    const navigate = useNavigate();
    const goToHomePage = () => {
        navigate('/');
      };


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


  return (
    <div className="flex flex-col p-6">

    <div
      className={cn(
        "flex items-center gap-3 px-3",
        {
          "justify-center gap-0": isCompact,
        },
      )}

    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full  cursor-pointer"
       onClick={goToHomePage}
      >
        <img src="/decice.png" alt="Decice logo" />
      </div>
      <span
      onClick={goToHomePage}
        className={cn("text-small font-bold uppercase opacity-100 cursor-pointer ", {
          "w-0 opacity-0": isCompact,
        })}
      >
        DECICE
      </span>
    </div>
    <Spacer y={8} />
    <div className="flex items-center gap-3 px-3">
        <Tooltip content={userData.active ? "user is active" : "user is inactive"}>
    <Badge content="" color={userData.active ? "success" : "danger"} shape="circle" placement="bottom-right">

      <Avatar
        isBordered
        radius="xl"
        className="flex-none"
        size="md"

      />
      </Badge>
      </Tooltip>
      <div className={cn("flex max-w-full flex-col", {hidden: isCompact})}>
        <p className="truncate text-small font-medium text-default-600">{userData.username}</p>
        <p className="truncate text-tiny text-default-400">{userData.email}</p>
      </div>
    </div>
  </div>
  )
}
