"use client";

import * as React from "react";
import {RadioGroup, Select, SelectItem, Spacer} from "@nextui-org/react";

import {cn} from "./cn";
import {ThemeCustomRadio} from "./theme-custom-radio";
import { useThemeProvider } from '../ThemeContext';
import SwitchCell from "./switch-cell";

interface AppearanceSettingCardProps {
  className?: string;
}

const fontSizeOptions = [
  {label: "Small", value: "small", description: "font size 14px"},
  {label: "Medium", value: "medium", description: "font size 16px"},
  {label: "Large", value: "large", description: "font size 18px"},
];

const AppearanceSetting = React.forwardRef<HTMLDivElement, AppearanceSettingCardProps>(
  ({className, ...props}, ref) => {

    const { currentTheme, changeCurrentTheme } = useThemeProvider();
  return(
    <div ref={ref} className={cn("p-2", className)} {...props}>
      {/* Theme */}
      <div>
        <p className="text-base font-medium text-default-700">Theme</p>
        <p className="mt-1 text-sm font-normal text-default-400">
          Change the appearance of the web.
        </p>
        {/* Theme radio group */}
        <RadioGroup className="mt-4 flex-wrap" orientation="horizontal" value={currentTheme === "light" ? "free" : "pro"}>
          <ThemeCustomRadio value="free" variant="light" onClick={() => changeCurrentTheme("light")}>
            Light
          </ThemeCustomRadio>
          <ThemeCustomRadio value="pro" variant="dark" onClick={() => changeCurrentTheme("dark")}>
            Dark
          </ThemeCustomRadio>
        </RadioGroup>
      </div>
      <Spacer y={4} />
    </div>
  )
});

AppearanceSetting.displayName = "AppearanceSetting";

export default AppearanceSetting;
