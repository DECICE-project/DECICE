import React from 'react';
import { Card, CardBody, Button } from "@nextui-org/react";
import { Icon } from "@iconify/react";

export const ErrorMessage = ({ message }) => {
  return (
    <div className="w-full min-h-[400px] flex flex-col items-center justify-center p-6">
      <Card className="w-[300px] bg-danger-50 dark:bg-danger/20 border-danger-100 dark:border-danger/30">
        <CardBody className="py-8 flex flex-col items-center gap-4">
          <div className="rounded-full bg-danger/10 p-3">
            <Icon icon="solar:danger-circle-bold" className="w-8 h-8 text-danger"/>
          </div>
          <div className="text-center">
            <h3 className="text-lg font-medium text-danger">Error</h3>
            <p className="text-small text-danger-500 mt-1">{message}</p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}; 