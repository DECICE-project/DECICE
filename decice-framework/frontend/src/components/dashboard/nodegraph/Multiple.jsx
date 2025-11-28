import {Tabs, Tab, Card, CardBody} from "@nextui-org/react";
import VisNetwork from "./VisNetwork";
import RawNetwork from "./RawNetworkGraph/RawNetwork";

export default function App() {
  return (
    <div className="flex w-full flex-col">
      <Tabs aria-label="Options">
        <Tab key="network with groups" title="Vertexpool network graph">
       <VisNetwork/>
        </Tab>
        <Tab key="all network" title="Raw latency graph">
        <RawNetwork/>
        </Tab>
      </Tabs>
    </div>
  );
}
