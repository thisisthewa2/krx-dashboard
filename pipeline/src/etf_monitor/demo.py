"""데모 데이터 생성기.

인증키가 없을 때도 대시보드를 그대로 구동할 수 있도록 합성 데이터를 만든다.
실데이터 흐름과 키마(컬럼·타입)가 동일하므로, 실데이터 모드와 산출 코드 경로가 같다.

** 실제 종목 이름과의 혼동을 피하기 위해 모든 종목명에 ``합성-NNN`` 접미사를 붙인다. **
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

# 운용사별 *종목수* 분포 (실제 시장과 유사하게)
_BRAND_TICKER_WEIGHTS: list[tuple[str, float]] = [
    ("KODEX", 0.20),
    ("TIGER", 0.19),
    ("ACE", 0.12),
    ("RISE", 0.10),
    ("PLUS", 0.08),
    ("SOL", 0.07),
    ("HANARO", 0.05),
    ("KOSEF", 0.05),
    ("히어로즈", 0.04),
    ("TIMEFOLIO", 0.03),
    ("WOORI", 0.02),
    ("BNK", 0.015),
    ("WON", 0.015),
    ("KCGI", 0.01),
    ("TRUSTON", 0.01),
]

# 운용사별 *종목당 평균 거래대금 배율* — 실제 시장에서 KODEX/TIGER 종목이
# 평균적으로 더 큰 거래대금을 갖는 사실을 반영한다 (대표 인덱스/레버리지 보유 등).
_BRAND_VALUE_BIAS: dict[str, float] = {
    "KODEX": 3.0,
    "TIGER": 2.6,
    "ACE": 1.0,
    "RISE": 0.7,
    "PLUS": 0.5,
    "SOL": 0.5,
    "HANARO": 0.4,
    "KOSEF": 0.3,
    "히어로즈": 0.3,
    "TIMEFOLIO": 0.4,
    "WOORI": 0.2,
    "BNK": 0.15,
    "WON": 0.15,
    "KCGI": 0.15,
    "TRUSTON": 0.15,
}

_TOTAL_TICKERS = 1058  # 2025년 말 KRX 발표 ETF 종목 수와 동일 규모


@dataclass(frozen=True)
class DemoSeed:
    n_tickers: int = _TOTAL_TICKERS
    seed: int = 20260530


def _assign_brands(n: int, rng: random.Random) -> list[str]:
    brands, weights = zip(*_BRAND_TICKER_WEIGHTS, strict=True)
    return rng.choices(brands, weights=weights, k=n)


def generate_master(seed: DemoSeed = DemoSeed()) -> pd.DataFrame:
    """종목 마스터 (ticker, isin, name, market, brand)."""
    rng = random.Random(seed.seed)
    brands = _assign_brands(seed.n_tickers, rng)
    rows = []
    for i in range(seed.n_tickers):
        brand = brands[i]
        ticker = f"9{str(i).zfill(5)}"  # 가짜 단축코드 (실 종목과 충돌 회피)
        rows.append(
            {
                "ticker": ticker,
                "isin": f"KR9{ticker}0007",
                "name": f"{brand} 합성-{i:03d}",
                "market": "KOSPI" if rng.random() < 0.97 else "KOSDAQ",
                "brand": brand,
            }
        )
    return pd.DataFrame(rows)


def generate_history(
    master: pd.DataFrame, *, end: date, days: int = 60, seed: int = 20260530
) -> pd.DataFrame:
    """과거 ``days`` 영업일치 시세 (date, ticker, ... ).

    - 거래대금 분포: log-normal × Pareto-tail (대형 종목 쏠림 모사)
    - 약 12% 종목은 휴면 (장기간 거래대금 0)
    - 일자별 일중 변동성과 등락률을 합리적 범위에서 흔든다
    """
    rng = random.Random(seed)
    n = len(master)

    # 종목별 *기본 거래대금 스케일* (Pareto)
    base_scale = []
    for _ in range(n):
        u = rng.random()
        # alpha=1.4 의 두꺼운 꼬리. 상위 1~2% 가 매우 큼
        x = (1.0 - u) ** (-1.0 / 1.4)
        base_scale.append(x)

    # 약 12% 종목은 휴면 (스케일을 0 근처로)
    dormant_idx = set(rng.sample(range(n), k=int(n * 0.12)))

    # 영업일 시뮬: end 부터 거꾸로, 주말 제외
    dates: list[date] = []
    cursor = end
    while len(dates) < days:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor -= timedelta(days=1)
    dates = sorted(dates)

    rows = []
    tickers = master["ticker"].tolist()
    for d in dates:
        day_factor = rng.uniform(0.7, 1.3)
        for i, ticker in enumerate(tickers):
            if i in dormant_idx:
                trade_value = 0.0
                volume = 0
                if rng.random() < 0.05:  # 가끔 거래
                    volume = rng.randint(10, 500)
                    trade_value = volume * rng.uniform(8000, 12000)
                close = rng.uniform(8000, 12000)
                hi = close * 1.001
                lo = close * 0.999
            else:
                brand = master.iloc[i]["brand"]
                bias = _BRAND_VALUE_BIAS.get(brand, 0.5)
                # 거래대금 (원 단위) — Pareto 꼬리 × 운용사 거래대금 배율 × 일자 변동
                trade_value = base_scale[i] * bias * 3e8 * day_factor * rng.uniform(0.6, 1.4)
                close = rng.uniform(7_000, 80_000)
                # 일중 변동폭 (대부분 0~3%, 가끔 5% 이상)
                rng_range = rng.choices(
                    [rng.uniform(0.001, 0.015), rng.uniform(0.015, 0.05), rng.uniform(0.05, 0.10)],
                    weights=[0.85, 0.13, 0.02],
                )[0]
                hi = close * (1 + rng_range / 2)
                lo = close * (1 - rng_range / 2)
                volume = int(trade_value / max(close, 1.0))

            change_rate = rng.gauss(0.0, 0.012)
            rows.append(
                {
                    "date": d.isoformat(),
                    "ticker": ticker,
                    "name": master.iloc[i]["name"],
                    "brand": master.iloc[i]["brand"],
                    "market": master.iloc[i]["market"],
                    "close": round(close, 2),
                    "open": round(close * (1 - change_rate / 2), 2),
                    "high": round(hi, 2),
                    "low": round(lo, 2),
                    "volume": volume,
                    "trade_value": round(trade_value, 2),
                    "change_rate": round(change_rate * 100, 3),
                }
            )

    return pd.DataFrame(rows)


def generate_listing_history(master: pd.DataFrame, *, end: date, days: int = 90, seed: int = 20260530) -> pd.DataFrame:
    """KRX상장종목정보 일별 스냅샷 (date, ticker, name, brand).

    종목 일부는 윈도우 후반부에야 등장하도록 해서 신규상장을 모사한다.
    """
    rng = random.Random(seed + 1)
    n = len(master)
    # 약 5% 종목은 최근 윈도우 안에 신규 상장
    new_count = int(n * 0.05)
    new_idx = set(rng.sample(range(n), k=new_count))
    listing_start: dict[str, int] = {}
    for i in range(n):
        if i in new_idx:
            listing_start[master.iloc[i]["ticker"]] = rng.randint(0, days - 1)
        else:
            listing_start[master.iloc[i]["ticker"]] = -1  # 항상 상장

    dates: list[date] = []
    cursor = end
    while len(dates) < days:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor -= timedelta(days=1)
    dates = sorted(dates)

    rows = []
    for offset, d in enumerate(dates):
        for i, ticker in enumerate(master["ticker"].tolist()):
            start_offset = listing_start[ticker]
            if start_offset >= 0 and offset < (days - start_offset):
                continue
            rows.append(
                {
                    "date": d.isoformat(),
                    "ticker": ticker,
                    "name": master.iloc[i]["name"],
                    "brand": master.iloc[i]["brand"],
                }
            )
    return pd.DataFrame(rows)
