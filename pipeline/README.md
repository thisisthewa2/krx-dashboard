# pipeline — 데이터 수집 · 지표 산출

Python 파이프라인. **공공데이터포털(data.go.kr) 의 금융위원회 데이터셋**을 호출해
ETF·ETN 시장의 건전성·운용사 시장구조 지표를 산출하고
프론트(`web/`)가 읽을 정적 JSON 을 만든다.

## 사용 데이터셋

| 데이터셋 | 페이지 | 용도 |
|---|---|---|
| 금융위원회_증권상품시세정보 | data.go.kr/data/15094806 | ETF·ETN 일별 시세 |
| 금융위원회_KRX상장종목정보 | data.go.kr/data/15094775 | 종목 마스터 / 신규상장 추적 / 운용사 매핑 |

## 설치

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 실행

```bash
python -m etf_monitor --demo                       # 인증키 없이 데모
DATA_GO_KR_KEY=xxx python -m etf_monitor           # 직전 영업일 실데이터
DATA_GO_KR_KEY=xxx python -m etf_monitor --date 20260530
```

산출물은 기본적으로 `web/public/data/latest.json` 으로 떨어진다. 프론트가
빌드 시 그대로 호스팅한다.

## 구조

```
src/etf_monitor/
├── __main__.py        CLI
├── config.py          엔드포인트·필드 매핑·임계치
├── client.py          공공데이터포털 HTTP 클라이언트 (페이지네이션·재시도)
├── issuer.py          종목명 prefix → 운용사 매핑 (data/issuer_map.yaml)
├── transform.py       HHI · CR4 · Gini · z-score · 신상품 빈도 등
├── collect.py         demo / live 수집 + payload 빌드 + 산출
└── demo.py            합성 데이터 생성기
tests/
└── test_transform.py
```

## 명세서 확인 후 조정 지점

활용신청 후 명세서(Swagger/PDF)를 받으면 두 곳만 검증·조정하면 된다.

1. `config.ETF_PRICE_URL`, `config.ETN_PRICE_URL`, `config.KRX_LISTED_INFO_URL`
2. `config.PRICE_FIELDS`, `config.LISTED_FIELDS` (응답 키 이름 매핑)

`--demo` 모드는 위 매핑 변경에 영향을 받지 않는다.
