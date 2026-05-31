"""CLI 진입점.

사용 예::

    # 데모 모드 (인증키 불필요)
    python -m etf_monitor --demo

    # 실데이터 모드 (직전 영업일 자동 계산)
    DATA_GO_KR_KEY=... python -m etf_monitor

    # 특정 일자 강제
    DATA_GO_KR_KEY=... python -m etf_monitor --date 20260530
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

from . import config as cfg
from .client import PublicDataClient
from .collect import (
    build_payload,
    collect_demo,
    collect_live,
    previous_business_day,
    save_snapshot,
    write_payload,
)
from .issuer import IssuerMap


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KRX ETF 시장 모니터링 파이프라인")
    parser.add_argument("--demo", action="store_true", help="합성 데이터로 산출 (인증키 불필요)")
    parser.add_argument("--date", dest="target_date", help="기준일자 YYYYMMDD")
    parser.add_argument(
        "--out",
        dest="out_dir",
        default=str(cfg.WEB_PUBLIC_DATA_DIR),
        help="산출 디렉터리 (기본: web/public/data)",
    )
    parser.add_argument(
        "--issuer-map",
        dest="issuer_map_path",
        default=str(cfg.ISSUER_MAP_PATH),
        help="운용사 매핑 yaml 경로",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose >= 2 else (logging.INFO if args.verbose else logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )

    target = _resolve_target_date(args.target_date)
    imap = IssuerMap.load(Path(args.issuer_map_path))
    out_dir = Path(args.out_dir)

    if args.demo or not os.environ.get("DATA_GO_KR_KEY"):
        if not args.demo:
            logging.warning("DATA_GO_KR_KEY 가 비어 있어 demo 모드로 폴백합니다.")
        today_df, history, listing_history = collect_demo(target)
        mode = "demo"
    else:
        client = PublicDataClient(os.environ["DATA_GO_KR_KEY"])
        today_df, history, listing_history = collect_live(client, target)
        save_snapshot(
            today_df,
            listing_history[listing_history["date"] == target.isoformat()],
            target,
        )
        mode = "live"

    payload = build_payload(
        today=today_df,
        history=history,
        listing_history=listing_history,
        imap=imap,
        target_date=target,
        mode=mode,
        thresholds=cfg.Thresholds(),
    )
    out = write_payload(payload, out_dir=out_dir)
    print(f"wrote {out}  (mode={mode}, as_of={target.isoformat()})")
    return 0


def _resolve_target_date(spec: str | None) -> date:
    if not spec:
        return previous_business_day()
    return datetime.strptime(spec, "%Y%m%d").date()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
