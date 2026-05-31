import type { DashboardPayload } from "../types";
import { IssuerShareChart } from "../components/IssuerShareChart";
import { KpiCard } from "../components/KpiCard";
import { NewProductFreq } from "../components/NewProductFreq";
import { RankMovement } from "../components/RankMovement";

interface Props {
  data: DashboardPayload;
}

export function StructurePage({ data }: Props) {
  const issuerCount = data.issuer_share.length;
  const top1 = data.issuer_share[0];
  const top2 = data.issuer_share[1];
  const top4Sum = data.issuer_share
    .slice(0, 4)
    .reduce((acc, r) => acc + r.trade_value_share, 0);

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="grid kpi">
        <KpiCard
          label="운용사 단위 HHI"
          value={data.concentration.issuer_hhi.toFixed(0)}
          sub="0~10000 · 미국 법무부 기준 1500~2500이 '집중'"
          hint="시장구조 집중도"
        />
        <KpiCard
          label="운용사 수"
          value={issuerCount}
          sub="ETF·ETN 발행사 합산"
        />
        <KpiCard
          label="상위 4개 운용사 점유율"
          value={`${(top4Sum * 100).toFixed(1)}%`}
          sub="CR4 · 거래대금 기준"
        />
        <KpiCard
          label="1위 운용사"
          value={top1 ? top1.issuer : "—"}
          sub={
            top1 && top2
              ? `${(top1.trade_value_share * 100).toFixed(1)}% (2위 ${top2.issuer} ${(top2.trade_value_share * 100).toFixed(1)}%)`
              : "데이터 없음"
          }
        />
      </div>

      <div className="grid cols-3">
        <IssuerShareChart rows={data.issuer_share} topN={10} />
        <RankMovement rows={data.issuer_rank} />
      </div>

      <NewProductFreq data={data.new_product_freq} />
    </div>
  );
}
