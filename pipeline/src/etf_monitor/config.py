"""실행 설정 및 경로 상수.

엔드포인트와 응답 필드명은 공공데이터포털 활용신청 후 받게 되는
**명세서(Swagger/PDF)**를 기준으로 검증해야 한다.
값이 틀려도 ``--demo`` 모드는 영향을 받지 않는다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------------------
# 경로
# --------------------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
ISSUER_MAP_PATH = DATA_DIR / "issuer_map.yaml"
WEB_PUBLIC_DATA_DIR = REPO_ROOT / "web" / "public" / "data"

# --------------------------------------------------------------------------------------
# 공공데이터포털 엔드포인트 (활용신청 후 명세서로 최종 검증)
# --------------------------------------------------------------------------------------

# 금융위원회_증권상품시세정보 (data.go.kr/data/15094806)
#   - ETF/ETN/ELW 시세를 3개 오퍼레이션으로 제공
DATA_GO_KR_BASE = "https://apis.data.go.kr/1160100/service"

ETF_PRICE_URL = f"{DATA_GO_KR_BASE}/GetSecuritiesProductInfoService/getETFPriceInfo"
ETN_PRICE_URL = f"{DATA_GO_KR_BASE}/GetSecuritiesProductInfoService/getETNPriceInfo"

# 금융위원회_KRX상장종목정보 (data.go.kr/data/15094775)
KRX_LISTED_INFO_URL = f"{DATA_GO_KR_BASE}/GetKrxListedInfoService/getItemInfo"

# --------------------------------------------------------------------------------------
# 응답 필드 매핑 (명세서 확인 후 조정)
# --------------------------------------------------------------------------------------

# 공공데이터포털 시세 API 들이 공통적으로 사용하는 키 이름의 추정값.
# 명세서 확인 후 실제 키와 다르면 본 매핑 한 곳만 고치면 된다.
PRICE_FIELDS: dict[str, str] = {
    "base_date": "basDt",       # 기준일자 YYYYMMDD
    "ticker": "srtnCd",         # 단축코드
    "isin": "isinCd",           # ISIN
    "name": "itmsNm",           # 종목명
    "market": "mrktCtg",        # 시장구분 (ETF/ETN/ELW)
    "close": "clpr",            # 종가
    "open": "mkp",              # 시가
    "high": "hipr",             # 고가
    "low": "lopr",              # 저가
    "change": "vs",             # 전일대비
    "change_rate": "fltRt",     # 등락률(%)
    "volume": "trqu",           # 거래량
    "trade_value": "trPrc",     # 거래대금
    "market_cap": "mrktTotAmt", # 시가총액
    "nav_total": "nPstgTotAmt", # 순자산총액 (있으면)
}

LISTED_FIELDS: dict[str, str] = {
    "base_date": "basDt",
    "ticker": "srtnCd",
    "isin": "isinCd",
    "name": "itmsNm",
    "market": "mrktCtg",
    "corp_name": "corpNm",
}

# --------------------------------------------------------------------------------------
# 임계치 / 룩백 설정
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Thresholds:
    """주요 임계치. 한 곳에서 조정한다."""

    zscore_volume_alert: float = 3.0          # 거래량 z-score 경보 임계치
    intraday_range_pct_alert: float = 0.05    # 일중 변동폭(고가-저가)/종가 경보 임계치
    dormant_consecutive_days: int = 10        # 휴면 판정: 거래대금 0원 연속 일수
    dormant_avg_volume_30d: int = 0           # 휴면 판정 보조: 30일 평균 거래량 기준
    new_listing_window_days: int = 30         # "최근 N일 신규상장" 윈도우
    rolling_lookback_days: int = 30           # z-score / 평균 산출 룩백
    top_n_share: tuple[int, ...] = (4, 10, 50)  # CR4, top10, top50 등


@dataclass
class RuntimeConfig:
    """실행 시 주입되는 설정."""

    service_key: str | None = None
    target_date: str | None = None  # YYYYMMDD. None 이면 직전 영업일.
    demo: bool = False
    thresholds: Thresholds = field(default_factory=Thresholds)

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            service_key=os.environ.get("DATA_GO_KR_KEY"),
            target_date=os.environ.get("COLLECT_DATE"),
        )
