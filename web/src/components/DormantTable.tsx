import type { DormantRow } from "../types";
import { fmtCount } from "../utils/format";

interface Props {
  rows: DormantRow[];
}

export function DormantTable({ rows }: Props) {
  return (
    <div className="card">
      <h3>휴면 ETF / 저유동성 종목</h3>
      <p className="desc">
        거래대금 0원이 10영업일 이상 연속된 ETF. 이른바 '좀비 ETF'로 분류되어 운용사·거래소
        모두 정리 대상으로 검토하는 영역.
      </p>
      {rows.length === 0 ? (
        <div className="empty">휴면 종목이 없습니다.</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>종목</th>
                <th>운용사</th>
                <th className="num">무거래 연속일</th>
                <th className="num">30일 평균 거래량</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 15).map((r) => (
                <tr key={r.ticker}>
                  <td>
                    <div>{r.name ?? r.ticker}</div>
                    <div className="ticker">{r.ticker}</div>
                  </td>
                  <td>{r.issuer ?? "—"}</td>
                  <td className="num">{r.consecutive_no_trade_days}일</td>
                  <td className="num">{fmtCount(r.avg_volume_30d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > 15 && (
        <div style={{ fontSize: 12, color: "var(--c-text-subtle)", marginTop: 6 }}>
          전체 {rows.length}개 중 상위 15개 표시
        </div>
      )}
    </div>
  );
}
