import type { Transaction } from "../types";
import { SITE_LABELS } from "../types";

interface Props {
  transactions: Transaction[];
}

export function TransactionsTable({ transactions }: Props) {
  if (transactions.length === 0) {
    return (
      <div className="text-center text-gray-500 text-sm py-8">
        取引履歴がありません
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-800">
            <th className="pb-2 pr-4">取引所</th>
            <th className="pb-2 pr-4">日時</th>
            <th className="pb-2 pr-4 text-right">額面</th>
            <th className="pb-2 pr-4 text-right">成立価格</th>
            <th className="pb-2 text-right">割引率</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => {
            const date = new Date(t.traded_at);
            const dateStr = date.toLocaleString("ja-JP", {
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
            });
            return (
              <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-2 pr-4 text-gray-300">
                  {SITE_LABELS[t.site_name] ?? t.site_name}
                </td>
                <td className="py-2 pr-4 text-gray-400 text-xs whitespace-nowrap">{dateStr}</td>
                <td className="py-2 pr-4 text-right text-gray-300">
                  ¥{t.face_value.toLocaleString()}
                </td>
                <td className="py-2 pr-4 text-right text-gray-300">
                  ¥{t.traded_price.toLocaleString()}
                </td>
                <td className="py-2 text-right font-semibold text-green-400">
                  {t.discount_rate.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
