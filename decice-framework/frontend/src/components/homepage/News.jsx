import { useMemo, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  Chip,
  Input,
} from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { useContentFeed } from "./useContentFeed";

const parseDateSafe = (value) => {
  if (!value) return { label: "Unknown date", timestamp: 0 };
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return { label: value, timestamp: 0 };
  }
  return {
    label: new Date(parsed).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }),
    timestamp: parsed,
  };
};

const truncate = (value, limit = 320) => {
  if (!value) return "";
  if (value.length <= limit) return value;
  return `${value.slice(0, limit)}...`;
};

function News() {
  const [query, setQuery] = useState("");

  const { data, status, error, refetch } = useContentFeed("news");

  const items = useMemo(() => {
    const raw = data?.payload?.items ?? [];
    return raw
      .map((item) => {
        const dateInfo = parseDateSafe(item.date);
        return {
          ...item,
          readableDate: dateInfo.label,
          timestamp: dateInfo.timestamp,
        };
      })
      .sort((a, b) => b.timestamp - a.timestamp);
  }, [data]);

  const filteredItems = useMemo(() => {
    if (!query.trim()) return items;
    const normalized = query.toLowerCase();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(normalized) ||
        item.content?.toLowerCase().includes(normalized)
    );
  }, [items, query]);

  const renderStatus = () => {
    if (status === "loading") {
      return (
        <div className="flex items-center gap-2 text-sm text-default-400">
          <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
          Loading news...
        </div>
      );
    }

    if (status === "error") {
      return (
        <div className="flex flex-col gap-2 rounded-md border border-danger px-3 py-2 text-sm text-danger">
          <span>{error || "Unable to load the newsroom feed."}</span>
          <Button size="sm" variant="light" onPress={refetch}>
            Retry
          </Button>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="order-2 md:order-1 md:grow">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <p className="font-nycd text-5xl text-indigo-500 font-normal">
            News
          </p>
          <p className="text-sm text-default-400">
            Latest stories fetched directly from the DECICE newsroom.
          </p>
        </div>
        <Input
          value={query}
          onValueChange={setQuery}
          placeholder="Search headline or keyword..."
          variant="flat"
          startContent={
            <Icon
              icon="solar:magnifer-linear"
              className="text-gray-400 w-4 h-4"
            />
          }
          radius="sm"
          size="sm"
          className="max-w-md"
          classNames={{
            inputWrapper:
              "!bg-gray-100 dark:!bg-gray-100 !border-none shadow-none",
            input:
              "bg-transparent !border-none focus:outline-none focus-visible:outline-none",
          }}
        />
      </div>
      {renderStatus()}
      <ol className="relative border-s border-gray-200 dark:border-gray-700">
        {filteredItems.map((item, index) => (
          <li
            key={`${item.title}-${item.date}`}
            className="group ms-6 mb-8"
          >
            <span className="absolute flex items-center justify-center w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full -start-3 ring-8 ring-white dark:ring-gray-900 dark:bg-indigo-500/30">
              <Icon icon="solar:news-linear" className="w-3 h-3" />
            </span>
            <Card className="border border-transparent bg-transparent transition hover:border-indigo-200 hover:bg-indigo-50/40 dark:hover:bg-indigo-500/10">
              <CardBody className="px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    {item.title}
                  </h3>
                  {index === 0 && (
                    <Chip size="sm" color="secondary" variant="flat">
                      Latest
                    </Chip>
                  )}
                </div>
                <time className="block text-xs text-gray-400">
                  {item.readableDate}
                </time>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 whitespace-pre-line">
                  {truncate(item.content || item.excerpt, 320)}
                </p>
                {item.link && (
                  <Button
                    as="a"
                    href={item.link}
                    target="_blank"
                    rel="noreferrer"
                    color="primary"
                    size="sm"
                    className="mt-3 text-xs px-3 py-1 w-fit rounded-full"
                  >
                    Read full article
                  </Button>
                )}
              </CardBody>
            </Card>
          </li>
        ))}
        {filteredItems.length === 0 && status === "success" && (
          <p className="text-sm text-default-400">
            No news matched your search query.
          </p>
        )}
      </ol>
    </div>
  );
}

export default News;
