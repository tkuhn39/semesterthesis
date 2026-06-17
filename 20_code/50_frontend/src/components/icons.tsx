// Minimal inline line-icons (stroke = currentColor), 18×18 by default.
import type { JSX } from "react";

type IconProps = { className?: string };
const base = (className?: string) => ({
  className: className ?? "ico",
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function IconOverview(p: IconProps): JSX.Element {
  return (
    <svg {...base(p.className)}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  );
}
export function IconGear(p: IconProps): JSX.Element {
  return (
    <svg {...base(p.className)}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" />
    </svg>
  );
}
export function IconGauge(p: IconProps): JSX.Element {
  return (
    <svg {...base(p.className)}>
      <path d="M4 19a8 8 0 1 1 16 0" />
      <path d="M12 19l4-6" />
      <circle cx="12" cy="19" r="1" />
    </svg>
  );
}
export function IconActivity(p: IconProps): JSX.Element {
  return (
    <svg {...base(p.className)}>
      <path d="M3 12h4l2.5 7 5-14L17 12h4" />
    </svg>
  );
}
export function IconGrid(p: IconProps): JSX.Element {
  return (
    <svg {...base(p.className)}>
      <path d="M4 4h16v16H4zM4 9h16M4 14h16M9 4v16M14 4v16" />
    </svg>
  );
}
export function IconSpark(p: IconProps): JSX.Element {
  return (
    <svg {...base(p.className)}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2" />
    </svg>
  );
}
