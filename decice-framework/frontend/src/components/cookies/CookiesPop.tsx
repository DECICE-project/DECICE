import React from "react";
import { Button, Link, ResizablePanel, Spacer } from "@nextui-org/react";
import { LazyMotion, domAnimation, AnimatePresence, m } from "framer-motion";
import { cn } from "@nextui-org/react";
import SwitchCell from "./switch-cell.tsx";
import { toast } from 'react-toastify';
const variants = {
  visible: { opacity: 1 },
  hidden: { opacity: 0 },
};

export default function Component() {
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
  const [themePreference, setThemePreference] = React.useState(true); // Varsayılan olarak koyu tema
  const [tokenManagement, setTokenManagement] = React.useState(true); // Varsayılan olarak etkin
  const [closeCookie, setCloseCookie] = React.useState(false);
  // Ayarları kaydetme fonksiyonu
  const saveSettingsToLocalStorage = (themePrefenceReject:any) => {


    const settings = {
      themePreference: themePreference ? false : true,
      tokenManagement: true,
    };
    if(themePrefenceReject === true)
        settings["themePreference"] = false;

    // LocalStorage'a kaydetme
    localStorage.setItem("cookieSettings", JSON.stringify(settings));


    setIsSettingsOpen(false);
    setCloseCookie(true);
    toast("Your settings have been saved.", {
        position: "bottom-right"
      })
  };

  // AnimatedWrapper component
  const AnimatedWrapper = ({
    children,
    className,
    ...props
  }: React.PropsWithChildren<{ className?: string }>) => (
    <m.div
      animate="visible"
      className={cn(
        "pointer-events-auto mr-auto max-w-sm rounded-large border border-divider bg-background/15 p-6 shadow-small backdrop-blur",
        className
      )}
      exit="hidden"
      initial="hidden"
      transition={{
        opacity: {
          duration: 0.5,
        },
      }}
      variants={variants}
      {...props}
    >
      {children}
    </m.div>
  );

  const cookieSettingsContent = (
    <AnimatedWrapper>
      <h1 className="text-large font-semibold">Your Privacy</h1>
      <p className="text-small font-normal text-default-700">
        This site uses tracking technologies to improve your experience. You may choose to accept or
        reject these technologies. Check our{" "}
        <Link href="#" size="sm" underline="always">
          Privacy
        </Link>{" "}
        for more information.
      </p>
      <Spacer y={4} />
      <div className="flex flex-col gap-y-2">
        <SwitchCell
          defaultSelected={tokenManagement}
          classNames={{
            base: "dark:bg-content1",
            label: "text-small",
          }}
          description="Your session tokens are securely stored in your browser's local storage to keep you logged in."
          label="Token Management"
          isDisabled={true} // Token yönetimi sabit (değiştirilemez)
        />
        <SwitchCell
          defaultSelected={themePreference}
          onValueChange={themePreference}
          classNames={{
            base: "dark:bg-content1",
            label: "text-small",
          }}
          description="You can choose your preferred theme for the platform."
          label="Theme Preference"

        />
      </div>
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
          onPress={() => {
            saveSettingsToLocalStorage(false); // Ayarları kaydet
            setIsSettingsOpen(false); // Pencereyi kapat
          }}
        >
          Save Settings
        </Button>
        <Button fullWidth variant="bordered" onPress={() => {setIsSettingsOpen(false), saveSettingsToLocalStorage(true)}}>
          Reject All Optional
        </Button>
      </div>
    </AnimatedWrapper>
  );

  const cookiesAlertContent = (
    <AnimatedWrapper>
      <p className="text-small font-normal text-default-700">
        We use cookies on our website to give you the most relevant experience by remembering your
        preferences and repeat visits. By clicking&nbsp;
        <b className="font-semibold">&quot;Accept All&quot;</b>, you consent to the use of ALL the
        cookies. However, you may visit&nbsp;
        <span className="font-semibold">&quot;Cookie Settings&quot;</span> to provide a controlled
        consent. For more information, please read our{" "}
        <Link href="#" size="sm" underline="hover">
          Cookie Policy.
        </Link>
      </p>
      <div className="mt-4 space-y-2">
        <Button
          fullWidth
          className="px-4 font-medium"
          radius="lg"
          style={{
            border: "solid 2px transparent",
            backgroundImage: `linear-gradient(hsl(var(--nextui-background)), hsl(var(--nextui-background))), linear-gradient(83.87deg, #F54180, #9353D3)`,
            backgroundOrigin: "border-box",
            backgroundClip: "padding-box, border-box",
          }}
          onPress={() => saveSettingsToLocalStorage(false)}
        >
          Accept All Cookies
        </Button>
        <Button
          fullWidth
          className="border-default-200 font-medium text-default-foreground"
          radius="lg"
          variant="bordered"
          onPress={() => saveSettingsToLocalStorage(true)}
        >
          Reject All Optional Cookies
        </Button>
        <Button
          fullWidth
          className="font-medium text-default-foreground"
          radius="lg"
          variant="light"
          onPress={() => setIsSettingsOpen(true)}
        >
          Cookie Settings
        </Button>
      </div>
    </AnimatedWrapper>
  );

  return ( ( closeCookie === false ?
    <div className="pointer-events-none fixed inset-x-0 bottom-0 px-6 pb-6 z-50">
      <ResizablePanel>
        <AnimatePresence initial={false} mode="wait">
          <LazyMotion features={domAnimation}>
            {isSettingsOpen ? cookieSettingsContent : cookiesAlertContent}
          </LazyMotion>
        </AnimatePresence>
      </ResizablePanel>
    </div>
    : null
  )
  );
}
