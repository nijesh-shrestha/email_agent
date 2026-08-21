export const NPT_TIME_ZONE = "Asia/Kathmandu";

export function formatNptDateTime(value: string | Date): string {
  return new Date(value).toLocaleString("en-US", {
    timeZone: NPT_TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function toNptDateTimeInput(date: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: NPT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date).reduce<Record<string, string>>((result, part) => {
    result[part.type] = part.value;
    return result;
  }, {});

  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

export function nptInputToUtc(value: string): string {
  return new Date(`${value}:00+05:45`).toISOString();
}

export function formatNptDate(value: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: NPT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(value);
}
