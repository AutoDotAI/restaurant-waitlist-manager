import { createFileRoute } from "@tanstack/react-router";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { usePublicStatus, useCustomerAction } from "@/lib/waitlist/hooks";

export const Route = createFileRoute("/r/status/$token")({
  head: () => ({
    meta: [
      { title: "Your waitlist status" },
      { name: "description", content: "Track your estimated wait, confirm you're coming, or cancel your place." },
      { property: "og:title", content: "Your waitlist status" },
      { property: "og:description", content: "Track your estimated wait, confirm you're coming, or cancel your place." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: StatusPage,
});

function StatusPage() {
  const { token } = Route.useParams();
  const status = usePublicStatus(token);
  const action = useCustomerAction(token);

  if (status.isLoading) {
    return <Centered title="Loading…" body="Checking your place in the queue." />;
  }
  if (status.isError || !status.data) {
    return <Centered title="Link no longer valid" body="Please speak to a host at the restaurant." />;
  }

  const s = status.data;
  const terminal = ["SEATED", "CANCELLED", "NO_SHOW", "REMOVED"].includes(s.status);

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="panel w-full max-w-md p-7 text-center">
        <p className="text-xs uppercase tracking-widest text-primary">{s.restaurantName}</p>

        {s.status === "SEATED" ? (
          <h1 className="mt-3 font-display text-3xl font-bold">Enjoy your meal, {s.customerName}</h1>
        ) : s.status === "CANCELLED" ? (
          <h1 className="mt-3 font-display text-3xl font-bold">Your place was cancelled</h1>
        ) : terminal ? (
          <h1 className="mt-3 font-display text-3xl font-bold">You&apos;re no longer on the waitlist</h1>
        ) : (
          <h1 className="mt-3 font-display text-3xl font-bold">You&apos;re on the waitlist</h1>
        )}

        {!terminal && (
          <>
            <div className="mt-6 rounded-xl bg-secondary/60 p-5">
              <p className="text-sm text-muted-foreground">Party of {s.partySize}</p>
              <p className="mt-1 font-display text-4xl font-bold text-gradient-warm">~{s.estimatedWaitMinutes} min</p>
              <p className="mt-1 text-xs text-muted-foreground">Estimated wait</p>
            </div>

            {s.status === "NOTIFIED" ? (
              <div className="mt-6 space-y-3">
                <p className="text-sm">
                  Your table is nearly ready. Please confirm within {s.gracePeriodMinutes} minutes.
                </p>
                <div className="flex gap-3">
                  <Button
                    className="flex-1"
                    disabled={action.isPending}
                    onClick={() =>
                      action.mutate("confirm", { onSuccess: () => toast.success("Thanks — see you shortly!") })
                    }
                  >
                    I&apos;m coming
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1"
                    disabled={action.isPending}
                    onClick={() => action.mutate("cancel", { onSuccess: () => toast("Your place was cancelled") })}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : s.status === "CONFIRMED" ? (
              <p className="mt-6 text-sm">Confirmed — please head to the restaurant.</p>
            ) : (
              <>
                <p className="mt-6 text-sm text-muted-foreground">
                  We&apos;ll text you when your table is nearly ready.
                </p>
                <Button
                  variant="ghost"
                  className="mt-4"
                  disabled={action.isPending}
                  onClick={() => action.mutate("cancel", { onSuccess: () => toast("Your place was cancelled") })}
                >
                  Cancel my place
                </Button>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Centered({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 text-center">
      <div>
        <h1 className="font-display text-2xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      </div>
    </div>
  );
}
