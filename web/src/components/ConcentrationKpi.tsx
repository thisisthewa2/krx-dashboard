import type { Concentration } from "../types";
import { fmtPct } from "../utils/format";

interface Props {
  c: Concentration;
}

export function ConcentrationKpi({ c }: Props) {
  return (
    <div className="card">
      <h3>거래 쏠림 지표</h3>
      <p className="desc">
        ETF 시장 1,000여 종목 중 거래대금이 어느 정도로 집중되어 있는가. 운용사 단위 HHI 는
        '운용사 시장구조' 화면에서, 종목 단위 쏠림은 아래 지표로 본다.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
          gap: 12,
        }}
      >
        <Metric label="Top 4 비중" value={fmtPct(c.top4)} hint="CR4" />
        <Metric label="Top 10 비중" value={fmtPct(c.top10)} hint="상위 10종목 거래대금 점유율" />
        <Metric label="Top 50 비중" value={fmtPct(c.top50)} hint="상위 50종목 점유율" />
        <Metric label="Gini 계수" value={c.gini.toFixed(3)} hint="0=평등, 1=완전집중" />
      </div>
    </div>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--c-text-muted)" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, marginTop: 2, fontVariantNumeric: "tabular-nums" }}>
        {value}
      </div>
      {hint && (
        <div style={{ fontSize: 11, color: "var(--c-text-subtle)", marginTop: 2 }}>{hint}</div>
      )}
    </div>
  );
}
