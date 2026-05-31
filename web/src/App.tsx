import { useEffect, useState } from "react";
import { loadLatest } from "./api";
import { ReliabilityFooter } from "./components/ReliabilityFooter";
import { HealthPage } from "./pages/HealthPage";
import { StructurePage } from "./pages/StructurePage";
import type { DashboardPayload } from "./types";
import { fmtDate } from "./utils/format";

type Tab = "health" | "structure";

export function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("health");

  useEffect(() => {
    loadLatest()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>KRX ETF Market Monitor</h1>
        <p className="subtitle">
          공공데이터로 만든 한국거래소 ETF 시장 일별 대시보드 ·
          <strong> 운영자 관점</strong>(시장 건전성·운용사 시장구조)에 초점
        </p>
        <div className="header-meta">
          {data && (
            <>
              <span className="pill">기준일 {fmtDate(data.as_of)}</span>
              {data.mode === "demo" ? (
                <span className="pill warn">데모 데이터 · 인증키 없이 합성 분포</span>
              ) : (
                <span className="pill">실데이터 · 공공데이터포털</span>
              )}
              <span className="pill muted">
                investor view 가 아닌 surveillance / structure view
              </span>
            </>
          )}
        </div>
        <nav className="app-tabs" role="tablist">
          <button
            className={`app-tab ${tab === "health" ? "active" : ""}`}
            onClick={() => setTab("health")}
            role="tab"
            aria-selected={tab === "health"}
          >
            시장 건전성
          </button>
          <button
            className={`app-tab ${tab === "structure" ? "active" : ""}`}
            onClick={() => setTab("structure")}
            role="tab"
            aria-selected={tab === "structure"}
          >
            운용사 시장구조
          </button>
        </nav>
      </header>

      <main className="app-main">
        {error && (
          <div className="error">
            데이터 로드 실패: {error}
            <div style={{ fontSize: 12, marginTop: 6 }}>
              <code>web/public/data/latest.json</code> 이 존재하는지, 또는 빌드 시 정적 파일이
              포함됐는지 확인하세요. 로컬에서는 <code>cd pipeline &amp;&amp; python -m etf_monitor --demo</code>
              로 생성할 수 있습니다.
            </div>
          </div>
        )}

        {!data && !error && <div className="empty">데이터를 불러오는 중...</div>}

        {data && tab === "health" && <HealthPage data={data} />}
        {data && tab === "structure" && <StructurePage data={data} />}
      </main>

      {data && <ReliabilityFooter r={data.reliability} />}
    </div>
  );
}
