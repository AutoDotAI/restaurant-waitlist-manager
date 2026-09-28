import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Clock, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePublicRestaurant, useJoinRemotely } from "@/lib/waitlist/hooks";

export const Route = createFileRoute("/r/$slug")({
  head: () => ({
    meta: [
      { title: "Join the waitlist" },
      { name: "description", content: "Join tonight's waitlist from your phone and get a text when your table is nearly ready." },
      { property: "og:title", content: "Join the waitlist" },
      { property: "og:description", content: "Join tonight's waitlist and get a text when your table is nearly ready." },
    ],
  }),
  component: JoinPage,
});

function JoinPage() {
  const { slug } = Route.useParams();
  const navigate = useNavigate();
  const info = usePublicRestaurant(slug);
  const join = useJoinRemotely(slug);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [party, setParty] = useState("2");

  if (info.isLoading) {
    return <CenteredMessage title="Loading…" body="Fetching the current wait." />;
  }
  if (info.isError || !info.data) {
    return <CenteredMessage title="Restaurant not found" body="Check the link and try again." />;
  }

  const [low, high] = info.data.estimatedWaitRange;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const size = Number(party);
    const max = info.data?.maxPartySize ?? 12;
    if (!name.trim()) {
      toast.error("Please enter your name.");
      return;
    }
    if (phone.replace(/\D/g, "").length < 6) {
      toast.error("Please enter a valid mobile number.");
      return;
    }
    if (!Number.isFinite(size) || size < 1 || size > max) {
      toast.error(`Party size must be between 1 and ${max}.`);
      return;
    }

    join.mutate(
      { customerName: name.trim(), phoneNumber: phone.trim(), partySize: size },
      {
        onSuccess: ({ token }) => navigate({ to: "/r/status/$token", params: { token } }),
        onError: (e) => toast.error((e as Error).message),
      },
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="panel w-full max-w-md p-7">
        <p className="text-xs uppercase tracking-widest text-primary">Waitlist</p>
        <h1 className="mt-2 font-display text-3xl font-bold">{info.data.name}</h1>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-secondary/60 p-4">
            <Clock className="size-4 text-primary" />
            <p className="mt-2 font-display text-xl font-bold">
              {low}–{high} min
            </p>
            <p className="text-xs text-muted-foreground">Estimated wait</p>
          </div>
          <div className="rounded-xl bg-secondary/60 p-4">
            <Users className="size-4 text-primary" />
            <p className="mt-2 font-display text-xl font-bold">{info.data.partiesWaiting}</p>
            <p className="text-xs text-muted-foreground">Parties waiting</p>
          </div>
        </div>

        {!info.data.remoteJoinEnabled ? (
          <div className="mt-6 rounded-xl border border-border bg-secondary/40 p-4 text-sm">
            <p className="font-semibold">Remote joining is closed right now.</p>
            <p className="mt-1 text-muted-foreground">Please come to the door and speak to a host.</p>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="c-name">Your name</Label>
              <Input id="c-name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="c-phone">Mobile number</Label>
              <Input
                id="c-phone"
                inputMode="tel"
                maxLength={24}
                placeholder="+33 6 12 34 56 78"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="c-party">Party size</Label>
              <Input
                id="c-party"
                type="number"
                min={1}
                max={info.data.maxPartySize}
                value={party}
                onChange={(e) => setParty(e.target.value)}
              />
            </div>
            <Button type="submit" className="w-full" size="lg" disabled={join.isPending}>
              {join.isPending ? "Joining…" : "Join the waitlist"}
            </Button>
            <p className="text-xs text-muted-foreground">
              We&apos;ll text you a link to track your wait. Please arrive within 30 minutes of joining.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}

function CenteredMessage({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 text-center">
      <div>
        <h1 className="font-display text-2xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      </div>
    </div>
  );
}
