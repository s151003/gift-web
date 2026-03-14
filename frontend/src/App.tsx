import useSWR from "swr";
import { useState } from "react";
import { fetchLatestSnapshots, fetchSnapshots, fetchTransactions, fetchHealth } from "./api";
import { SummaryCard } from "./components/SummaryCard";
import { PriceChart } from "./components/PriceChart";
import { TransactionsTable } from "./components/TransactionsTable";
import type { MetricKey, HourOption, CardType } from "./types";
import { CARD_TYPE_LABELS, CARD_TYPE_ICONS } from "./types";

const METRIC_OPTIONS: { value: MetricKey; label: string }[] = [
  { value: "best_discount_rate", label: "最高割引率" },
  { value: "avg_discount_rate", label: "平均割引率" },
  { value: "listing_count", label: "出品数" },
];

const HOUR_OPTIONS: { value: HourOption; label: string }[] = [
  { value: 6, label: "6h" },
  { value: 12, label: "12h" },
  { value: 24, label: "24h" },
  { value: 168, label: "7d" },
];

const CARD_TYPE_OPTIONS: CardType[] = ["amazon", "google_play", "apple"];

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-800 rounded ${className}`} />;
}

export default function App() {
  const [cardType, setCardType] = useState<CardType>("amazon");
  const [metric, setMetric] = useState<MetricKey>("best_discount_rate");
  const [hours, setHours] = useState<HourOption>(24);

  const { data: latestData, error: latestError } = useSWR(
    ["latest", cardType],
    () => fetchLatestSnapshots(cardType),
    { revalidateOnFocus: true }
  );
  const { data: snapshotsData, error: snapshotsError, mutate: refetchSnapshots } = useSWR(
    ["snapshots", hours, cardType],
    () => fetchSnapshots(hours, undefined, cardType),
    { refreshInterval: 300_000 }
  );
  const { data: txData } = useSWR(
    ["transactions", cardType],
    () => fetchTransactions(48, undefined, cardType),
    { refreshInterval: 300_000 }
  );
  const { data: health } = useSWR("health", fetchHealth, { refreshInterval: 300_000 });

  const latest = latestData?.data ?? [];
  const snapshots = snapshotsData?.data ?? [];
  const transactions = txData?.data ?? [];

  const lastUpdated = health?.latest_scraped_at
    ? new Date(health.latest_scraped_at).toLocaleString("ja-JP")
    : null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* ヘッダー */}
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🎁</span>
          <h1 className="font-bold text-lg">ギフト券相場チェッカー</h1>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-400">
          {lastUpdated && <span>最終更新: {lastUpdated}</span>}
          {health && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                health.stale
                  ? "bg-red-900/50 text-red-300"
                  : "bg-green-900/50 text-green-300"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${health.stale ? "bg-red-400" : "bg-green-400"}`}
              />
              {health.stale ? "データ古い" : "正常"}
            </span>
          )}
        </div>
      </header>

      {/* 券種タブ */}
      <div className="border-b border-gray-800 px-4">
        <div className="max-w-6xl mx-auto flex gap-1">
          {CARD_TYPE_OPTIONS.map((ct) => (
            <button
              key={ct}
              onClick={() => setCardType(ct)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                cardType === ct
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-400 hover:text-gray-200"
              }`}
            >
              <span className="mr-1.5">{CARD_TYPE_ICONS[ct]}</span>
              {CARD_TYPE_LABELS[ct]}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* サマリーカード */}
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            現在の最安値
          </h2>
          {latestError ? (
            <div className="text-red-400 text-sm">データを取得できませんでした</div>
          ) : !latestData ? (
            <div className="flex gap-3 flex-wrap">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-32 w-36" />
              ))}
            </div>
          ) : (
            <div className="flex gap-3 flex-wrap">
              {latest.length === 0 ? (
                <p className="text-gray-500 text-sm">まだデータがありません</p>
              ) : (
                latest.map((s) => <SummaryCard key={`${s.site_name}-${s.card_type}`} snapshot={s} />)
              )}
            </div>
          )}
        </section>

        {/* グラフ */}
        <section className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
            <h2 className="font-semibold">割引率推移</h2>
            <div className="flex items-center gap-4">
              {/* 表示切替 */}
              <div className="flex gap-1">
                {METRIC_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setMetric(opt.value)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      metric === opt.value
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {/* 期間 */}
              <div className="flex gap-1">
                {HOUR_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setHours(opt.value)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      hours === opt.value
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {snapshotsError ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <p className="text-red-400 text-sm">データを取得できませんでした</p>
              <button
                onClick={() => refetchSnapshots()}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm"
              >
                再試行
              </button>
            </div>
          ) : !snapshotsData ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <PriceChart snapshots={snapshots} metric={metric} />
          )}
        </section>

        {/* 取引履歴 */}
        <section className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <h2 className="font-semibold mb-4">取引履歴（直近48時間）</h2>
          {!txData ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <TransactionsTable transactions={transactions} />
          )}
        </section>
      </main>
    </div>
  );
}
