import type { IssuerRankRow } from "../types";

interface Props {
  rows: IssuerRankRow[];
}

export function RankMovement({ rows }: Props) {
  const sorted = [...rows].sort((a, b) => a.rank_today - b.rank_today).slice(0, 12);
  return (
    <div className="card">
      <h3>운용사 순위 변동</h3>
      <p className="desc">
        직전 거래일 대비 거래대금 기준 순위 변동. 양수(▲)는 상승. 시장 점유율 재편 신호를
        포착하는 가장 직관적인 보조 지표.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th className="num" style={{ width: 40 }}>#</th>
              <th>운용사</th>
              <th className="num">전일</th>
              <th className="num">변동</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const delta = r.delta ?? 0;
              const sign =
                delta > 0 ? "▲" : delta < 0 ? "▼" : delta === 0 && r.rank_prev ? "—" : "•";
              const cls =
                delta > 0
                  ? "delta-up"
                  : delta < 0
                  ? "delta-down"
                  : "delta-flat";
              return (
                <tr key={r.issuer}>
                  <td className="num">{r.rank_today}</td>
                  <td>{r.issuer}</td>
                  <td className="num">{r.rank_prev ? r.rank_prev : "—"}</td>
                  <td className={`num ${cls}`}>
                    {sign} {Math.abs(delta) || ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
