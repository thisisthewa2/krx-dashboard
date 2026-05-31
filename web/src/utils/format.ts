export function fmtKRW(value: number, opts?: { compact?: boolean }): string {
  if (!Number.isFinite(value)) return "-";
  const abs = Math.abs(value);
  if (opts?.compact) {
    const units: [number, string][] = [
      [1e12, "조"],
      [1e8, "억"],
      [1e4, "만"],
    ];
    for (const [u, label] of units) {
      if (abs >= u) {
        return `${(value / u).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}${label}원`;
      }
    }
  }
  return `${value.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}원`;
}

export function fmtCount(value: number): string {
  if (!Number.isFinite(value)) return "-";
  return value.toLocaleString("ko-KR");
}

export function fmtPct(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "-";
  return `${(value * 100).toFixed(digits)}%`;
}

export function fmtSignedPct(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "-";
  const v = (value * 100).toFixed(digits);
  return value > 0 ? `+${v}%` : `${v}%`;
}

export function fmtDate(iso: string): string {
  if (!iso) return "-";
  const [y, m, d] = iso.split("-");
  return `${y}.${m}.${d}`;
}

export function fmtDateTimeKST(iso: string): string {
  if (!iso) return "-";
  try {
    const date = new Date(iso);
    return date.toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "Asia/Seoul",
    });
  } catch {
    return iso;
  }
}
