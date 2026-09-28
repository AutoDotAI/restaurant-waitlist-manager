import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Loader2, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLogout, useRestaurant, useSession } from "@/lib/waitlist/hooks";

const NAV = [
  { to: "/", label: "Waitlist" },
  { to: "/analytics", label: "Analytics" },
  { to: "/settings", label: "Settings" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const session = useSession();
  const restaurant = useRestaurant();
  const logout = useLogout();

  useEffect(() => {
    if (!session.isLoading && !session.data) {
      navigate({ to: "/login" });
    }
  }, [session.isLoading, session.data, navigate]);

  if (session.isLoading || !session.data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-xl text-lg font-bold text-primary-foreground" style={{ background: "var(--gradient-warm)" }}>
              H
            </span>
            <div className="leading-tight">
              <p className="font-display text-base font-bold">{restaurant.data?.name ?? "Hostline"}</p>
              <p className="text-xs text-muted-foreground">Waitlist manager</p>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                activeOptions={{ exact: item.to === "/" }}
                className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                activeProps={{ className: "bg-secondary text-foreground" }}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">{session.data.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{session.data.role.toLowerCase()}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Sign out"
              onClick={() => logout.mutate(undefined, { onSettled: () => navigate({ to: "/login" }) })}
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
