import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalytics, useHistory } from "@/lib/waitlist/hooks";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "Service analytics — Hostline" },
      { name: "description", content: "Guests served, average waits, cancellations and walk-in vs remote mix." },
      { property: "og:title", content: "Service analytics — Hostline" },
      { property: "og:description", content: "Guests served, average waits, cancellations and walk-in vs remote mix." },
    ],
  }),
  component: AnalyticsPage,
});

const RANGES = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
] as const;

function AnalyticsPage() {
  const [range, setRange] = useState<"today" | "7d" | "30d">("today");
  const analytics = useAnalytics(range);
  const history = useHistory();

  const stats = analytics.data;
  const cards = [
    { label: "Guests served", value: stats?.guestsServed },
    { label: "Avg estimated wait", value: stats ? `${stats.averageEstimatedWait} min` : undefined },
    { label: "Avg actual wait", value: stats ? `${stats.averageActualWait} min` : undefined },
    { label: "Cancellations", value: stats?.cancellations },
    { label: "No-shows", value: stats?.noShows },
    { label: "Walk-ins", value: stats?.walkIns },
    { label: "Remote joins", value: stats?.remoteJoins },
    { label: "Avg party size", value: stats?.averagePartySize },
  ];

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Analytics</h1>
          <p className="mt-1 text-sm text-muted-foreground">Manager view of service performance.</p>
        </div>
        <Tabs value={range} onValueChange={(v) => setRange(v as typeof range)}>
          <TabsList>
            {RANGES.map((r) => (
              <TabsTrigger key={r.value} value={r.value}>
                {r.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="panel p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{c.label}</p>
            {c.value === undefined ? (
              <Skeleton className="mt-2 h-8 w-16" />
            ) : (
              <p className="mt-2 font-display text-3xl font-bold text-gradient-warm">{c.value}</p>
            )}
          </div>
        ))}
      </div>

      <section className="panel mt-6 p-5">
        <h2 className="font-display text-lg font-bold">Recent history</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2">Guest</th>
                <th className="py-2">Party</th>
                <th className="py-2">Source</th>
                <th className="py-2">Outcome</th>
                <th className="py-2">Joined</th>
              </tr>
            </thead>
            <tbody>
              {(history.data ?? []).map((e) => (
                <tr key={e.id} className="border-t border-border/60">
                  <td className="py-2 font-medium">{e.customerName}</td>
                  <td className="py-2">{e.partySize}</td>
                  <td className="py-2 text-muted-foreground">{e.source === "WALK_IN" ? "Walk-in" : "Remote"}</td>
                  <td className="py-2 capitalize">{e.status.replace("_", " ").toLowerCase()}</td>
                  <td className="py-2 text-muted-foreground">
                    {new Date(e.joinedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(history.data ?? []).length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">No completed guests yet.</p>
          )}
        </div>
      </section>
    </AppShell>
  );
}
