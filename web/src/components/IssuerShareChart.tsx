import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { IssuerShareRow } from "../types";
import { fmtPct } from "../utils/format";

interface Props {
  rows: IssuerShareRow[];
  topN?: number;
}

const VALUE_COLOR = "#2954a6";
const COUNT_COLOR = "#82a3d6";

export function IssuerShareChart({ rows, topN = 10 }: Props) {
  const data = rows.slice(0, topN).map((r) => ({
    issuer: r.issuer,
    value_share: r.trade_value_share,
    count_share: r.ticker_count_share,
  }));

  return (
    <div className="card">
      <h3>운용사별 점유율 (Top {topN})</h3>
      <p className="desc">
        같은 운용사라도 *거래대금 점유율*과 *종목수 점유율*이 크게 차이날 수 있다. 종목은
        많은데 거래대금이 적다면 휴면 종목 누적, 반대면 소수 대표 ETF 가 거래대금을 끌고
        있다는 뜻.
      </p>
      <ResponsiveContainer width="100%" height={Math.max(220, data.length * 28)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
        >
          <CartesianGrid stroke="#eef0f4" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            fontSize={11}
            stroke="#8a91a4"
          />
          <YAxis
            type="category"
            dataKey="issuer"
            width={120}
            fontSize={11}
            stroke="#8a91a4"
          />
          <Tooltip
            formatter={(v: number, k: string) => [
              fmtPct(v),
              k === "value_share" ? "거래대금 점유율" : "종목수 점유율",
            ]}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(k) => (k === "value_share" ? "거래대금 점유율" : "종목수 점유율")}
          />
          <Bar dataKey="value_share" fill={VALUE_COLOR}>
            {data.map((_, i) => (
              <Cell key={i} fill={VALUE_COLOR} />
            ))}
          </Bar>
          <Bar dataKey="count_share" fill={COUNT_COLOR}>
            {data.map((_, i) => (
              <Cell key={i} fill={COUNT_COLOR} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
