import React, { useEffect, useState } from "react";
import { Button, ResizablePanel, Spacer } from "@nextui-org/react";
import { LazyMotion, domAnimation, AnimatePresence, m } from "framer-motion";
import { cn } from "@nextui-org/react";
import ServerSetting from "../dashboard/setting/ServerSetting";
import { useSelector } from "react-redux";

const variants = {
  visible: { opacity: 1 },
  hidden: { opacity: 0 },
};

export default function Component() {
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
  const [isServerOnline, setIsServerOnline] = useState(null);
  const serverIP = useSelector((state) => state.serverIP.value);
  const timeoutId = setTimeout(() => controller.abort(), 4000); // Set timeout for 4 seconds
  const checkServerStatus = async () => {
    try { `http://${serverIP}/health`
      const response = await fetch(`http://${serverIP}/health`, { signal: AbortSignal.timeout(5000) });
      console.log("response: ", response.ok)
      if (response.ok) {
        setIsServerOnline(true);
      } else {
        setIsServerOnline(false);
      }
    } catch (error) {
      setIsServerOnline(false);
    }
  };

  useEffect(() => {
    checkServerStatus();
    const interval = setInterval(checkServerStatus, 5000); // Ping every 5 seconds
    return () => clearInterval(interval);
  }, [serverIP]);

  const AnimatedWrapper = ({ children, className, ...props }) => (
    <m.div
      animate="visible"
      className={cn(
        "pointer-events-auto m-auto max-w-sm rounded-large border border-divider bg-background/15 p-3 shadow-small backdrop-blur",
        className,
      )}
      exit="hidden"
      initial="hidden"
      transition={{ opacity: { duration: 0.5 } }}
      variants={variants}
      {...props}
    >
      {children}
    </m.div>
  );

  const serverSettingsContent = (
    <AnimatedWrapper>
      <ServerSetting />
      <Spacer y={4} />
      <div className="flex justify-between gap-x-3">
        <Button
          fullWidth
          radius="lg"
          style={{
            border: "solid 2px transparent",
            backgroundImage: `linear-gradient(hsl(var(--nextui-background)), hsl(var(--nextui-background))), linear-gradient(83.87deg, #F54180, #9353D3)`,
            backgroundOrigin: "border-box",
            backgroundClip: "padding-box, border-box",
          }}
          onPress={() => setIsSettingsOpen(false)}
        >
          Return
        </Button>
      </div>
    </AnimatedWrapper>
  );

  const serverAlertContent = (
    <AnimatedWrapper>
      <div className="flex items-center justify-center">
        {isServerOnline === null ? (
          <div className="px-3 py-1 text-lg font-medium leading-none text-center text-yellow-800 bg-yellow-200 rounded-full animate-pulse dark:bg-yellow-900 dark:text-yellow-200">
            Checking server status...
          </div>
        ) : isServerOnline ? (
          <div className="px-3 py-1 text-lg font-medium leading-none text-center text-green-800 bg-green-200 rounded-full animate-pulse dark:bg-green-900 dark:text-green-200">
            The server is online
          </div>
        ) : (
          <div className="px-3 py-1 text-lg font-medium leading-none text-center text-red-800 bg-red-200 rounded-full animate-pulse dark:bg-red-900 dark:text-red-200">
            DECICE API is offline
          </div>
        )}
      </div>
      <div className="mt-4 space-y-2">
        <Button
          fullWidth
          className="border-default-200 font-medium text-default-foreground"
          radius="lg"
          variant="bordered"
          onPress={() => setIsSettingsOpen(true)}
        >
          Server Settings
        </Button>
      </div>
    </AnimatedWrapper>
  );

  return (
    (isServerOnline ? null:


    <div className="pointer-events-none fixed inset-x-0 bottom-0 px-6 pb-6 z-50">
      <ResizablePanel>
        <AnimatePresence initial={false} mode="wait">
          <LazyMotion features={domAnimation}>
            {isSettingsOpen ? serverSettingsContent : serverAlertContent}
          </LazyMotion>
        </AnimatePresence>
      </ResizablePanel>
    </div>

    )
  );
}
