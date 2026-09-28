import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { GripVertical, MoreHorizontal, Pencil } from "lucide-react";
import type { GuestStatus, WaitlistEntry } from "@/lib/waitlist/types";

const STATUS_STYLES: Record<GuestStatus, string> = {
  WAITING: "bg-secondary text-secondary-foreground",
  ARRIVED: "bg-accent/20 text-accent",
  NOTIFIED: "bg-primary/20 text-primary",
  CONFIRMED: "bg-primary text-primary-foreground",
  SEATED: "bg-secondary text-muted-foreground",
  CANCELLED: "bg-destructive/20 text-destructive",
  NO_SHOW: "bg-destructive/20 text-destructive",
  REMOVED: "bg-secondary text-muted-foreground",
};

function minutesSince(iso: string | null) {
  if (!iso) return null;
  return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
}

interface Props {
  entry: WaitlistEntry;
  index: number;
  gracePeriodMinutes: number;
  dragging: boolean;
  onEdit: () => void;
  onStatus: (status: GuestStatus) => void;
  onDragStart: () => void;
  onDragOver: () => void;
  onDragEnd: () => void;
}

export function QueueRow({
  entry,
  index,
  gracePeriodMinutes,
  dragging,
  onEdit,
  onStatus,
  onDragStart,
  onDragOver,
  onDragEnd,
}: Props) {
  const wait = entry.manualWaitOverride ?? entry.estimatedWaitMinutes;
  const waitingFor = minutesSince(entry.joinedAt);
  const notifiedFor = minutesSince(entry.notifiedAt);
  const graceExpired = notifiedFor != null && notifiedFor > gracePeriodMinutes;

  return (
    <li
      draggable
      onDragStart={onDragStart}
      onDragOver={(e) => {
        e.preventDefault();
        onDragOver();
      }}
      onDragEnd={onDragEnd}
      onDrop={(e) => e.preventDefault()}
      className={`panel flex flex-wrap items-center gap-3 px-3 py-3 transition-opacity sm:px-4 ${
        dragging ? "opacity-40" : "opacity-100"
      }`}
    >
      <GripVertical className="size-4 shrink-0 cursor-grab text-muted-foreground" aria-hidden />
      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-secondary font-display text-sm font-bold">
        {index + 1}
      </span>

      <div className="min-w-[9rem] flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-display text-base font-bold">{entry.customerName}</p>
          <Badge variant="outline" className="text-xs">
            {entry.partySize} {entry.partySize === 1 ? "guest" : "guests"}
          </Badge>
          <Badge variant="outline" className="text-xs text-muted-foreground">
            {entry.source === "WALK_IN" ? "Walk-in" : "Remote"}
          </Badge>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {entry.phoneNumber} · waiting {waitingFor} min
          {entry.staffNotes ? ` · ${entry.staffNotes}` : ""}
        </p>
      </div>

      <div className="text-right">
        <p className="font-display text-lg font-bold">
          {wait} <span className="text-xs font-medium text-muted-foreground">min</span>
        </p>
        {entry.manualWaitOverride != null && <p className="text-[11px] text-primary">host override</p>}
      </div>

      <div className="flex flex-col items-end gap-1">
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[entry.status]}`}>
          {entry.status.replace("_", " ").toLowerCase()}
        </span>
        {notifiedFor != null && entry.status === "NOTIFIED" && (
          <span className={`text-[11px] ${graceExpired ? "text-destructive" : "text-muted-foreground"}`}>
            {graceExpired ? "Grace period expired" : `Notified ${notifiedFor} min ago`}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {entry.status === "WAITING" && entry.source === "REMOTE" && (
          <Button size="sm" variant="secondary" onClick={() => onStatus("ARRIVED")}>
            Arrived
          </Button>
        )}
        {(entry.status === "WAITING" || entry.status === "ARRIVED") && (
          <Button size="sm" onClick={() => onStatus("NOTIFIED")}>
            Notify
          </Button>
        )}
        {(entry.status === "NOTIFIED" || entry.status === "CONFIRMED") && (
          <Button size="sm" onClick={() => onStatus("SEATED")}>
            Seat
          </Button>
        )}
        <Button size="icon" variant="ghost" aria-label="Edit guest" onClick={onEdit}>
          <Pencil className="size-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="icon" variant="ghost" aria-label="More actions">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onStatus("ARRIVED")}>Mark arrived</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onStatus("NOTIFIED")}>Notify by SMS</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onStatus("CONFIRMED")}>Mark confirmed</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onStatus("SEATED")}>Seat guest</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onStatus("CANCELLED")}>Cancel</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onStatus("NO_SHOW")}>No-show</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onStatus("REMOVED")}>Remove</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  );
}
