// Number, duration, cost, date and size formatting.

export function fmtNum(n) {
  if (n == null || Number.isNaN(n)) return "–";
  return Number(n).toLocaleString();
}

export function fmtDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return "–";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const totalSec = ms / 1000;
  if (totalSec < 60) return `${totalSec.toFixed(1)}s`;
  const totalSecR = Math.round(totalSec);
  const m = Math.floor(totalSecR / 60);
  const s = totalSecR % 60;
  return `${m}m ${s}s`;
}

export function fmtCost(usd) {
  if (usd == null || Number.isNaN(usd)) return "–";
  return `$${Number(usd).toFixed(usd < 0.01 ? 4 : 3)}`;
}

// "Sep 27, 07:12 AM": compact form for table cells (fmtDate has the year).
export function fmtDateShort(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function fmtDate(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// Elapsed time since session start, as "+m:ss".
export function fmtElapsed(ms) {
  if (ms == null || Number.isNaN(ms) || ms < 0) return null;
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `+${m}:${String(s).padStart(2, "0")}`;
}

export function fmtBytes(n) {
  if (n == null) return null;
  return n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}
