import type {RadioProps} from "@nextui-org/react";

import React from "react";
import {useRadio, VisuallyHidden} from "@nextui-org/react";

import {cn} from "./cn";

export const PlanCustomRadio = (props: RadioProps) => {
  const {
    Component,
    children,
    description,
    getBaseProps,
    getWrapperProps,
    getInputProps,
    getLabelProps,
    getControlProps,
  } = useRadio(props);

  const wrapperProps = getWrapperProps();

  return (
    <Component
      {...getBaseProps()}
      className={cn(
        "group px-4 py-4",
        "max-w-[300px] cursor-pointer gap-4 rounded-lg border-2 border-transparent",
        "flex-1 bg-default-100 data-[selected=true]:border-default-foreground",
      )}
    >
      {/*header*/}
      <section className={"flex flex-row-reverse justify-between hover:bg-content2"}>
        <VisuallyHidden>
          <input {...getInputProps()} />
        </VisuallyHidden>
        <span
          {...getWrapperProps()}
          className={cn(
            wrapperProps["className"],
            "border-2 border-default",
            "group-data-[selected=true]:border-default-foreground",
          )}
        >
          <span
            {...getControlProps()}
            className={cn(
              "z-10 h-2 w-2 origin-center scale-0 rounded-full bg-default-foreground text-primary-foreground opacity-0 transition-transform-opacity group-data-[selected=true]:scale-100 group-data-[selected=true]:opacity-100 motion-reduce:transition-none",
            )}
          />
        </span>
        <div>{description && <span {...getLabelProps()}>{description}</span>}</div>
      </section>
      {/*  content*/}
      {children && <div>{children}</div>}
    </Component>
  );
};
