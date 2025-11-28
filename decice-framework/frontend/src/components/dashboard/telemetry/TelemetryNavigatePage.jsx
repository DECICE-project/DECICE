import React from 'react'
import { Card, CardHeader, CardBody,Chip, Button, Kbd, Link } from "@nextui-org/react";
const grafana_url = import.meta.env.VITE_GRAFANA_URL;
function TelemetryNavigatePage() {
  return (
    <div>
          <h1 className="mb-3 text-2xl">Telemetry Dashboard</h1>

        <p>you are automatically redirected to the new page.
On the page you are directed to, you will see the telemetry dashboard login screen. After entering your information, you can access the telemetry panel.
</p>
<p>
If you are not automatically redirected, you can press the button below.</p>
<div className="flex justify-center" ><Button  as={Link} target="_blank" href={`${grafana_url}`} color="primary" className="mb-1">Go to Telemetry Dashboard</Button></div>
<div className="flex justify-center" ><Kbd color="primary">{`${grafana_url}`} </Kbd></div>
        </div>
  )
}

export default TelemetryNavigatePage
