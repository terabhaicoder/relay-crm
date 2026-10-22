const paths: Record<string, string> = {
  workbench: "M4 5h16v16H4z M8 3v4 M16 3v4 M8 12l2 2 5-5 M8 18h8",
  dashboard: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  leads:
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M20 8v6 M17 11h6",
  contacts:
    "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8",
  accounts:
    "M4 21V5h10v16 M14 10h6v11 M2 21h20 M7 8h4 M7 12h4 M7 16h4 M17 13v2 M17 17v2",
  deals: "M3 4h5v16H3z M10 4h5v11h-5z M17 4h4v14h-4z",
  quotations: "M5 3h10l4 4v14H5z M14 3v5h5 M8 12h8 M8 16h5",
  activities: "M9 5H5v16h14V5h-4 M9 3h6v4H9z M8 12l2 2 5-5 M8 18h8",
  calendar: "M4 5h16v16H4z M4 10h16 M8 3v4 M16 3v4 M8 14h2 M14 14h2 M8 18h2",
  campaigns: "M3 10v5h4l10 4V6L7 10H3 M7 15l2 6h3l-2-5 M20 8v8",
  tickets:
    "M4 11V9a8 8 0 0 1 16 0v2 M4 11H2v7h4v-7H4 M20 11h2v7h-4v-7h2 M18 18v3h-6",
  reports: "M4 20h17 M7 16V9 M12 16V4 M17 16v-5",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2",
  search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6",
  plus: "M12 5v14 M5 12h14",
  close: "M6 6l12 12 M6 18 18 6",
  arrow: "M5 12h14 M14 7l5 5-5 5",
  down: "m6 9 6 6 6-6",
  check: "m5 12 4 4L19 6",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2",
  logout: "M9 4H4v16h5 M9 12h12 M17 8l4 4-4 4",
  mail: "M3 5h18v14H3z M3 5l9 8 9-8",
  phone: "M5 3h4l2 5-3 2a15 15 0 0 0 6 6l2-3 5 2v4c0 3-7 2-12-3S2 3 5 3",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  download: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
  help: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4 M12 17h.01",
};
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] ?? paths.dashboard} />
    </svg>
  );
}
