import { useState } from "react";
import {DateRangePicker} from "@nextui-org/react";
import {parseZonedDateTime, getLocalTimeZone} from "@internationalized/date";
import {useDateFormatter} from "@react-aria/i18n";
export default function App() {

    const [value, setValue] = useState({
        start: parseZonedDateTime("2024-04-01T00:45[America/Los_Angeles]"),
        end: parseZonedDateTime("2024-04-08T11:15[America/Los_Angeles]"),
      });

      let formatter = useDateFormatter({dateStyle: "long"});

  return (
    <div className="w-full max-w-xl flex flex-row gap-4">
      <DateRangePicker
        label="Time duration"
        hideTimeZone
        visibleMonths={3}
        value={value}
        onChange={setValue}
      />
              <p className="text-default-500 text-sm">
          Selected date:{" "}
          {value
            ? formatter.formatRange(
                value.start.toDate(getLocalTimeZone()),
                value.end.toDate(getLocalTimeZone()),
              )
            : "--"}
        </p>
    </div>
  );
}
