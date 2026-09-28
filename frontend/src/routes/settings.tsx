import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAddStaff,
  useRemoveStaff,
  useRestaurant,
  useSession,
  useStaff,
  useUpdateRestaurant,
} from "@/lib/waitlist/hooks";
import type { Restaurant, StaffRole } from "@/lib/waitlist/types";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Restaurant settings — Hostline" },
      { name: "description", content: "Wait-time rules, arrival window, grace period, staff accounts and SMS sender." },
      { property: "og:title", content: "Restaurant settings — Hostline" },
      { property: "og:description", content: "Wait-time rules, arrival window, grace period and staff accounts." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const restaurant = useRestaurant();
  const update = useUpdateRestaurant();
  const session = useSession();
  const staff = useStaff();
  const addStaff = useAddStaff();
  const removeStaff = useRemoveStaff();

  const [form, setForm] = useState<Restaurant | null>(null);
  const [newStaff, setNewStaff] = useState({ name: "", email: "", role: "HOST" as StaffRole });

  useEffect(() => {
    if (restaurant.data) setForm(restaurant.data);
  }, [restaurant.data]);

  const isManager = session.data?.role === "MANAGER";

  if (!form) return <AppShell>Loading…</AppShell>;

  function field<K extends keyof Restaurant>(key: K, value: Restaurant[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function save() {
    if (!form) return;
    update.mutate(form, { onSuccess: () => toast.success("Settings saved") });
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl font-bold">Settings</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {isManager ? "Manager access — you can change everything here." : "Host access — settings are read-only."}
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="panel space-y-4 p-5">
          <h2 className="font-display text-lg font-bold">Restaurant</h2>
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={form.name} disabled={!isManager} onChange={(e) => field("name", e.target.value)} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="slug">Public page slug</Label>
              <Input id="slug" value={form.slug} disabled={!isManager} onChange={(e) => field("slug", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tz">Timezone</Label>
              <Input id="tz" value={form.timezone} disabled={!isManager} onChange={(e) => field("timezone", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cc">Phone country code</Label>
              <Input
                id="cc"
                value={form.phoneCountryCode}
                disabled={!isManager}
                onChange={(e) => field("phoneCountryCode", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sender">SMS sender name</Label>
              <Input
                id="sender"
                value={form.smsSenderName}
                disabled={!isManager}
                onChange={(e) => field("smsSenderName", e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-secondary/60 p-3">
            <div>
              <p className="text-sm font-medium">Remote waitlist</p>
              <p className="text-xs text-muted-foreground">Allow guests to join from the public page.</p>
            </div>
            <Switch
              checked={form.remoteJoinEnabled}
              disabled={!isManager}
              onCheckedChange={(v) => field("remoteJoinEnabled", v)}
            />
          </div>
        </section>

        <section className="panel space-y-4 p-5">
          <h2 className="font-display text-lg font-bold">Queue rules</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <NumberField
              label="Base wait per party (min)"
              value={form.baseWaitPerGroupMinutes}
              disabled={!isManager}
              onChange={(v) => field("baseWaitPerGroupMinutes", v)}
            />
            <NumberField
              label="Arrival window (min)"
              value={form.arrivalWindowMinutes}
              disabled={!isManager}
              onChange={(v) => field("arrivalWindowMinutes", v)}
            />
            <NumberField
              label="Grace period (min)"
              value={form.gracePeriodMinutes}
              disabled={!isManager}
              onChange={(v) => field("gracePeriodMinutes", v)}
            />
            <NumberField
              label="Max party size"
              value={form.maxPartySize}
              disabled={!isManager}
              onChange={(v) => field("maxPartySize", v)}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Estimate = parties ahead × base wait × party-size modifier (1–2: 1.0×, 3–4: 1.2×, 5–6: 1.5×, 7+: 2.0×).
            Hosts can always override a guest&apos;s displayed wait.
          </p>
          <Button onClick={save} disabled={!isManager || update.isPending}>
            {update.isPending ? "Saving…" : "Save settings"}
          </Button>
        </section>

        <section className="panel space-y-4 p-5 lg:col-span-2">
          <h2 className="font-display text-lg font-bold">Staff accounts</h2>
          <ul className="space-y-2">
            {(staff.data ?? []).map((s) => (
              <li key={s.id} className="flex items-center justify-between rounded-lg bg-secondary/60 px-3 py-2">
                <div>
                  <p className="text-sm font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {s.email} · {s.role.toLowerCase()}
                  </p>
                </div>
                {isManager && (
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label={`Remove ${s.name}`}
                    onClick={() => removeStaff.mutate(s.id)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                )}
              </li>
            ))}
          </ul>

          {isManager && (
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr_10rem_auto]">
              <Input
                placeholder="Name"
                value={newStaff.name}
                onChange={(e) => setNewStaff({ ...newStaff, name: e.target.value })}
              />
              <Input
                placeholder="Email"
                value={newStaff.email}
                onChange={(e) => setNewStaff({ ...newStaff, email: e.target.value })}
              />
              <Select
                value={newStaff.role}
                onValueChange={(v) => setNewStaff({ ...newStaff, role: v as StaffRole })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="HOST">Host</SelectItem>
                  <SelectItem value="MANAGER">Manager</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={() => {
                  if (!newStaff.name.trim() || !newStaff.email.includes("@")) {
                    toast.error("Enter a name and a valid email.");
                    return;
                  }
                  addStaff.mutate(newStaff, {
                    onSuccess: () => {
                      toast.success("Staff member added");
                      setNewStaff({ name: "", email: "", role: "HOST" });
                    },
                  });
                }}
              >
                Add staff
              </Button>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

function NumberField({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: number;
  disabled: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input
        type="number"
        min={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
