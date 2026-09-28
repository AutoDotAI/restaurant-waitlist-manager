import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Plus, Radio } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { GuestDialog } from "@/components/guest-dialog";
import { QueueRow } from "@/components/queue-row";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useQueue,
  useReorderQueue,
  useRestaurant,
  useSetStatus,
  useSmsLog,
  useUpdateRestaurant,
} from "@/lib/waitlist/hooks";
import type { GuestStatus, WaitlistEntry } from "@/lib/waitlist/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Host dashboard — Hostline waitlist" },
      { name: "description", content: "The live queue: add walk-ins, reorder guests, notify and seat them." },
      { property: "og:title", content: "Host dashboard — Hostline waitlist" },
      { property: "og:description", content: "The live queue: add walk-ins, reorder guests, notify and seat them." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const restaurant = useRestaurant();
  const updateRestaurant = useUpdateRestaurant();
  const queue = useQueue();
  const reorder = useReorderQueue();
  const setStatus = useSetStatus();
  const sms = useSmsLog();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<WaitlistEntry | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [order, setOrder] = useState<WaitlistEntry[] | null>(null);

  const rows = order ?? queue.data ?? [];
  const covers = rows.reduce((sum, r) => sum + r.partySize, 0);

  function handleStatus(entry: WaitlistEntry, status: GuestStatus) {
    setStatus.mutate(
      { id: entry.id, status },
      {
        onSuccess: () => {
          setOrder(null);
          if (status === "NOTIFIED") toast.success(`SMS sent to ${entry.customerName}`);
          else toast.success(`${entry.customerName} → ${status.replace("_", " ").toLowerCase()}`);
        },
        onError: (e) => toast.error((e as Error).message),
      },
    );
  }

  function handleDragOver(targetId: string) {
    if (!dragId || dragId === targetId) return;
    const current = [...rows];
    const from = current.findIndex((r) => r.id === dragId);
    const to = current.findIndex((r) => r.id === targetId);
    if (from < 0 || to < 0) return;
    const [moved] = current.splice(from, 1);
    current.splice(to, 0, moved!);
    setOrder(current);
  }

  function handleDragEnd() {
    setDragId(null);
    if (order) reorder.mutate(order.map((r) => r.id), { onSuccess: () => setOrder(null) });
  }

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Tonight&apos;s queue</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {rows.length} {rows.length === 1 ? "party" : "parties"} waiting · {covers} covers
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="panel flex items-center gap-3 px-4 py-2.5">
            <Radio className="size-4 text-primary" />
            <div className="leading-tight">
              <p className="text-xs text-muted-foreground">Remote join</p>
              <p className="text-sm font-semibold">{restaurant.data?.remoteJoinEnabled ? "OPEN" : "CLOSED"}</p>
            </div>
            <Switch
              checked={restaurant.data?.remoteJoinEnabled ?? false}
              onCheckedChange={(checked) =>
                updateRestaurant.mutate(
                  { remoteJoinEnabled: checked },
                  { onSuccess: () => toast.success(`Remote joining ${checked ? "opened" : "closed"}`) },
                )
              }
              aria-label="Toggle remote joining"
            />
          </div>
          <Button
            size="lg"
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="size-4" /> Add guest
          </Button>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_20rem]">
        <section>
          {queue.isLoading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-20 w-full rounded-xl" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="panel grid place-items-center px-6 py-16 text-center">
              <p className="font-display text-lg font-bold">No one is waiting</p>
              <p className="mt-1 text-sm text-muted-foreground">Add a walk-in or open remote joining.</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {rows.map((entry, index) => (
                <QueueRow
                  key={entry.id}
                  entry={entry}
                  index={index}
                  gracePeriodMinutes={restaurant.data?.gracePeriodMinutes ?? 10}
                  dragging={dragId === entry.id}
                  onEdit={() => {
                    setEditing(entry);
                    setDialogOpen(true);
                  }}
                  onStatus={(status) => handleStatus(entry, status)}
                  onDragStart={() => setDragId(entry.id)}
                  onDragOver={() => handleDragOver(entry.id)}
                  onDragEnd={handleDragEnd}
                />
              ))}
            </ul>
          )}
        </section>

        <aside className="space-y-4">
          <div className="panel p-4">
            <h2 className="font-display text-sm font-bold uppercase tracking-wide text-muted-foreground">
              Public join page
            </h2>
            <p className="mt-2 break-all text-sm text-primary">/r/{restaurant.data?.slug ?? "…"}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Share this link or put it on a QR code at the door.
            </p>
          </div>

          <div className="panel p-4">
            <h2 className="font-display text-sm font-bold uppercase tracking-wide text-muted-foreground">
              Recent SMS
            </h2>
            <ul className="mt-3 space-y-3">
              {(sms.data ?? []).slice(0, 5).map((m) => (
                <li key={m.id} className="rounded-lg bg-secondary/60 p-3">
                  <p className="text-xs font-semibold text-primary">{m.messageType.replace(/_/g, " ").toLowerCase()}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{m.body}</p>
                </li>
              ))}
              {(sms.data ?? []).length === 0 && (
                <li className="text-xs text-muted-foreground">No messages sent yet this service.</li>
              )}
            </ul>
          </div>
        </aside>
      </div>

      <GuestDialog open={dialogOpen} onOpenChange={setDialogOpen} entry={editing} />
    </AppShell>
  );
}
