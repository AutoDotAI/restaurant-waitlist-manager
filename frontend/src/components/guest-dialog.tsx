import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAddGuest, useRestaurant, useUpdateGuest } from "@/lib/waitlist/hooks";
import type { WaitlistEntry } from "@/lib/waitlist/types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entry?: WaitlistEntry | null;
}

export function GuestDialog({ open, onOpenChange, entry }: Props) {
  const restaurant = useRestaurant();
  const addGuest = useAddGuest();
  const updateGuest = useUpdateGuest();
  const editing = Boolean(entry);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [party, setParty] = useState("2");
  const [notes, setNotes] = useState("");
  const [override, setOverride] = useState("");

  useEffect(() => {
    if (!open) return;
    setName(entry?.customerName ?? "");
    setPhone(entry?.phoneNumber ?? restaurant.data?.phoneCountryCode ?? "");
    setParty(String(entry?.partySize ?? 2));
    setNotes(entry?.staffNotes ?? "");
    setOverride(entry?.manualWaitOverride != null ? String(entry.manualWaitOverride) : "");
  }, [open, entry, restaurant.data?.phoneCountryCode]);

  const max = restaurant.data?.maxPartySize ?? 12;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const size = Number(party);
    if (!name.trim()) {
      toast.error("Guest name is required.");
      return;
    }
    if (phone.replace(/\D/g, "").length < 6) {
      toast.error("Enter a valid phone number.");
      return;
    }
    if (!Number.isFinite(size) || size < 1 || size > max) {
      toast.error(`Party size must be 1–${max}.`);
      return;
    }

    if (editing && entry) {
      updateGuest.mutate(
        {
          id: entry.id,
          patch: {
            customerName: name.trim(),
            phoneNumber: phone.trim(),
            partySize: size,
            staffNotes: notes,
            manualWaitOverride: override.trim() === "" ? null : Number(override),
          },
        },
        {
          onSuccess: () => {
            toast.success("Guest updated");
            onOpenChange(false);
          },
          onError: (e) => toast.error((e as Error).message),
        },
      );
      return;
    }

    addGuest.mutate(
      { customerName: name.trim(), phoneNumber: phone.trim(), partySize: size, source: "WALK_IN", staffNotes: notes },
      {
        onSuccess: () => {
          toast.success(`${name.trim()} added to the waitlist`);
          onOpenChange(false);
        },
        onError: (e) => toast.error((e as Error).message),
      },
    );
  }

  const pending = addGuest.isPending || updateGuest.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display">{editing ? "Edit guest" : "Add walk-in guest"}</DialogTitle>
          <DialogDescription>
            {editing ? "Update details or override the displayed wait." : "Name, phone and party size — that's it."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="g-name">Name</Label>
            <Input id="g-name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="g-phone">Phone</Label>
              <Input id="g-phone" value={phone} maxLength={24} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="g-party">Party size</Label>
              <Input
                id="g-party"
                type="number"
                min={1}
                max={max}
                value={party}
                onChange={(e) => setParty(e.target.value)}
              />
            </div>
          </div>
          {editing && (
            <div className="space-y-2">
              <Label htmlFor="g-override">Wait override (minutes)</Label>
              <Input
                id="g-override"
                type="number"
                min={0}
                placeholder="Leave empty to use the system estimate"
                value={override}
                onChange={(e) => setOverride(e.target.value)}
              />
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="g-notes">Staff notes</Label>
            <Textarea
              id="g-notes"
              rows={2}
              maxLength={200}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Terrace preferred, regular, birthday…"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : editing ? "Save changes" : "Add to waitlist"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
