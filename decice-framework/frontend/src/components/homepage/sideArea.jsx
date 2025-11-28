import { useMemo, useState } from "react";
import {
  Avatar,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Chip,
  Input,
  Link,
} from "@nextui-org/react";
import { Icon } from "@iconify/react";
import { useContentFeed } from "./useContentFeed";

const partnerPlaceholder =
  "https://dummyimage.com/80x80/1e1b4b/ffffff.png&text=DEC";

function truncateText(text, max = 140) {
  if (!text) return "";
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...`;
}

export default function SideArea() {
  const [partnerQuery, setPartnerQuery] = useState("");
  const [visiblePartners, setVisiblePartners] = useState(4);

  const {
    data: consortiumData,
    status: consortiumStatus,
    error: consortiumError,
    refetch: refetchConsortium,
  } = useContentFeed("consortium");

  const {
    data: eventData,
    status: eventStatus,
    error: eventError,
    refetch: refetchEvents,
  } = useContentFeed("events");

  const partners = consortiumData?.payload?.partners ?? [];
  const events = eventData?.payload?.events ?? [];

  const filteredPartners = useMemo(() => {
    if (!partnerQuery.trim()) {
      return [...partners].sort((a, b) => a.name.localeCompare(b.name));
    }
    return partners
      .filter((partner) =>
        partner.name.toLowerCase().includes(partnerQuery.toLowerCase())
      )
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [partners, partnerQuery]);

  const partnerList =
    filteredPartners.length > 0
      ? filteredPartners.slice(0, visiblePartners)
      : [];

  const renderStatus = (status, errorMessage, onRetry) => {
    if (status === "loading") {
      return (
        <div className="flex items-center gap-2 text-sm text-default-400 px-1 py-2">
          <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
          Loading data...
        </div>
      );
    }

    if (status === "error") {
      return (
        <div className="flex items-center justify-between rounded-md border border-danger px-3 py-2 text-sm text-danger">
          <span>{errorMessage || "Unable to fetch data."}</span>
          <Button size="sm" variant="light" onPress={onRetry}>
            Retry
          </Button>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="mt-7 md:mt-0 space-y-7">
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="font-nycd text-4xl text-indigo-500 font-normal">
            Consortium
          </p>
          <Chip color="secondary" variant="flat" className="capitalize">
            {partners.length} partners
          </Chip>
        </div>
        <Input
          value={partnerQuery}
          onValueChange={setPartnerQuery}
          placeholder="Search partner..."
          variant="flat"
          size="sm"
          radius="sm"
          className="mb-6"
          startContent={
            <Icon
              icon="solar:magnifer-linear"
              className="text-gray-400 w-4 h-4"
            />
          }
          classNames={{
            inputWrapper:
              "!bg-gray-100 dark:!bg-gray-100 !border-none shadow-none",
            input:
              "bg-transparent !border-none focus:outline-none focus-visible:outline-none",
          }}
        />
        {renderStatus(consortiumStatus, consortiumError, refetchConsortium)}
        <div className="space-y-3">
          {partnerList.map((partner) => (
            <Card key={partner.name} className="max-w-5xl">
              <CardHeader className="justify-between">
                <div className="flex gap-4">
                  <Avatar
                    isBordered
                    radius="md"
                    size="lg"
                    src={partner.logo || partnerPlaceholder}
                    name={partner.name}
                    referrerPolicy="no-referrer"
                    fallback={
                      <div className="w-full h-full flex items-center justify-center text-[10px]">
                        DEC
                      </div>
                    }
                  />
                  <div className="flex flex-col gap-1">
                    <h4 className="text-sm font-semibold text-default-600">
                      {partner.name}
                    </h4>
                  </div>
                </div>
              </CardHeader>
              <CardBody className="px-4 py-0 text-xs text-default-500">
                <p className="mb-2">{truncateText(partner.description, 220)}</p>
              </CardBody>
              <CardFooter className="flex flex-wrap gap-2">
                {partner.links?.slice(0, 3).map((link) => (
                  <Link
                    key={`${partner.name}-${link.url}`}
                    href={link.url}
                    isExternal
                    className="text-xs text-indigo-500 underline-offset-2 hover:underline"
                  >
                    {link.label}
                  </Link>
                ))}
              </CardFooter>
            </Card>
          ))}
        </div>
        {filteredPartners.length === 0 && consortiumStatus === "success" && (
          <div className="text-sm text-default-400 mt-3">
            No partners matched your search.
          </div>
        )}
        {filteredPartners.length > visiblePartners && (
          <Button
            className="mt-4"
            size="sm"
            variant="bordered"
            onPress={() => setVisiblePartners((prev) => prev + 4)}
          >
            Show more
          </Button>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/40 dark:bg-slate-900/40 p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="font-nycd text-3xl text-indigo-500 font-normal">
            Events
          </p>
          <Chip color="secondary" variant="flat" className="capitalize">
            {events.length} events
          </Chip>
        </div>
        {renderStatus(eventStatus, eventError, refetchEvents)}
        <ul className="space-y-3">
          {events.slice(0, 10).map((event) => (
            <li key={`${event.title}-${event.date}`} className="flex gap-3">
              <span className="text-indigo-500 shrink-0">—</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-default-600 break-words">
                  {event.title}
                </p>
                <p className="text-xs text-default-400 break-words">
                  {event.date}
                  {event.location ? ` • ${event.location}` : ""}
                </p>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  {event.organiser && (
                    <Chip size="sm" variant="flat" color="secondary" className="max-w-full">
                      <span className="truncate block max-w-[180px]">{event.organiser}</span>
                    </Chip>
                  )}
                  {event.link && (
                    <Link
                      href={event.link}
                      isExternal
                      className="text-xs text-indigo-500 shrink-0"
                    >
                      Details
                    </Link>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
        {events.length === 0 && eventStatus === "success" && (
          <p className="text-sm text-default-400">
            No events available.
          </p>
        )}
      </div>

      <a
        href="https://www.decice.eu"
        target="_blank"
        rel="noopener noreferrer"
        className="block rounded-lg border border-slate-200 dark:border-slate-800 dark:bg-gradient-to-t dark:from-slate-800 dark:to-slate-800/30 p-5 hover:border-indigo-300 dark:hover:border-indigo-500 transition-colors cursor-pointer"
      >
        <div className="flex items-center space-x-3 mb-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="20">
            <path
              fill="#38BDF8"
              fillRule="evenodd"
              d="M.73 6.173a9.92 9.92 0 0 1 3.527-4.488A9.294 9.294 0 0 1 9.58 0h.737v4.67l.14-.226a9.68 9.68 0 0 1 4.3-3.683A9.205 9.205 0 0 1 20.29.192a9.461 9.461 0 0 1 4.904 2.737 10.143 10.143 0 0 1 2.622 5.12c.37 1.94.18 3.95-.545 5.778a9.92 9.92 0 0 1-3.528 4.488A9.294 9.294 0 0 1 18.42 20h-.737v-4.67a10.459 10.459 0 0 1-.14.226 9.68 9.68 0 0 1-4.3 3.683 9.205 9.205 0 0 1-5.534.569 9.461 9.461 0 0 1-4.904-2.737 10.143 10.143 0 0 1-2.622-5.12C-.186 10.01.004 8 .73 6.173ZM8.841 10V1.573a7.89 7.89 0 0 0-3.766 1.391A8.394 8.394 0 0 0 2.09 6.762a8.808 8.808 0 0 0-.462 4.889 8.583 8.583 0 0 0 2.219 4.332 8.006 8.006 0 0 0 4.15 2.316 7.789 7.789 0 0 0 4.683-.482 8.18 8.18 0 0 0 3.528-2.95 4.958 4.958 0 0 1-2.209.518c-2.849 0-5.158-2.411-5.158-5.385Zm10.316 8.427a7.89 7.89 0 0 0 3.766-1.391 8.393 8.393 0 0 0 2.985-3.798 8.807 8.807 0 0 0 .462-4.889 8.583 8.583 0 0 0-2.219-4.332 8.006 8.006 0 0 0-4.15-2.316 7.789 7.789 0 0 0-4.683.482 8.179 8.179 0 0 0-3.528 2.95A4.958 4.958 0 0 1 14 4.615c2.849 0 5.158 2.411 5.158 5.385v8.427Z"
            />
          </svg>
        </div>
        <div className="font-aspekta font-[650] mb-1">decice.eu</div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Visit our main website for more detailed updates.
        </p>
      </a>
    </div>
  );
}
