import type { PriceSnapshot } from "../types";
import { SITE_LABELS, SITE_COLORS } from "../types";

interface Props {
  snapshot: PriceSnapshot;
}

export function SummaryCard({ snapshot }: Props) {
  const label = SITE_LABELS[snapshot.site_name] ?? snapshot.site_name;
  const color = SITE_COLORS[snapshot.site_name] ?? "#6b7280";
  const date = new Date(snapshot.scraped_at);
  const timeStr = date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });

  return (
    <div
      className="rounded-xl border p-4 flex flex-col gap-2 min-w-[140px]"
      style={{ borderColor: color + "55", backgroundColor: color + "11" }}
    >
      <div className="flex items-center gap-2">
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{ backgroundColor: color }}
        />
        <span className="font-semibold text-sm truncate">{label}</span>
      </div>
      <div>
        <span className="text-3xl font-bold" style={{ color }}>
          {snapshot.best_discount_rate.toFixed(1)}
        </span>
        <span className="text-xs text-gray-400 ml-1">% 最高割引</span>
      </div>
      <div className="text-xs text-gray-400 space-y-0.5">
        <div>平均: {snapshot.avg_discount_rate.toFixed(1)}%</div>
        <div>出品数: {snapshot.listing_count.toLocaleString()}</div>
        <div>更新: {timeStr}</div>
      </div>
    </div>
  );
}
