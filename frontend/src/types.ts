export interface PriceSnapshot {
  id: number;
  site_name: string;
  card_type: string;
  scraped_at: string;
  listing_count: number;
  best_discount_rate: number;
  worst_discount_rate: number;
  avg_discount_rate: number;
  median_discount_rate: number;
}

export interface Transaction {
  id: number;
  site_name: string;
  card_type: string;
  traded_at: string;
  face_value: number;
  traded_price: number;
  discount_rate: number;
  scraped_at: string;
}

export interface HealthResponse {
  status: string;
  latest_scraped_at: string | null;
  stale: boolean;
}

export type MetricKey = "best_discount_rate" | "avg_discount_rate" | "listing_count";
export type HourOption = 6 | 12 | 24 | 168;
export type CardType = "amazon" | "google_play" | "apple";

export const SITE_LABELS: Record<string, string> = {
  "ama-gift": "アマギフ",
  giftissue: "ギフトイシュー",
  beterugift: "べてるギフト",
  amaten: "アマテン",
};

export const SITE_COLORS: Record<string, string> = {
  "ama-gift": "#f97316",
  giftissue: "#3b82f6",
  beterugift: "#22c55e",
  amaten: "#a855f7",
};

export const CARD_TYPE_LABELS: Record<CardType, string> = {
  amazon: "Amazon",
  google_play: "Google Play",
  apple: "Apple",
};

export const CARD_TYPE_ICONS: Record<CardType, string> = {
  amazon: "📦",
  google_play: "🎮",
  apple: "🍎",
};
