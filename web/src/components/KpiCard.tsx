import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  hint?: string;
}

export function KpiCard({ label, value, sub, hint }: Props) {
  return (
    <div className="card kpi-card">
      <div className="card-title">
        <span>{label}</span>
        {hint && <span className="hint">{hint}</span>}
      </div>
      <div className="value">{value}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}
