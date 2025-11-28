import * as React from "react";
import { Button, Input, Spacer, Badge, Textarea, Tooltip} from "@nextui-org/react";
import { useSelector, useDispatch } from "react-redux";
import { changeAuthToken } from "../../../redux/authTokenSlice";
import { cn } from "./cn";
import {Card, CardBody, CardFooter} from "@nextui-org/card";
import {Avatar} from "@nextui-org/avatar";
import {Icon} from "@iconify/react";
import { useNavigate } from "react-router-dom";

interface AccountSettingCardProps {
  className?: string;
}

const AccountSetting = React.forwardRef<HTMLDivElement, AccountSettingCardProps>(
  ({ className, ...props }, ref) => {
    const authToken = useSelector((state) => state.authToken.value);
    const serverIP = useSelector((state) => state.serverIP.value);
    const dispatch = useDispatch();
    const [userData, setUserData] = React.useState({
      full_name: "",
      username: "",
      email: "",
      active: false,
    });
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);



    const navigate = useNavigate();
    function logOut(){
      localStorage.removeItem("access_token");
      dispatch(changeAuthToken(null));
      navigate("/signin");
    }


    React.useEffect(() => {
      const fetchUserData = async () => {
        if (!authToken) {
          setError("User is not authenticated.");
          setLoading(false);
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
            throw new Error("Failed to fetch user data. Your token has expired. you need to logout and login again.");
          }

          const data = await response.json();

          setUserData({
            full_name: data.full_name || "",
            username: data.username || "",
            email: data.email || "",
            active: data.active || false,
          });
        } catch (err) {
          setError((err as Error).message);
        } finally {
          setLoading(false);
        }
      };

      fetchUserData();
    }, [authToken]);

    const handleUpdateAccount = async () => {
      if (!authToken) {
        setError("User is not authenticated.");
        return;
      }

      try {
        const response = await fetch(`http://${serverIP}/v1/user/me/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({
            full_name: userData.full_name,
            // Include other fields if they are allowed to be updated
          }),
        });

        if (!response.ok) {
          throw new Error("Failed to update user data.");
        }

        const data = await response.json();

        // Update the auth token if a new one is provided
        if (data.token && data.token.access_token) {
          dispatch(changeAuthToken(data.token.access_token));
          localStorage.setItem("access_token", data.token.access_token);
        }

        // Update the user data with the response
        setUserData({
          full_name: data.user.full_name || "",
          username: data.user.username || "",
          email: data.user.email || "",
          active: data.user.active || false,
        });

        // Optionally, display a success message
        alert("Account updated successfully!");
      } catch (err) {
        setError((err as Error).message);
      }
    };

    if (loading) {
      return <div>Loading...</div>;
    }

    if (error) {
      return (
      <div>
      <div className="text-red-500">{error}</div>
      <Button color="danger"   onClick={() => logOut()}>
        Logout
      </Button>
      </div>
      );
    }

    return (
      <>
      <div ref={ref} className={cn("p-2", className)} {...props}>


              {/* Profile */}
      <div>
        <p className="text-base font-medium text-default-700">Profile</p>
        <p className="mt-1 text-sm font-normal text-default-400">
          This displays your public profile on the site.
        </p>
        <Card className="mt-4 bg-default-100" shadow="none">
          <CardBody className="-mb-12">
            <div className="flex items-center gap-4">
            <Tooltip content={userData.active ? "user is active" : "user is inactive"}>
    <Badge content="" color={userData.active ? "success" : "danger"} shape="circle" placement="bottom-right">

      <Avatar
        isBordered
        className="flex-none"
        size="md"

      />
      </Badge>
      </Tooltip>
              <div>
                <p className="text-sm font-medium text-default-600">{userData.username}</p>
                <p className="text-xs text-default-400">{userData.email}</p>

              </div>
            </div>
          </CardBody>
          <CardFooter className="flex justify-end">
        <Button color="danger" variant="light" size="sm" onClick={() => logOut()}
          startContent={
            <Icon
            className="flex-none text-red-500"
            icon="solar:logout-2-bold"
            width={18}
          />}
          >

                      Logout
                </Button>
      </CardFooter>
        </Card>
      </div>
      <Spacer y={4} />



        {/* Full name */}
        <div>
          <p className="text-base font-medium text-default-700">Full name</p>
          <p className="mt-1 text-sm font-normal text-default-400">
            Name to be used for emails
          </p>
          <Input
           isDisabled={true}
            className="mt-2"
            placeholder="e.g Malik Türkoğlu"
            value={userData.full_name}
            onChange={(e) => setUserData({ ...userData, full_name: e.target.value })}
          />
        </div>
        <Spacer y={2} />
        {/* Username */}
        <div>
          <p className="text-base font-medium text-default-700">Username</p>
          <p className="mt-1 text-sm font-normal text-default-400">
            Nickname or first name.
          </p>
          <Input
            className="mt-2"
            placeholder="malik.turkoglu"
            value={userData.username}
            isDisabled={true}
          />
        </div>
        <Spacer y={2} />
        {/* User ID (Assuming it's part of userData) */}
        {/* If the API returns a user ID, include it here */}
        {/* Email Address */}
        <div>
          <p className="text-base font-medium text-default-700">Email Address</p>
          <p className="mt-1 text-sm font-normal text-default-400">
            The email address associated with your account.
          </p>
          <Input
            className="mt-2"
            placeholder="malik.turkoglu@venit.org"
            value={userData.email}
            isDisabled={true}
          />
        </div>
        <Spacer y={2} />

        <div>
          <p className="text-base font-medium text-default-700">User Auth Token</p>
          <p className="mt-1 text-sm font-normal text-default-400">
           This is your Decice User Auth Token
          </p>
          <Input
            className="mt-2"
            placeholder="malik.turkoglu@venit.org"
            value="**********************************************************************************************************"
            isDisabled={true}

          />
        </div>
        <Spacer y={2} />
        {/* Update Account Button */}
        <Button
          className="mt-4 bg-default-foreground text-background"
          size="sm"
          onClick={handleUpdateAccount}
          isDisabled={true}
        >
          Update Account
        </Button>
        {error && <div className="text-red-500 mt-2">{error}</div>}
      </div>
      </>
    );
  }
);

AccountSetting.displayName = "AccountSetting";

export default AccountSetting;
