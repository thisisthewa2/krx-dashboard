"""파이프라인 본체.

* 데모 모드: 합성 데이터로 산출
* 실데이터 모드: 공공데이터포털 ETF 시세 + KRX상장종목정보 호출 후 산출

두 모드 모두 동일한 :class:`DashboardPayload` 형태를 만들며, 그 결과를
``web/public/data/latest.json`` 등 정적 JSON 으로 떨어뜨린다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dateutil import tz

from . import config as cfg
from . import transform as T
from .client import PublicDataClient
from .demo import (
    DemoSeed,
    generate_history,
    generate_listing_history,
    generate_master,
)
from .issuer import Issuer, IssuerMap

logger = logging.getLogger(__name__)

KST = tz.gettz("Asia/Seoul")


# --------------------------------------------------------------------------------------
# 페이로드 모델
# --------------------------------------------------------------------------------------


@dataclass
class DashboardPayload:
    as_of: str
    generated_at: str
    mode: str  # "demo" | "live"
    kpis: dict[str, Any]
    concentration: dict[str, Any]
    issuer_share: list[dict[str, Any]]
    issuer_rank: list[dict[str, Any]]
    new_product_freq: dict[str, Any]
    alerts: list[dict[str, Any]]
    dormant: list[dict[str, Any]]
    concentration_trend: list[dict[str, Any]]
    reliability: dict[str, Any]
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "generated_at": self.generated_at,
            "mode": self.mode,
            "schema_version": self.schema_version,
            "kpis": self.kpis,
            "concentration": self.concentration,
            "issuer_share": self.issuer_share,
            "issuer_rank": self.issuer_rank,
            "new_product_freq": self.new_product_freq,
            "alerts": self.alerts,
            "dormant": self.dormant,
            "concentration_trend": self.concentration_trend,
            "reliability": self.reliability,
        }


# --------------------------------------------------------------------------------------
# 운용사 매핑 적용
# --------------------------------------------------------------------------------------


UNMAPPED_LABEL = "(미매핑)"


def attach_issuer(df: pd.DataFrame, imap: IssuerMap) -> pd.DataFrame:
    """``brand`` 또는 ``name`` 으로부터 ``issuer`` 컬럼을 채운다.

    매핑 실패한 종목은 ``UNMAPPED_LABEL`` 로 통일해서 집계 단계에서 누락되지 않도록 한다.
    이렇게 하면 점유율 분모가 *전체 거래대금*으로 유지되고, 화면에서도 "(미매핑)" 그룹이
    얼마나 큰지 한눈에 보인다 — 그 자체가 운용사 매핑 yaml 보강이 얼마나 더 필요한지의
    피드백 루프가 된다.
    """
    if df.empty:
        df = df.copy()
        df["issuer"] = pd.Series(dtype="string")
        return df

    if "brand" in df.columns:
        out = df.copy()
        out["issuer"] = out["brand"].map(lambda b: _issuer_from_brand(b, imap))
        return out

    out = df.copy()
    out["brand"] = out["name"].map(_first_token)
    out["issuer"] = out["brand"].map(lambda b: _issuer_from_brand(b, imap))
    return out


def _issuer_from_brand(brand: str | None, imap: IssuerMap) -> str:
    if not brand:
        return UNMAPPED_LABEL
    info: Issuer | None = imap.resolve(brand)
    return info.issuer if info else UNMAPPED_LABEL


def _first_token(name: str) -> str:
    s = name or ""
    for sep in (" ", "_", "-"):
        s = s.replace(sep, " ")
    return s.strip().split(" ", 1)[0]


# --------------------------------------------------------------------------------------
# 페이로드 산출
# --------------------------------------------------------------------------------------


def build_payload(
    *,
    today: pd.DataFrame,            # 당일 (date, ticker, name, brand, close, high, low, volume, trade_value, ...)
    history: pd.DataFrame,          # 룩백 일자 (today 포함 가능)
    listing_history: pd.DataFrame,  # KRX 상장종목정보 일별 스냅샷
    imap: IssuerMap,
    target_date: date,
    mode: str,
    thresholds: cfg.Thresholds,
) -> DashboardPayload:
    today = attach_issuer(today, imap)
    history = attach_issuer(history, imap)
    listing_history = attach_issuer(listing_history, imap)

    # ----- KPIs --------------------------------------------------------------
    total_trade_value = float(today["trade_value"].sum()) if not today.empty else 0.0
    active_count = int((today["trade_value"] > 0).sum()) if not today.empty else 0
    total_count = int(today["ticker"].nunique()) if not today.empty else 0

    history_excl_today = history[history["date"] != target_date.isoformat()]
    no_trade_streak = T.consecutive_no_trade_days(
        history.assign(date=pd.to_datetime(history["date"]))
    )
    dormant_mask = no_trade_streak >= thresholds.dormant_consecutive_days
    dormant_count = int(dormant_mask.sum())

    new_listings_30d = _count_new_listings_recent(
        listing_history, end=target_date, days=thresholds.new_listing_window_days
    )

    # ----- 거래 쏠림 ----------------------------------------------------------
    sorted_today = today.sort_values("trade_value", ascending=False).reset_index(drop=True)
    top_n_share = {
        f"top{n}": T.cr_n(sorted_today["trade_value"], n) for n in thresholds.top_n_share
    }
    gini_value = T.gini(today["trade_value"]) if not today.empty else 0.0

    # 운용사 단위 HHI (운용사 시장구조 집중도)
    iss_today = T.issuer_share(today)
    issuer_hhi = T.hhi(iss_today["trade_value"]) if not iss_today.empty else 0.0

    # 거래대금 분포 히스토그램용 로그 분포
    log_dist = _log_value_histogram(today["trade_value"])

    # 직전 거래일 운용사 점유율 (순위 변동용)
    prev_date = _previous_business_date(history, target_date)
    prev_today = (
        history[history["date"] == prev_date.isoformat()] if prev_date else history.iloc[0:0]
    )
    prev_today = attach_issuer(prev_today, imap)
    iss_prev = T.issuer_share(prev_today)
    # 순위 변동에서는 (미매핑) 그룹 제외 — 운용사 서열 변동이 핵심이라 노이즈가 됨.
    iss_today_ranked = iss_today[iss_today["issuer"] != UNMAPPED_LABEL]
    iss_prev_ranked = iss_prev[iss_prev["issuer"] != UNMAPPED_LABEL]
    rank_df = T.rank_movement(iss_today_ranked, iss_prev_ranked)

    # ----- 신상품 출시 빈도 ---------------------------------------------------
    new_freq_df = T.new_listings_by_month(listing_history)
    new_freq = _shape_new_product_freq(new_freq_df, end=target_date, months=6)

    # ----- 이상 신호 (z-score & 일중 변동) ------------------------------------
    z = T.rolling_zscore(
        history_excl_today.rename(columns={"volume": "volume"}),
        today,
        key="ticker",
        value="volume",
        lookback=thresholds.rolling_lookback_days,
    )
    today_with_z = today.copy()
    today_with_z["z_volume"] = today_with_z["ticker"].map(z).fillna(0.0)
    today_with_z["intraday_range_pct"] = (
        (today_with_z["high"] - today_with_z["low"]) / today_with_z["close"].replace(0, pd.NA)
    ).fillna(0.0)

    alert_mask = (today_with_z["z_volume"] >= thresholds.zscore_volume_alert) | (
        today_with_z["intraday_range_pct"] >= thresholds.intraday_range_pct_alert
    )
    alerts_df = today_with_z[alert_mask].sort_values("z_volume", ascending=False).head(20)

    # ----- 휴면 ETF 리스트 ----------------------------------------------------
    avg_vol = T.avg_volume_window(
        history.assign(date=pd.to_datetime(history["date"])), window=30
    )
    # 종목명/운용사는 *history 의 가장 최근 등장* 기준으로 매핑한다.
    # today 기준으로만 join 하면 상장폐지된 ETN 처럼 today 에 빠진 종목이 ticker 만 표시된다.
    name_map = (
        history.assign(date=pd.to_datetime(history["date"]))
        .sort_values("date")
        .groupby("ticker", as_index=False)
        .last()[["ticker", "name", "issuer", "date"]]
        .rename(columns={"date": "last_seen_date"})
    )
    dormant_list = no_trade_streak[dormant_mask].reset_index()
    dormant_list = dormant_list.merge(name_map, on="ticker", how="left")
    dormant_list["avg_volume_30d"] = dormant_list["ticker"].map(avg_vol).fillna(0).astype(int)
    # 상장폐지 후보(=마지막 등장일이 기준일과 큰 격차) 와 단순 휴면을 구분
    target_ts = pd.Timestamp(target_date)
    dormant_list["days_since_last_seen"] = (
        (target_ts - dormant_list["last_seen_date"]).dt.days.fillna(0).astype(int)
    )
    dormant_list = dormant_list.sort_values(
        "consecutive_no_trade_days", ascending=False
    ).head(30)

    # ----- 집중도 추세 (최근 N일) --------------------------------------------
    trend = _build_concentration_trend(history, imap, days=20)

    # ----- 신뢰성 메타 --------------------------------------------------------
    reliability = build_reliability(
        mode=mode,
        as_of=target_date.isoformat(),
        records=total_count,
        missing=int(today[["close", "trade_value"]].isna().any(axis=1).sum()),
    )

    return DashboardPayload(
        as_of=target_date.isoformat(),
        generated_at=datetime.now(tz=KST).isoformat(timespec="seconds"),
        mode=mode,
        kpis={
            "total_trade_value": total_trade_value,
            "active_count": active_count,
            "total_count": total_count,
            "dormant_count": dormant_count,
            "new_listings_30d": new_listings_30d,
        },
        concentration={
            **top_n_share,
            "gini": round(gini_value, 4),
            "issuer_hhi": round(issuer_hhi, 1),
            "log_value_histogram": log_dist,
        },
        issuer_share=iss_today.to_dict(orient="records"),
        issuer_rank=rank_df.fillna({"rank_prev": 0, "delta": 0}).to_dict(orient="records"),
        new_product_freq=new_freq,
        alerts=[
            {
                "ticker": r["ticker"],
                "name": r["name"],
                "issuer": r.get("issuer"),
                "z_volume": round(float(r["z_volume"]), 2),
                "intraday_range_pct": round(float(r["intraday_range_pct"]), 4),
                "trade_value": float(r["trade_value"]),
                "change_rate": float(r.get("change_rate", 0.0)),
                "reason": _alert_reason(r["z_volume"], r["intraday_range_pct"], thresholds),
            }
            for _, r in alerts_df.iterrows()
        ],
        dormant=[
            {
                "ticker": r["ticker"],
                "name": r.get("name"),
                "issuer": r.get("issuer"),
                "consecutive_no_trade_days": int(r["consecutive_no_trade_days"]),
                "avg_volume_30d": int(r["avg_volume_30d"]),
                "days_since_last_seen": int(r.get("days_since_last_seen") or 0),
                "delisted_candidate": int(r.get("days_since_last_seen") or 0) >= 14,
            }
            for _, r in dormant_list.iterrows()
        ],
        concentration_trend=trend,
        reliability=reliability,
    )


def _alert_reason(z: float, range_pct: float, th: cfg.Thresholds) -> str:
    parts = []
    if z >= th.zscore_volume_alert:
        parts.append(f"거래량 z={z:.1f}")
    if range_pct >= th.intraday_range_pct_alert:
        parts.append(f"일중변동 {range_pct * 100:.1f}%")
    return " · ".join(parts) or "기준 충족"


def _previous_business_date(history: pd.DataFrame, target: date) -> date | None:
    if history.empty:
        return None
    dates = sorted({pd.Timestamp(d).date() for d in history["date"]})
    earlier = [d for d in dates if d < target]
    return earlier[-1] if earlier else None


def _count_new_listings_recent(
    listing_history: pd.DataFrame, *, end: date, days: int
) -> int:
    if listing_history.empty:
        return 0
    first_seen = (
        listing_history.assign(date=pd.to_datetime(listing_history["date"]))
        .sort_values("date")
        .groupby("ticker", as_index=False)
        .first()
    )
    cutoff = pd.Timestamp(end) - pd.Timedelta(days=days)
    return int((first_seen["date"] >= cutoff).sum())


def _shape_new_product_freq(df: pd.DataFrame, *, end: date, months: int) -> dict[str, Any]:
    """프론트가 그리기 좋은 형태로 변형: months 축 + issuer 별 시리즈.

    (미매핑) 그룹은 *어떤 운용사가 라인업을 늘리는가* 라는 질문 자체에 답을 못 하므로
    운용사 시장구조 화면에서는 제외한다.
    """
    if df.empty:
        return {"months": [], "series": []}

    end_period = pd.Timestamp(end).to_period("M")
    start_period = end_period - (months - 1)
    months_idx = pd.period_range(start_period, end_period, freq="M").strftime("%Y-%m").tolist()

    df = df.copy()
    df = df[df["month"].isin(months_idx) & (df["issuer"] != UNMAPPED_LABEL)]
    pivot = df.pivot_table(index="month", columns="issuer", values="count", fill_value=0)
    pivot = pivot.reindex(months_idx, fill_value=0)
    series = []
    for issuer in pivot.columns:
        total = int(pivot[issuer].sum())
        if total == 0:
            continue
        series.append({"issuer": issuer, "data": [int(v) for v in pivot[issuer].values]})
    series.sort(key=lambda s: sum(s["data"]), reverse=True)
    return {"months": months_idx, "series": series[:10]}


def _build_concentration_trend(
    history: pd.DataFrame, imap: IssuerMap, *, days: int
) -> list[dict[str, Any]]:
    if history.empty:
        return []
    df = attach_issuer(history, imap)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    last_dates = sorted(df["date"].unique())[-days:]
    out = []
    for d in last_dates:
        slice_ = df[df["date"] == d]
        iss = T.issuer_share(slice_)
        out.append(
            {
                "date": pd.Timestamp(d).date().isoformat(),
                "top10_share": round(T.cr_n(slice_["trade_value"], 10), 4),
                "issuer_hhi": round(T.hhi(iss["trade_value"]), 1),
                "gini": round(T.gini(slice_["trade_value"]), 4),
            }
        )
    return out


def _log_value_histogram(values: pd.Series, bins: int = 16) -> dict[str, Any]:
    import math

    arr = [v for v in values.tolist() if v and v > 0]
    if not arr:
        return {"bins": [], "counts": []}
    log_vals = [math.log10(v) for v in arr]
    lo, hi = min(log_vals), max(log_vals)
    if hi - lo < 1e-9:
        return {"bins": [round(lo, 2)], "counts": [len(log_vals)]}
    edges = [lo + (hi - lo) * i / bins for i in range(bins + 1)]
    counts = [0] * bins
    for v in log_vals:
        idx = min(int((v - lo) / (hi - lo) * bins), bins - 1)
        counts[idx] += 1
    return {
        "bins": [round((edges[i] + edges[i + 1]) / 2, 2) for i in range(bins)],
        "counts": counts,
    }


# --------------------------------------------------------------------------------------
# 데이터 신뢰성 메타
# --------------------------------------------------------------------------------------


def build_reliability(*, mode: str, as_of: str, records: int, missing: int) -> dict[str, Any]:
    if mode == "demo":
        source = "데모 합성 데이터 (실데이터 아님 — 종목명에 '합성-' 접미사)"
    else:
        source = (
            "공공데이터포털 금융위원회_증권상품시세정보 (15094806) "
            "+ 금융위원회_KRX상장종목정보 (15094775)"
        )
    return {
        "source": source,
        "as_of_business_day": as_of,
        "last_updated_kst": datetime.now(tz=KST).isoformat(timespec="seconds"),
        "records_collected": records,
        "missing": missing,
        "validation": "passed" if missing == 0 else "passed_with_warnings",
        "demo_mode": mode == "demo",
    }


# --------------------------------------------------------------------------------------
# 데이터 적재 — demo / live
# --------------------------------------------------------------------------------------


def collect_demo(target_date: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master = generate_master(DemoSeed())
    history = generate_history(master, end=target_date, days=60)
    listing = generate_listing_history(master, end=target_date, days=90)
    today_df = history[history["date"] == target_date.isoformat()].copy()
    return today_df, history, listing


def collect_live(
    client: PublicDataClient, target_date: date
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """공공데이터포털에서 당일 ETF·ETN 시세를 가져와 마스터/시세를 동시에 만든다.

    * ETF 시세 + ETN 시세 응답 자체가 그날 거래된 ETF/ETN 의 마스터이기도 하므로,
      별도 종목 마스터 호출 없이 ``listing_history`` 도 함께 만든다.
    * KRX상장종목정보(GetKrxListedInfoService) 는 ``mrktCtg`` (KOSPI/KOSDAQ) 와
      ``corpNm`` (법인명) 보강 용도로만 호출하며, **실패해도 대시보드 산출은 진행**한다.
    * 과거 일자는 ``data/snapshots/`` 에 누적된 파일에서 합친다.
    """
    target_str = target_date.strftime("%Y%m%d")

    # ----- ETF + ETN 시세 ----------------------------------------------------
    rows: list[dict[str, Any]] = []
    for endpoint, product_type in (
        (cfg.ETF_PRICE_URL, "ETF"),
        (cfg.ETN_PRICE_URL, "ETN"),
    ):
        try:
            for raw in client.paginate(endpoint, {"basDt": target_str}):
                rows.append(_normalize_price_row(raw, product_type=product_type))
            logger.info("price collected: %s (cumulative rows=%d)", product_type, len(rows))
        except Exception as exc:  # noqa: BLE001
            logger.warning("price endpoint %s failed: %s", endpoint, exc)
    today_df = pd.DataFrame(rows)

    if today_df.empty:
        logger.warning(
            "당일(%s) 시세 응답이 비어 있습니다. 영업일이 아니거나 갱신 전일 수 있습니다.",
            target_date.isoformat(),
        )

    # ----- KRX상장종목정보로 mrktCtg / corpNm 보강 (옵션) ---------------------
    listed_rows: list[dict[str, Any]] = []
    try:
        for raw in client.paginate(cfg.KRX_LISTED_INFO_URL, {"basDt": target_str}):
            listed_rows.append(_normalize_listed_row(raw))
        logger.info("listed info collected: %d rows", len(listed_rows))
    except Exception as exc:  # noqa: BLE001
        logger.warning("listed info endpoint failed (skipping enrichment): %s", exc)

    if listed_rows and not today_df.empty:
        listed_df = pd.DataFrame(listed_rows)
        # ticker 기준 left-join 으로 보강
        merged = today_df.merge(
            listed_df[["ticker", "market", "corp_name"]].drop_duplicates("ticker"),
            on="ticker",
            how="left",
            suffixes=("", "_listed"),
        )
        # 시세 응답에 'market' 이 None 이라 _listed 도 같이 생기지 않음 → 그대로 사용
        today_df = merged

    # ----- 시계열 마스터(=신상품 출시 빈도 산출용) ---------------------------
    listing_today = today_df.assign(
        date=today_df.get("date", pd.Series(dtype=str))
    )[["date", "ticker", "name"]].drop_duplicates() if not today_df.empty else pd.DataFrame(
        columns=["date", "ticker", "name"]
    )

    # ----- 과거 누적 합치기 --------------------------------------------------
    history = _load_history_from_snapshots()
    listing_history = _load_listing_from_snapshots()

    history = pd.concat([history, today_df], ignore_index=True).drop_duplicates(
        ["date", "ticker"]
    )
    listing_history = pd.concat([listing_history, listing_today], ignore_index=True).drop_duplicates(
        ["date", "ticker"]
    )

    return today_df, history, listing_history


def _normalize_price_row(raw: dict[str, Any], *, product_type: str) -> dict[str, Any]:
    """ETF/ETN 응답 한 건을 공통 키마로 정규화한다.

    ETF 의 ``nPptTotAmt`` 와 ETN 의 ``indcValTotAmt`` 처럼 키가 다른 항목은
    제품별 alternate 키를 모두 시도한다.
    """
    f = cfg.PRICE_FIELDS

    def pick(*keys: str) -> Any:
        for k in keys:
            v = raw.get(k)
            if v not in (None, ""):
                return v
        return None

    return {
        "date": _date_iso(raw.get(f["base_date"])),
        "ticker": str(raw.get(f["ticker"], "")).strip(),
        "isin": raw.get(f["isin"]),
        "name": raw.get(f["name"]),
        "product_type": product_type,
        "close": _to_float(raw.get(f["close"])),
        "open": _to_float(raw.get(f["open"])),
        "high": _to_float(raw.get(f["high"])),
        "low": _to_float(raw.get(f["low"])),
        "change": _to_float(raw.get(f["change"])),
        "change_rate": _to_float(raw.get(f["change_rate"])),
        "volume": _to_int(raw.get(f["volume"])),
        "trade_value": _to_float(raw.get(f["trade_value"])),
        "market_cap": _to_float(raw.get(f["market_cap"])),
        "nav": _to_float(pick(f["nav"], f["nav_etn"])),
        "nav_total": _to_float(pick(f["nav_total"], f["nav_total_etn"])),
        "listed_count": _to_int(pick(f["listed_count"], f["listed_count_alt"])),
        "underlying_index": raw.get(f["underlying_index"]),
        "underlying_close": _to_float(raw.get(f["underlying_close"])),
    }


def _normalize_listed_row(raw: dict[str, Any]) -> dict[str, Any]:
    f = cfg.LISTED_FIELDS
    return {
        "date": _date_iso(raw.get(f["base_date"])),
        "ticker": str(raw.get(f["ticker"], "")).strip(),
        "isin": raw.get(f["isin"]),
        "name": raw.get(f["name"]),
        "market": raw.get(f["market"]),
        "corp_no": raw.get(f["corp_no"]),
        "corp_name": raw.get(f["corp_name"]),
    }


def _date_iso(s: Any) -> str | None:
    if s is None:
        return None
    s = str(s)
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _to_int(v: Any) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None


def _load_history_from_snapshots() -> pd.DataFrame:
    out = []
    for p in sorted(cfg.SNAPSHOTS_DIR.glob("price_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.extend(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("snapshot %s skipped: %s", p, exc)
    return pd.DataFrame(out)


def _load_listing_from_snapshots() -> pd.DataFrame:
    out = []
    for p in sorted(cfg.SNAPSHOTS_DIR.glob("listing_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.extend(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("snapshot %s skipped: %s", p, exc)
    return pd.DataFrame(out)


def save_snapshot(today: pd.DataFrame, listing_today: pd.DataFrame, target_date: date) -> None:
    cfg.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    target_str = target_date.strftime("%Y%m%d")
    if not today.empty:
        (cfg.SNAPSHOTS_DIR / f"price_{target_str}.json").write_text(
            today.to_json(orient="records", force_ascii=False), encoding="utf-8"
        )
    if not listing_today.empty:
        (cfg.SNAPSHOTS_DIR / f"listing_{target_str}.json").write_text(
            listing_today.to_json(orient="records", force_ascii=False), encoding="utf-8"
        )


# --------------------------------------------------------------------------------------
# 산출
# --------------------------------------------------------------------------------------


def write_payload(payload: DashboardPayload, *, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    obj = _to_jsonable(payload.to_dict())
    target = out_dir / "latest.json"
    target.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    archive = out_dir / f"snapshot_{payload.as_of.replace('-', '')}.json"
    archive.write_text(
        json.dumps(obj, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    return target


def _to_jsonable(obj: Any) -> Any:
    """JSON 표준에 맞게 NaN/Inf/numpy 타입을 정규화한다.

    * float NaN/Inf → None
    * numpy 정수/실수 → 파이썬 기본형
    * pandas Timestamp → ISO 문자열
    * dict/list 재귀
    """
    import math

    import numpy as np

    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if obj is pd.NA:
        return None
    return obj


# --------------------------------------------------------------------------------------
# 영업일 계산
# --------------------------------------------------------------------------------------


def previous_business_day(today: date | None = None) -> date:
    """주말 제외한 직전 영업일. 공휴일은 무시(보수적 추정)."""
    base = today or datetime.now(tz=KST).date()
    cur = base - timedelta(days=1)
    while cur.weekday() >= 5:
        cur -= timedelta(days=1)
    return cur


def now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
