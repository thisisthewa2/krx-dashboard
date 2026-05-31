import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ConcentrationTrendPoint } from "../types";
import { fmtDate, fmtPct } from "../utils/format";

interface Props {
  data: ConcentrationTrendPoint[];
}

export function ConcentrationChart({ data }: Props) {
  return (
    <div className="card">
      <h3>거래 쏠림 · 운용사 집중도 추세</h3>
      <p className="desc">
        상위 10종목 거래대금 비중과 운용사 단위 HHI 의 일자별 추세. 두 선이 동시에
        오른다면 시장 자금이 소수 종목과 소수 운용사로 동시에 집중되고 있다는 신호.
      </p>
      {data.length === 0 ? (
        <div className="empty">추세 산출에 필요한 일자 데이터가 아직 누적되지 않았습니다.</div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
            <CartesianGrid stroke="#eef0f4" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d) => d.slice(5)}
              fontSize={11}
              stroke="#8a91a4"
            />
            <YAxis
              yAxisId="left"
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              fontSize={11}
              stroke="#8a91a4"
              domain={[0, "dataMax + 0.05"]}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tickFormatter={(v) => v.toFixed(0)}
              fontSize={11}
              stroke="#8a91a4"
            />
            <Tooltip
              labelFormatter={(d) => fmtDate(String(d))}
              formatter={(value: number, name: string) => {
                if (name === "top10_share") return [fmtPct(value), "Top10 거래대금 비중"];
                if (name === "issuer_hhi") return [value.toFixed(0), "운용사 HHI"];
                return [value, name];
              }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="top10_share"
              stroke="#2954a6"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="issuer_hhi"
              stroke="#b07b14"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
      <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: 12, color: "var(--c-text-muted)" }}>
        <span>
          <span className="legend-dot" style={{ background: "#2954a6" }} />
          Top10 거래대금 비중 (좌)
        </span>
        <span>
          <span className="legend-dot" style={{ background: "#b07b14" }} />
          운용사 HHI (우)
        </span>
      </div>
    </div>
  );
}
