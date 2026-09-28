import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "@/lib/waitlist/hooks";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Staff sign in — Hostline" },
      { name: "description", content: "Sign in to manage tonight's restaurant waitlist." },
      { property: "og:title", content: "Staff sign in — Hostline" },
      { property: "og:description", content: "Sign in to manage tonight's restaurant waitlist." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState("claire@obermamma.fr");
  const [password, setPassword] = useState("demo1234");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    login.mutate(
      { email, password },
      {
        onSuccess: (user) => {
          toast.success(`Welcome back, ${user.name.split(" ")[0]}`);
          navigate({ to: "/" });
        },
        onError: (e) => toast.error((e as Error).message),
      },
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="panel w-full max-w-sm p-8">
        <span
          className="grid size-11 place-items-center rounded-xl font-display text-xl font-bold text-primary-foreground"
          style={{ background: "var(--gradient-warm)" }}
        >
          H
        </span>
        <h1 className="mt-5 font-display text-2xl font-bold">Staff sign in</h1>
        <p className="mt-1 text-sm text-muted-foreground">Hosts and managers only.</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button type="submit" className="w-full" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-xs text-muted-foreground">
          Demo accounts: claire@obermamma.fr (manager) · tom@obermamma.fr (host). Any password works until the real
          backend is connected.
        </p>
      </div>
    </div>
  );
}
