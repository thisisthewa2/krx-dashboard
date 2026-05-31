import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { NewProductFreq as Data } from "../types";

interface Props {
  data: Data;
}

const COLORS = [
  "#2954a6",
  "#3a7bd5",
  "#5e9bd1",
  "#82a3d6",
  "#a3c0e0",
  "#b07b14",
  "#1f7a4d",
  "#7a8ba6",
  "#c9cfd9",
  "#5d6478",
];

export function NewProductFreq({ data }: Props) {
  if (data.months.length === 0 || data.series.length === 0) {
    return (
      <div className="card">
        <h3>운용사별 신상품 출시 빈도 (월간)</h3>
        <p className="desc">
          KRX상장종목정보 일별 스냅샷의 ticker diff 로 산출. 일자 데이터가 누적되면 채워집니다.
        </p>
        <div className="empty">월별 신규 상장 데이터가 아직 누적되지 않았습니다.</div>
      </div>
    );
  }

  // {month: '2026-01', '삼성자산운용': 5, '미래에셋자산운용': 3, ...}
  const rows = data.months.map((m, i) => {
    const obj: Record<string, number | string> = { month: m };
    for (const s of data.series) {
      obj[s.issuer] = s.data[i] ?? 0;
    }
    return obj;
  });

  return (
    <div className="card">
      <h3>운용사별 신상품 출시 빈도 (최근 6개월)</h3>
      <p className="desc">
        매달 새로 등장한 ETF 종목 수를 운용사별로 stack. 상품기획·상장심사 부서가 가장
        직접적으로 관심을 두는 지표 — *어떤 운용사가 어느 테마로 라인업을 빠르게 늘리고
        있는가.*
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="#eef0f4" vertical={false} />
          <XAxis dataKey="month" fontSize={11} stroke="#8a91a4" />
          <YAxis fontSize={11} stroke="#8a91a4" allowDecimals={false} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} iconSize={8} />
          {data.series.map((s, i) => (
            <Bar
              key={s.issuer}
              dataKey={s.issuer}
              stackId="a"
              fill={COLORS[i % COLORS.length]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
