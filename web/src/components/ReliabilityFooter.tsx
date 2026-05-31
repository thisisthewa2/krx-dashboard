import type { Reliability } from "../types";
import { fmtCount, fmtDate, fmtDateTimeKST } from "../utils/format";

interface Props {
  r: Reliability;
}

export function ReliabilityFooter({ r }: Props) {
  return (
    <footer className="app-footer">
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "4px 18px",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 18px" }}>
          <span>
            <strong>출처</strong> · {r.source}
          </span>
          <span>
            <strong>기준일</strong> · {fmtDate(r.as_of_business_day)}
          </span>
          <span>
            <strong>최종 갱신</strong> · {fmtDateTimeKST(r.last_updated_kst)} (KST)
          </span>
          <span>
            <strong>수집 종목 수</strong> · {fmtCount(r.records_collected)}
          </span>
          <span>
            <strong>결측</strong> · {fmtCount(r.missing)}
          </span>
          <span>
            <strong>검증</strong> · {r.validation === "passed" ? "통과" : r.validation}
          </span>
        </div>
        <div style={{ color: "var(--c-text-subtle)" }}>schema v1.0.0</div>
      </div>
    </footer>
  );
}
