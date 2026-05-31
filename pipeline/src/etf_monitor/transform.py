"""지표 계산.

운영자 관점의 시장 건전성·운용사 시장구조 지표를 산출한다.

* HHI : 운용사 단위 시장구조 집중도 (점유율 제곱합 × 10000)
* CR4 / TopN share : 거래대금 상위 N(종목/운용사) 비중
* Gini : 거래대금 분포의 불평등도
* z-score : 종목별 거래량 이상치
* 휴면 ETF : 거래대금 무거래 연속일 / 30일 평균 거래량 임계치 미만
* 신상품 출시 빈도 : 운용사별 월간 신규 상장 종목 수 (KRX상장종목정보 일별 diff 기반)
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------
# 집중도 / 불평등도
# --------------------------------------------------------------------------------------


def shares(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    total = arr.sum()
    if total <= 0:
        return np.zeros_like(arr)
    return arr / total


def hhi(values: Iterable[float]) -> float:
    """Herfindahl-Hirschman Index. 0 ~ 10000.

    분모가 0이면 0을 반환한다.
    """
    s = shares(values)
    return float(np.sum((s * 100.0) ** 2))


def cr_n(values: Iterable[float], n: int) -> float:
    """상위 N개 점유율. 0 ~ 1."""
    s = np.sort(shares(values))[::-1]
    return float(s[:n].sum())


def gini(values: Iterable[float]) -> float:
    """Gini 계수. 0(완전평등) ~ 1(완전불평등)."""
    arr = np.sort(np.asarray(list(values), dtype=float))
    n = arr.size
    if n == 0 or arr.sum() == 0:
        return 0.0
    cum = np.cumsum(arr)
    return float((n + 1 - 2 * cum.sum() / cum[-1]) / n)


# --------------------------------------------------------------------------------------
# 거래량 z-score (이상 신호)
# --------------------------------------------------------------------------------------


def rolling_zscore(
    history: pd.DataFrame,
    today: pd.DataFrame,
    *,
    key: str = "ticker",
    value: str = "volume",
    lookback: int = 30,
    min_mu: float = 1000.0,
    cap: float = 10.0,
) -> pd.Series:
    """종목별 거래량의 룩백 표본 평균/표준편차 대비 z-score.

    실제 시장감시 룰과 동일하게 *비활성 종목*은 z-score 산출에서 제외한다.

    Parameters
    ----------
    history : 룩백 기간의 일자×종목 데이터 (오늘 제외)
    today   : 당일 종목별 데이터
    min_mu  : 룩백 평균이 이 값 미만이면 z-score 0 (휴면·신규상장 종목 제외)
    cap     : z-score 절대값 상한
    """
    if history.empty:
        return pd.Series(0.0, index=today[key].values)
    stats = (
        history.groupby(key)[value]
        .agg(["mean", "std"])
        .rename(columns={"mean": "mu", "std": "sigma"})
    )
    merged = today.set_index(key).join(stats, how="left")
    sigma = merged["sigma"].replace(0, np.nan)
    z = (merged[value] - merged["mu"]) / sigma
    z = z.where(merged["mu"] >= min_mu, 0.0)
    z = z.clip(lower=-cap, upper=cap)
    return z.fillna(0.0)


# --------------------------------------------------------------------------------------
# 휴면 ETF
# --------------------------------------------------------------------------------------


def consecutive_no_trade_days(history: pd.DataFrame, *, key: str = "ticker") -> pd.Series:
    """종목별 거래대금 0원 연속일 수 (가장 최근 일자 기준).

    history 는 ``date`` 와 ``trade_value`` 컬럼을 포함해야 한다.
    """
    if history.empty:
        return pd.Series(dtype=int)

    h = history.sort_values([key, "date"], ascending=[True, False])

    def _streak(s: pd.Series) -> int:
        streak = 0
        for v in s:
            if v <= 0 or pd.isna(v):
                streak += 1
            else:
                break
        return streak

    return h.groupby(key)["trade_value"].apply(_streak).rename("consecutive_no_trade_days")


def avg_volume_window(
    history: pd.DataFrame, *, key: str = "ticker", window: int = 30
) -> pd.Series:
    """종목별 최근 window 일 거래량 평균."""
    if history.empty:
        return pd.Series(dtype=float)
    h = history.sort_values([key, "date"], ascending=[True, False])
    return h.groupby(key).head(window).groupby(key)["volume"].mean()


# --------------------------------------------------------------------------------------
# 신상품 출시 빈도 (KRX상장종목정보 일별 diff)
# --------------------------------------------------------------------------------------


def new_listings_by_month(listing_history: pd.DataFrame) -> pd.DataFrame:
    """운용사별 월간 신규 상장 종목 수.

    Parameters
    ----------
    listing_history : 컬럼 ``date``, ``ticker``, ``issuer`` 를 가지는 일별 종목 마스터.
        같은 ticker 가 처음 등장한 날짜를 신규 상장일로 간주한다.

    Returns
    -------
    DataFrame[month, issuer, count]
    """
    if listing_history.empty:
        return pd.DataFrame(columns=["month", "issuer", "count"])

    first_seen = (
        listing_history.sort_values("date").groupby("ticker", as_index=False).first()
    )
    first_seen["month"] = pd.to_datetime(first_seen["date"]).dt.strftime("%Y-%m")
    return (
        first_seen.groupby(["month", "issuer"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["month", "count"], ascending=[True, False])
    )


def diff_listings(prev: pd.DataFrame, curr: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """전일 대비 신규/소멸 종목 추출.

    Returns dict with keys ``new``, ``removed``.
    """
    prev_set = set(prev["ticker"]) if not prev.empty else set()
    curr_set = set(curr["ticker"]) if not curr.empty else set()
    new_tickers = curr_set - prev_set
    removed_tickers = prev_set - curr_set
    return {
        "new": curr[curr["ticker"].isin(new_tickers)].copy(),
        "removed": prev[prev["ticker"].isin(removed_tickers)].copy(),
    }


# --------------------------------------------------------------------------------------
# 운용사 점유율 / 순위
# --------------------------------------------------------------------------------------


def issuer_share(today: pd.DataFrame) -> pd.DataFrame:
    """운용사별 거래대금/종목수 점유율."""
    if today.empty:
        return pd.DataFrame(
            columns=["issuer", "trade_value", "trade_value_share", "ticker_count", "ticker_count_share"]
        )
    grp = today.groupby("issuer", dropna=True).agg(
        trade_value=("trade_value", "sum"),
        ticker_count=("ticker", "nunique"),
    )
    total_value = grp["trade_value"].sum()
    total_count = grp["ticker_count"].sum()
    grp["trade_value_share"] = grp["trade_value"] / total_value if total_value > 0 else 0.0
    grp["ticker_count_share"] = grp["ticker_count"] / total_count if total_count > 0 else 0.0
    return (
        grp.reset_index()
        .sort_values("trade_value", ascending=False)
        .reset_index(drop=True)
    )


def rank_movement(curr: pd.DataFrame, prev: pd.DataFrame) -> pd.DataFrame:
    """오늘 vs 직전 비교일의 운용사 순위 변동.

    delta = prev_rank - curr_rank (양수면 상승).
    """
    if curr.empty:
        return pd.DataFrame(columns=["issuer", "rank_today", "rank_prev", "delta"])

    curr = curr.copy()
    curr["rank_today"] = curr["trade_value"].rank(method="min", ascending=False).astype(int)

    if prev.empty:
        curr["rank_prev"] = pd.NA
        curr["delta"] = pd.NA
        return curr[["issuer", "rank_today", "rank_prev", "delta"]]

    prev = prev.copy()
    prev["rank_prev"] = prev["trade_value"].rank(method="min", ascending=False).astype(int)
    merged = curr.merge(prev[["issuer", "rank_prev"]], on="issuer", how="left")
    merged["delta"] = merged["rank_prev"] - merged["rank_today"]
    return merged[["issuer", "rank_today", "rank_prev", "delta"]]
