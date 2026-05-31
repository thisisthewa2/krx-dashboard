import type { AlertRow } from "../types";
import { fmtKRW, fmtSignedPct } from "../utils/format";

interface Props {
  alerts: AlertRow[];
}

export function AlertSignals({ alerts }: Props) {
  return (
    <div className="card">
      <h3>오늘의 이상 신호</h3>
      <p className="desc">
        룩백 30영업일 대비 거래량 z-score ≥ 3 또는 일중 변동폭(고가-저가)/종가 ≥ 5%
        ETF. 휴면·신규상장 종목은 룩백 표본이 부족해 의도적으로 제외 (실제 시장감시 룰과
        동일한 처리).
      </p>
      {alerts.length === 0 ? (
        <div className="empty">기준을 충족하는 종목이 없습니다.</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>종목</th>
                <th>운용사</th>
                <th className="num">z(거래량)</th>
                <th className="num">일중변동</th>
                <th className="num">등락률</th>
                <th className="num">거래대금</th>
                <th>신호</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.ticker} className="alert-row">
                  <td>
                    <div>{a.name}</div>
                    <div className="ticker">{a.ticker}</div>
                  </td>
                  <td>{a.issuer ?? "—"}</td>
                  <td className="num">{a.z_volume.toFixed(2)}</td>
                  <td className="num">{(a.intraday_range_pct * 100).toFixed(2)}%</td>
                  <td className="num">
                    <span
                      className={
                        a.change_rate > 0 ? "delta-up" : a.change_rate < 0 ? "delta-down" : "delta-flat"
                      }
                    >
                      {fmtSignedPct(a.change_rate / 100)}
                    </span>
                  </td>
                  <td className="num">{fmtKRW(a.trade_value, { compact: true })}</td>
                  <td>{a.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
