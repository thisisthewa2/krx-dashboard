"""과거 일자 백필.

활용신청 직후 시계열 깊이가 부족해 휴면 판정·z-score·신규상장이 비어 보이는 문제를
해결하기 위해, 직전 N 영업일치 ETF/ETN 시세를 일괄 수집해 ``data/snapshots/`` 에 저장한다.

사용 예::

    python -m etf_monitor.backfill --days 60 --end 20260528 --rate-limit 0.2

* 30 tps 제한 + 매너 있는 호출 간격을 위해 기본 ``rate-limit`` 0.2 초 (= 5 req/s) 로 둔다.
* 이미 존재하는 스냅샷은 건너뛴다 (idempotent).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd

from . import config as cfg
from .client import PublicDataClient
from .collect import _normalize_price_row

logger = logging.getLogger(__name__)


def business_days(end: date, n: int) -> list[date]:
    out: list[date] = []
    cur = end
    while len(out) < n:
        if cur.weekday() < 5:
            out.append(cur)
        cur -= timedelta(days=1)
    return sorted(out)


def fetch_day(client: PublicDataClient, target: date) -> pd.DataFrame:
    """단일 일자의 ETF + ETN 시세를 정규화된 DataFrame 으로 반환."""
    target_str = target.strftime("%Y%m%d")
    rows: list[dict] = []
    for endpoint, ptype in (
        (cfg.ETF_PRICE_URL, "ETF"),
        (cfg.ETN_PRICE_URL, "ETN"),
    ):
        try:
            for raw in client.paginate(endpoint, {"basDt": target_str}):
                rows.append(_normalize_price_row(raw, product_type=ptype))
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s %s 호출 실패: %s", target_str, ptype, exc)
    return pd.DataFrame(rows)


def save_day(df: pd.DataFrame, target: date) -> bool:
    """스냅샷 저장. 행이 0이면 저장하지 않고 False."""
    if df.empty:
        return False
    target_str = target.strftime("%Y%m%d")
    cfg.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    (cfg.SNAPSHOTS_DIR / f"price_{target_str}.json").write_text(
        df.to_json(orient="records", force_ascii=False), encoding="utf-8"
    )
    listing = df[["date", "ticker", "name"]].drop_duplicates()
    (cfg.SNAPSHOTS_DIR / f"listing_{target_str}.json").write_text(
        listing.to_json(orient="records", force_ascii=False), encoding="utf-8"
    )
    return True


def run(
    *,
    end: date,
    days: int,
    rate_limit: float,
    skip_existing: bool = True,
) -> dict:
    key = os.environ.get("DATA_GO_KR_KEY")
    if not key:
        raise SystemExit("DATA_GO_KR_KEY 가 비어 있습니다.")
    client = PublicDataClient(key)

    saved = 0
    skipped = 0
    empty = 0
    targets: Iterable[date] = business_days(end, days)
    total = len(list(targets))
    targets = business_days(end, days)  # iter 재생성

    for i, d in enumerate(targets, start=1):
        target_str = d.strftime("%Y%m%d")
        out = cfg.SNAPSHOTS_DIR / f"price_{target_str}.json"
        if skip_existing and out.exists():
            skipped += 1
            continue
        df = fetch_day(client, d)
        if save_day(df, d):
            saved += 1
            logger.info("%s [%d/%d] saved %d rows", d.isoformat(), i, total, len(df))
        else:
            empty += 1
            logger.info("%s [%d/%d] empty (holiday?)", d.isoformat(), i, total)
        time.sleep(rate_limit)

    return {"saved": saved, "skipped": skipped, "empty": empty, "total": total}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="과거 일자 시세 백필")
    parser.add_argument("--days", type=int, default=60, help="백필할 영업일 수")
    parser.add_argument("--end", type=str, default=None, help="끝 일자 YYYYMMDD (기본: 오늘)")
    parser.add_argument("--rate-limit", type=float, default=0.2)
    parser.add_argument("--no-skip", action="store_true", help="기존 스냅샷도 덮어씀")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose >= 2 else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )

    end = (
        datetime.strptime(args.end, "%Y%m%d").date()
        if args.end
        else datetime.now().date()
    )
    summary = run(
        end=end,
        days=args.days,
        rate_limit=args.rate_limit,
        skip_existing=not args.no_skip,
    )
    print(f"backfill done: {summary}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
