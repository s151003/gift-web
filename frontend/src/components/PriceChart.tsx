import ReactApexChart from "react-apexcharts";
import type { ApexOptions } from "apexcharts";
import type { PriceSnapshot, MetricKey } from "../types";
import { SITE_LABELS, SITE_COLORS } from "../types";

interface Props {
  snapshots: PriceSnapshot[];
  metric: MetricKey;
}

export function PriceChart({ snapshots, metric }: Props) {
  const sites = Array.from(new Set(snapshots.map((s) => s.site_name))).sort();

  const series = sites.map((site) => ({
    name: SITE_LABELS[site] ?? site,
    color: SITE_COLORS[site] ?? "#6b7280",
    data: snapshots
      .filter((s) => s.site_name === site)
      .map((s) => ({
        x: new Date(s.scraped_at).getTime(),
        y:
          metric === "listing_count"
            ? s.listing_count
            : parseFloat(s[metric].toFixed(2)),
      })),
  }));

  const isRate = metric !== "listing_count";

  const options: ApexOptions = {
    chart: {
      type: "line",
      zoom: { enabled: true, type: "x" },
      toolbar: { show: true },
      background: "transparent",
      foreColor: "#9ca3af",
      animations: { enabled: false },
    },
    stroke: { curve: "smooth", width: 2 },
    markers: { size: 0 },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeUTC: false,
        style: { colors: "#6b7280", fontSize: "11px" },
      },
    },
    yaxis: {
      labels: {
        formatter: (v) => (isRate ? `${v.toFixed(1)}%` : v.toLocaleString()),
        style: { colors: "#6b7280", fontSize: "11px" },
      },
      title: {
        text: isRate ? "割引率 (%)" : "出品数",
        style: { color: "#6b7280" },
      },
    },
    tooltip: {
      shared: true,
      intersect: false,
      x: { format: "MM/dd HH:mm" },
      y: {
        formatter: (v) => (isRate ? `${v?.toFixed(2)}%` : v?.toLocaleString() ?? "-"),
      },
    },
    legend: {
      position: "top",
      labels: { colors: "#d1d5db" },
    },
    grid: {
      borderColor: "#374151",
    },
    theme: { mode: "dark" },
  };

  if (snapshots.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        データがありません
      </div>
    );
  }

  return (
    <ReactApexChart
      type="line"
      series={series}
      options={options}
      height={320}
    />
  );
}
