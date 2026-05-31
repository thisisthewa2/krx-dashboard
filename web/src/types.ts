export interface DashboardPayload {
  as_of: string;
  generated_at: string;
  mode: "demo" | "live";
  schema_version: string;
  kpis: Kpis;
  concentration: Concentration;
  issuer_share: IssuerShareRow[];
  issuer_rank: IssuerRankRow[];
  new_product_freq: NewProductFreq;
  alerts: AlertRow[];
  dormant: DormantRow[];
  concentration_trend: ConcentrationTrendPoint[];
  reliability: Reliability;
}

export interface Kpis {
  total_trade_value: number;
  active_count: number;
  total_count: number;
  dormant_count: number;
  new_listings_30d: number;
}

export interface Concentration {
  top4: number;
  top10: number;
  top50: number;
  gini: number;
  issuer_hhi: number;
  log_value_histogram: { bins: number[]; counts: number[] };
}

export interface IssuerShareRow {
  issuer: string;
  trade_value: number;
  trade_value_share: number;
  ticker_count: number;
  ticker_count_share: number;
}

export interface IssuerRankRow {
  issuer: string;
  rank_today: number;
  rank_prev: number | null;
  delta: number | null;
}

export interface NewProductFreq {
  months: string[];
  series: { issuer: string; data: number[] }[];
}

export interface AlertRow {
  ticker: string;
  name: string;
  issuer: string | null;
  z_volume: number;
  intraday_range_pct: number;
  trade_value: number;
  change_rate: number;
  reason: string;
}

export interface DormantRow {
  ticker: string;
  name: string | null;
  issuer: string | null;
  consecutive_no_trade_days: number;
  avg_volume_30d: number;
  days_since_last_seen: number;
  delisted_candidate: boolean;
}

export interface ConcentrationTrendPoint {
  date: string;
  top10_share: number;
  issuer_hhi: number;
  gini: number;
}

export interface Reliability {
  source: string;
  as_of_business_day: string;
  last_updated_kst: string;
  records_collected: number;
  missing: number;
  validation: string;
  demo_mode: boolean;
}
