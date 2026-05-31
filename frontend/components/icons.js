// Minimal inline stroke icons (no dependency). 24x24 viewBox.
const s = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };

export const IconHome = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></svg>
);
export const IconGrid = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></svg>
);
export const IconLayers = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></svg>
);
export const IconUsers = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><circle cx="9" cy="8" r="3.2" /><path d="M3.5 20a5.5 5.5 0 0 1 11 0" /><path d="M16 5.2a3.2 3.2 0 0 1 0 5.6" /><path d="M17.5 20a5.5 5.5 0 0 0-3-4.9" /></svg>
);
export const IconScale = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><path d="M12 3v18" /><path d="M5 7h14" /><path d="m5 7-2.5 5a2.5 2.5 0 0 0 5 0L5 7Z" /><path d="m19 7-2.5 5a2.5 2.5 0 0 0 5 0L19 7Z" /><path d="M8 21h8" /></svg>
);
export const IconWallet = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><rect x="3" y="6" width="18" height="13" rx="3" /><path d="M3 9h18" /><circle cx="16.5" cy="13" r="1.2" fill="currentColor" stroke="none" /></svg>
);
export const IconClock = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
);
export const IconFlag = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><path d="M5 21V4" /><path d="M5 4h11l-1.5 3.5L16 11H5" /></svg>
);
export const IconTarget = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.5" /></svg>
);
export const IconAlert = (p) => (
  <svg viewBox="0 0 24 24" {...s} {...p}><path d="M12 3 2.5 20h19L12 3Z" /><path d="M12 10v4" /><circle cx="12" cy="17" r=".6" fill="currentColor" stroke="none" /></svg>
);
