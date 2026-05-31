"""핵심 지표 계산 단위 테스트.

복잡한 통계 라이브러리 의존성 없이 손으로 계산한 기댓값과 비교한다.
"""

from __future__ import annotations

import pandas as pd
import pytest

from etf_monitor import transform as T


class TestConcentrationMetrics:
    def test_hhi_monopoly_is_10000(self):
        assert T.hhi([100]) == pytest.approx(10000.0)

    def test_hhi_two_equal_is_5000(self):
        assert T.hhi([50, 50]) == pytest.approx(5000.0)

    def test_hhi_zero_total_returns_zero(self):
        assert T.hhi([0, 0, 0]) == 0.0

    def test_cr_n_returns_top_n_share(self):
        assert T.cr_n([1, 2, 3, 4], 1) == pytest.approx(0.4)
        assert T.cr_n([1, 2, 3, 4], 2) == pytest.approx(0.7)

    def test_gini_equal_distribution_is_zero(self):
        assert T.gini([10, 10, 10, 10]) == pytest.approx(0.0, abs=1e-6)

    def test_gini_concentrated_is_close_to_one(self):
        # 한 명이 다 가져갈수록 1에 가까워져야 한다
        g = T.gini([0, 0, 0, 100])
        assert g > 0.7


class TestZScore:
    def test_returns_zero_when_history_empty(self):
        today = pd.DataFrame({"ticker": ["A", "B"], "volume": [10, 20]})
        z = T.rolling_zscore(pd.DataFrame(columns=["ticker", "volume"]), today)
        # 빈 history 면 모두 NaN/0
        assert len(z) == 2

    def test_high_value_gets_positive_z(self):
        # A: 평소 ~5000 → 오늘 25000  (z 큼)
        # B: 평소 ~50000 → 오늘 50000 (z 작음)
        history = pd.DataFrame(
            {
                "ticker": ["A"] * 5 + ["B"] * 5,
                "volume": [5000, 5500, 4500, 5000, 5000, 50000, 55000, 45000, 50000, 50000],
            }
        )
        today = pd.DataFrame({"ticker": ["A", "B"], "volume": [25000, 50000]})
        z = T.rolling_zscore(history, today, min_mu=1000.0)
        # cap=10 이 걸려 정확히 폭발하진 않지만 양수 큰 값이어야 한다
        assert z["A"] >= 5
        assert abs(z["B"]) < 1

    def test_inactive_ticker_gets_zero_z(self):
        # 평균 거래량이 min_mu 미만이면 z=0 으로 처리되어 경보에서 빠진다
        history = pd.DataFrame(
            {"ticker": ["A"] * 5, "volume": [0, 0, 0, 0, 100]}
        )
        today = pd.DataFrame({"ticker": ["A"], "volume": [10000]})
        z = T.rolling_zscore(history, today, min_mu=1000.0)
        assert z["A"] == 0.0


class TestNewListings:
    def test_first_seen_per_ticker_groups_by_month(self):
        df = pd.DataFrame(
            [
                {"date": "2026-01-15", "ticker": "X", "issuer": "A"},
                {"date": "2026-01-20", "ticker": "X", "issuer": "A"},
                {"date": "2026-02-03", "ticker": "Y", "issuer": "A"},
                {"date": "2026-02-10", "ticker": "Z", "issuer": "B"},
            ]
        )
        out = T.new_listings_by_month(df)
        # X 는 2026-01 에 처음, Y 는 2026-02, Z 는 2026-02
        a_jan = out[(out["month"] == "2026-01") & (out["issuer"] == "A")]["count"].sum()
        a_feb = out[(out["month"] == "2026-02") & (out["issuer"] == "A")]["count"].sum()
        b_feb = out[(out["month"] == "2026-02") & (out["issuer"] == "B")]["count"].sum()
        assert a_jan == 1
        assert a_feb == 1
        assert b_feb == 1


class TestDormancy:
    def test_consecutive_no_trade_streak(self):
        history = pd.DataFrame(
            [
                {"ticker": "X", "date": "2026-05-29", "trade_value": 0},
                {"ticker": "X", "date": "2026-05-28", "trade_value": 0},
                {"ticker": "X", "date": "2026-05-27", "trade_value": 1000},
                {"ticker": "Y", "date": "2026-05-29", "trade_value": 5000},
            ]
        )
        history["date"] = pd.to_datetime(history["date"])
        s = T.consecutive_no_trade_days(history)
        assert int(s.loc["X"]) == 2
        assert int(s.loc["Y"]) == 0


class TestRankMovement:
    def test_delta_positive_means_rose(self):
        curr = pd.DataFrame({"issuer": ["A", "B", "C"], "trade_value": [100, 80, 60]})
        prev = pd.DataFrame({"issuer": ["A", "B", "C"], "trade_value": [60, 80, 100]})
        out = T.rank_movement(curr, prev)
        # A 는 prev 3등 → curr 1등 (delta +2)
        a_row = out[out["issuer"] == "A"].iloc[0]
        assert a_row["delta"] == 2
