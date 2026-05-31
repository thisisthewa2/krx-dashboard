# KRX ETF Market Monitor

> 공공데이터로 만든 한국거래소 ETF 시장 일별 대시보드.
> **'어떤 ETF를 살까'가 아닌 '시장이 건강한가, 시장 구조가 어떻게 바뀌나'를 본다.**

## 왜 이 프로젝트인가

ETF 시장 트래커는 핀테크 블로그·증권사 앱에 이미 흔하다. 그런데 한국거래소가 실제로 보는 관점은 *투자자의 수익률*이 아니라 *시장의 건전성과 상품 생태계의 구조 변화*다. 본 프로젝트는 같은 ETF·ETN 데이터를 **시장 운영자(시장감시·상품기획) 관점**에서 재구성한 모니터링 도구다.

* **시장 건전성** — 거래 쏠림 (Top10 / CR4 / Gini), 휴면 ETF, 거래량 z-score 기반 이상 신호
* **운용사 시장구조** — 거래대금/종목수 점유율, HHI, 일별 순위 변동, **운용사별 신상품 출시 빈도**
* **데이터 신뢰성** — 출처·기준일·갱신 시각·결측·검증 결과가 매 화면 푸터에 명시

## 스크린샷

> *1차 배포 후 메인 화면 / 운용사 시장구조 화면 / 신상품 빈도 캡처 추가 예정.*

## 빠른 시작

### 1. 데이터 파이프라인 (Python)

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 인증키 없이도 실행 — 합성 데모 데이터로 산출
python -m etf_monitor --demo

# 실데이터 모드 (직전 영업일 자동 계산)
DATA_GO_KR_KEY=<공공데이터포털_일반인증키_decoding> python -m etf_monitor

# 특정 일자 강제
DATA_GO_KR_KEY=... python -m etf_monitor --date 20260530

# 지표 단위 테스트
pytest -q
```

### 2. 프론트엔드 (React + TS + Vite)

```bash
cd web
npm install
npm run dev          # http://localhost:5173
npm run build        # dist/
```

## 사용 데이터

활용신청은 모두 **공공데이터포털 (data.go.kr)**, 제공기관은 **금융위원회**.

| 데이터셋 | 페이지 | 용도 |
|---|---|---|
| 금융위원회_증권상품시세정보 | data.go.kr/data/15094806 | ETF·ETN 일별 시세 |
| 금융위원회_KRX상장종목정보 | data.go.kr/data/15094775 | 종목 마스터 / 신규상장 추적 / 운용사 매핑 |

> 공공데이터포털 거래소 데이터는 **영업일+1 오후 1시 이후 갱신**되는 비실시간 EOD 데이터이며, 이 프로젝트의 일배치도 KST 14:30 으로 안전마진을 두고 동작한다.

## 지표 정의

| 지표 | 정의 | 적용 위치 |
|---|---|---|
| **Top N share** | 상위 N종목 거래대금 점유율 (CR4·Top10·Top50) | 시장 건전성 화면 — 종목 단위 거래 쏠림 |
| **Gini 계수** | 거래대금 분포의 불평등도 (0=평등, 1=완전집중) | 시장 건전성 화면 |
| **운용사 HHI** | Σ (운용사별 거래대금 점유율 × 100)² . 0~10000 | 운용사 시장구조 화면 — 시장구조 집중도 |
| **거래량 z-score** | (오늘 거래량 − 룩백 30일 평균) / σ . 휴면·신규상장 종목은 룩백 표본 부족으로 의도적 제외, 절대값 10 cap | 이상 신호 |
| **일중 변동폭** | (고가 − 저가) / 종가 | 이상 신호 (>=5% 경보) |
| **휴면 ETF** | 거래대금 0원이 10영업일 이상 연속 | 휴면 종목 리스트 |
| **신상품 출시 빈도** | 월별 신규 등장 ticker 수 (KRX상장종목정보 일별 diff) × 운용사 | 운용사 시장구조 화면 |
| **순위 변동(Δ)** | 직전 영업일 대비 거래대금 기준 운용사 순위 변동 | 운용사 시장구조 화면 |

운용사 매핑은 [`data/issuer_map.yaml`](./data/issuer_map.yaml) 한 곳에서 관리하며, **리브랜딩 이력(KBSTAR→RISE, KINDEX→ACE, ARIRANG→PLUS, 2024~2025)** 도 alias로 보존하여 시계열 점유율이 끊기지 않도록 했다.

## 데이터 흐름

```
                     ┌──────────────────────────┐
                     │ data.go.kr (금융위)       │
                     │  · 증권상품시세정보(ETF/ETN) │
                     │  · KRX상장종목정보         │
                     └─────────────┬────────────┘
                                   │  GET (HTTPS, 일배치)
                                   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  pipeline/  (Python)                                            │
   │   client.py    페이지네이션·재시도                                  │
   │   collect.py   demo / live 두 모드 동일 키마                        │
   │   transform.py HHI · CR4 · Gini · z-score · 신상품 빈도              │
   │   issuer.py    yaml 매핑 (리브랜딩 보존)                             │
   └─────────────┬───────────────────────────────────────┬───────────┘
                 │ data/snapshots/{price,listing}_*.json │ web/public/data/latest.json
                 ▼ (일별 누적, 시계열·diff 용)             ▼ (정적 페이로드)
                                                  ┌────────────────┐
                                                  │  web/  (React) │
                                                  │  · Health      │
                                                  │  · Structure   │
                                                  └─────────┬──────┘
                                                            │  vite build
                                                            ▼
                                                    GitHub Pages
```

## 자동 운영

* `.github/workflows/daily-collect.yml` — 평일 KST 14:30 자동 수집 → JSON commit → push
* `.github/workflows/deploy-pages.yml` — 코드 또는 데이터 변경 시 자동 빌드 & GitHub Pages 배포

> Repo Settings → Pages → **Source: GitHub Actions** 로 설정하고, Repo Secrets 에 `DATA_GO_KR_KEY` (공공데이터포털 일반 인증키 Decoding) 를 추가해야 한다. Secret 이 비어 있으면 워크플로우는 자동으로 demo 모드로 폴백된다.

## 알려진 한계 & 개선 계획

| 한계 | 영향 | 개선 방향 |
|---|---|---|
| 공공데이터에 호가·LP·상장좌수 데이터 없음 | LP 품질·시장조성 깊이 분석 불가 | KRX OpenAPI(https://openapi.krx.co.kr) 활용신청 후 보강 |
| 응답 필드명(NAV/순자산총액 포함 여부)이 명세서에서 최종 확정됨 | NAV·괴리율 분석은 명세서 확인 후 추가 | `pipeline/src/etf_monitor/config.py` 의 `PRICE_FIELDS` 에서 한 곳만 조정 |
| 운용사 prefix 파싱은 새 브랜드 등장 시 깨질 수 있음 | 시장 구조 분석에 일시 영향 | `data/issuer_map.yaml` 단일 파일 갱신으로 대응 (리브랜딩 이력 보존) |
| EOD 일배치 (실시간 아님) | 장중 모니터링 불가 | KRX 실시간 시세 도입 시 호가/체결 스트림 단계적 확장 가능 |
| 시계열 깊이는 배포 이후부터 누적 | 추세 차트는 N일 누적 후 의미 | 초기 백필을 위해 data.krx.co.kr 수동 다운로드 자료 활용 가능 |

## 향후 검토 (1차 배포 후 결정)

* **ETF 시장 건전성 종합 스코어카드** — Top10 / 휴면 비율 / 운용사 HHI / 신규·소멸 비율을 가중평균한 0~100 단일 지수
* **이벤트 스터디 케이스 1건 박제** — 실제 시장 이벤트(예: MSCI 편출입, 빅테크 급락) 시점에 본 도구가 어떤 신호를 냈는지 캡처

## 폴더 구조

```
.
├── data/
│   ├── issuer_map.yaml         # 운용사 매핑 (리브랜딩 이력 보존)
│   └── snapshots/              # 일별 수집 원본 (price_YYYYMMDD.json)
├── pipeline/                   # Python 수집·집계 엔진
│   ├── pyproject.toml
│   ├── src/etf_monitor/
│   │   ├── __main__.py · CLI
│   │   ├── config.py · 엔드포인트·필드 매핑·임계치
│   │   ├── client.py · 공공데이터 HTTP 클라이언트
│   │   ├── issuer.py · 운용사 매핑 적용
│   │   ├── transform.py · 지표 산출
│   │   ├── collect.py · 모드별 적재 + payload 빌드
│   │   └── demo.py · 합성 데이터 생성
│   └── tests/
├── web/                        # Vite + React + TypeScript + Recharts
│   ├── src/{pages,components,utils}/
│   └── public/data/latest.json # 파이프라인이 산출한 정적 페이로드
└── .github/workflows/
    ├── daily-collect.yml       # 평일 KST 14:30 자동 수집
    └── deploy-pages.yml        # 자동 배포
```

## 라이선스

코드는 MIT. 데이터는 공공데이터포털·KRX 의 각 이용 약관을 따른다.
