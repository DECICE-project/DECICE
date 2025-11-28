import React from "react";
import {Table, TableHeader, TableColumn, TableBody, TableRow, TableCell, getKeyValue} from "@nextui-org/react";

const rows = [
  {
    key: "1",
    name: "Malik Türkoğlu",
    role: "Frontend",
    status: "Active",
  },
  {
    key: "2",
    name: "Ozay Tek",
    role: "Backend",
    status: "Active",
  },
  {
    key: "3",
    name: "Jane Fisher",
    role: "Senior Developer",
    status: "Active",
  },
  {
    key: "4",
    name: "William Howard",
    role: "Community Manager",
    status: "Vacation",
  },
];

const columns = [
  {
    key: "name",
    label: "NAME",
  },
  {
    key: "role",
    label: "ROLE",
  },
  {
    key: "status",
    label: "STATUS",
  },
];

export default function App() {
    const [selectedColor, setSelectedColor] = React.useState("secondary");
    const [selectedKeys, setSelectedKeys] = React.useState(new Set(["1","2"]));
  return (
    <Table aria-label="Example table with dynamic content"
    color={selectedColor}
    disabledKeys={[ "4"]}
    selectionMode="multiple"
    defaultSelectedKeys={selectedKeys}
    >
      <TableHeader columns={columns}>
        {(column) => <TableColumn key={column.key}>{column.label}</TableColumn>}
      </TableHeader>
      <TableBody items={rows}>
        {(item) => (
          <TableRow key={item.key}>
            {(columnKey) => <TableCell>{getKeyValue(item, columnKey)}</TableCell>}
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
