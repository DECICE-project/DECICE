import { useState } from "react";
import { changeServerIP, changeWatmonApiIP } from "../../../redux/serverInfoTokenSlice";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@nextui-org/react";
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { useThemeProvider } from '../ThemeContext';

function ServerSetting() {
    const { currentTheme } = useThemeProvider();
    const serverIPRedux = useSelector((state) => state.serverIP.value);
    const watmonApiIPRedux = useSelector((state) => state.serverIP.watmon_api_ip);
    const[serverIP, setServerIP] = useState(serverIPRedux);
    const[watmonApiIP, setWatmonApiIP] = useState(watmonApiIPRedux);
    const dispatch = useDispatch();

    function savingLocalStorageOfServerIP(serverIP){
      localStorage.setItem("server_ip", serverIP);
      showSuccessToast();
    }


    function savingWatmonApiIP(watmonApiIP){
      localStorage.setItem("watmon_api_ip", watmonApiIP);
      showSuccessToast();
    }

    function showSuccessToast() {
      toast.success("IP has been saved successfully!", {
        position: "top-center",
        autoClose: 2000,
        hideProgressBar: false,
        closeOnClick: true,
        pauseOnHover: true,
        draggable: true,
        theme: currentTheme === 'light' ? 'light' : 'dark',
        progress: undefined,
      });
    }
  return (
        <div>
        <h2 className="mb-3 mt-3 font-semibold dark:text-zinc-100">Control Manager IP Address</h2>
        <div className="block">
        <input
                 className="form-input w-full py-2 dark:text-black"
                    label="Name"
                    name="name"
                    value={serverIP}
                    onChange={(e) => setServerIP(e.target.value)}
                    placeholder="Enter Server IP"
                  />
                          <Button
          className="mt-4 bg-default-foreground text-background w-full"
          size="sm"
          onClick={() => {dispatch(changeServerIP(serverIP)), savingLocalStorageOfServerIP(serverIP)}  }
        >
          Control Manager IP
        </Button>
        <p className="text-xs mt-1">Current IP: {serverIPRedux}</p>
        <h2 className="mb-3 mt-3 font-semibold dark:text-zinc-100">WATMON API IP Address</h2>
        <input
                 className="form-input w-full py-2 mt-4 dark:text-black"
                    label="Watmon Api IP"
                    name="watmonApiIP"
                    value={watmonApiIP}
                    onChange={(e) => setWatmonApiIP(e.target.value)}
                    placeholder="Enter WATMON Api IP"
                  />
        <Button
          className="mt-4 bg-default-foreground text-background w-full"
          size="sm"
          onClick={() => {dispatch(changeWatmonApiIP(watmonApiIP)), savingWatmonApiIP(watmonApiIP)}  }
        >
          WATMON API IP
        </Button>
        <p className="text-xs mt-1">Current WATMON API IP: {watmonApiIPRedux}</p>
        </div>
        </div>
  )
}

export default ServerSetting
