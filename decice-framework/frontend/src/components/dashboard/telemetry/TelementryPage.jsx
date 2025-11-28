import {useState} from "react"
import {CircularProgress, Card, CardBody, CardFooter, Chip} from "@nextui-org/react";
import DatePicker from "../common/DatePicker";
import Table from "../common/Table";

const CircleBarChart = (props) => {

  return(
    <Card className={`w-[240px] h-[240px] border-none bg-gradient-to-br ${props.bgColor}`}>
    <CardBody className="justify-center items-center pb-0">
      <CircularProgress
        classNames={{
          svg: "w-36 h-36 drop-shadow-md",
          indicator: "stroke-white",
          track: "stroke-white/10",
          value: "text-3xl font-semibold text-white",
        }}
        value={props.value}
        strokeWidth={5}
        showValueLabel={true}
      />
    </CardBody>
    <CardFooter className="justify-center items-center pt-0 flex-col">
      <Chip
        classNames={{
          base: "border-1 border-white/30",
          content: "text-white/90 text-small font-semibold",
        }}
        variant="bordered"
      >
        {props.text}
      </Chip>
    <h2 className="font-bold text-white">{props.title}</h2>
    </CardFooter>
  </Card>
  )
}


export default function App() {
const[value, setValue] = useState(50);
  return (
    <div>

      <h1 className="font-bold text-2xl mb-3">Compute</h1>
      <DatePicker/>
      <Table/>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      <CircleBarChart value={100} title={"Instances"} text={"Used 3 of 3"} bgColor={"from-zinc-300 to-slate-700"}/>
 <CircleBarChart value={100} title={"VCPUs"} text={"Used 12 of 12"} bgColor={"from-violet-500 to-fuchsia-500"}/>
 <CircleBarChart value={50} title={"RAM"} text={"Used 12GB of 24GB"} bgColor={"from-violet-500 to-fuchsia-500"}/>
      </div>


      <h1 className="font-bold text-2xl my-3">Volume</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      <CircleBarChart value={50} title={"Volumes"} text={"Used 3 of 6"} bgColor={"from-violet-500 to-fuchsia-500"}/>
 <CircleBarChart value={0} title={"Volume Snapshots"} text={"Used 0 of 10"} bgColor={"from-violet-500 to-fuchsia-500"}/>
 <CircleBarChart value={80} title={"Volume Storage"} text={"Used 120GB of 150GB"} bgColor={"from-violet-500 to-fuchsia-500"}/>
      </div>

      <h1 className="font-bold text-2xl my-3">Network</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      <CircleBarChart value={100} title={"Floating IPs"} text={"Allocated 3 of 3"} bgColor={"from-violet-500 to-fuchsia-500"}/>
 <CircleBarChart value={20} title={"Security Groups"} text={"Used 4 of 20"} bgColor={"from-violet-500 to-fuchsia-500"}/>
 <CircleBarChart value={18} title={"Security Groups Rules"} text={"Used 18 of 100"} bgColor={"from-violet-500 to-fuchsia-500"}/>
      </div>


    </div>


  );
}
