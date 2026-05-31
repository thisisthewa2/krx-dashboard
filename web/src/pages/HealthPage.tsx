import type { DashboardPayload } from "../types";
import { AlertSignals } from "../components/AlertSignals";
import { ConcentrationChart } from "../components/ConcentrationChart";
import { ConcentrationKpi } from "../components/ConcentrationKpi";
import { DistributionChart } from "../components/DistributionChart";
import { DormantTable } from "../components/DormantTable";
import { KpiCard } from "../components/KpiCard";
import { fmtCount, fmtKRW, fmtPct } from "../utils/format";

interface Props {
  data: DashboardPayload;
}

export function HealthPage({ data }: Props) {
  const k = data.kpis;
  const dormantPct = k.total_count > 0 ? k.dormant_count / k.total_count : 0;
  const activePct = k.total_count > 0 ? k.active_count / k.total_count : 0;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="grid kpi">
        <KpiCard
          label="총 거래대금"
          value={fmtKRW(k.total_trade_value, { compact: true })}
          sub="기준일 ETF·ETN 거래대금 합계"
        />
        <KpiCard
          label="거래 활성 종목"
          value={fmtCount(k.active_count)}
          sub={`전체 ${fmtCount(k.total_count)}개 중 ${fmtPct(activePct)} 거래 발생`}
        />
        <KpiCard
          label="휴면 ETF"
          value={fmtCount(k.dormant_count)}
          sub={`거래대금 0원 10일+ 연속 · 전체의 ${fmtPct(dormantPct)}`}
          hint="좀비 ETF"
        />
        <KpiCard
          label="최근 30일 신규 상장"
          value={fmtCount(k.new_listings_30d)}
          sub="KRX상장종목정보 일별 diff"
        />
      </div>

      <div className="grid cols-2">
        <ConcentrationKpi c={data.concentration} />
        <DistributionChart
          bins={data.concentration.log_value_histogram.bins}
          counts={data.concentration.log_value_histogram.counts}
        />
      </div>

      <ConcentrationChart data={data.concentration_trend} />

      <div className="grid cols-2">
        <AlertSignals alerts={data.alerts} />
        <DormantTable rows={data.dormant} />
      </div>
    </div>
  );
}
