import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  bins: number[];
  counts: number[];
}

export function DistributionChart({ bins, counts }: Props) {
  const data = bins.map((b, i) => ({
    bin: b,
    count: counts[i],
    label: `10^${b.toFixed(1)}`,
  }));

  return (
    <div className="card">
      <h3>종목별 거래대금 분포 (로그)</h3>
      <p className="desc">
        x축은 종목별 일 거래대금의 상용로그. 분포가 우측으로 길게 늘어진 두꺼운 꼬리는
        소수 대형 종목이 시장 거래대금을 가져가고 있음을 의미.
      </p>
      {counts.length === 0 ? (
        <div className="empty">집계 데이터 없음</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
            <CartesianGrid stroke="#eef0f4" vertical={false} />
            <XAxis
              dataKey="label"
              fontSize={10}
              stroke="#8a91a4"
              interval={1}
            />
            <YAxis fontSize={11} stroke="#8a91a4" />
            <Tooltip
              labelFormatter={(l) => `거래대금 ≈ ${l}원`}
              formatter={(v: number) => [v.toLocaleString("ko-KR"), "종목 수"]}
            />
            <Bar dataKey="count" fill="#2954a6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
