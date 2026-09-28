export type GuestStatus =
  | "WAITING"
  | "ARRIVED"
  | "NOTIFIED"
  | "CONFIRMED"
  | "SEATED"
  | "CANCELLED"
  | "NO_SHOW"
  | "REMOVED";

export const ACTIVE_STATUSES: GuestStatus[] = ["WAITING", "ARRIVED", "NOTIFIED", "CONFIRMED"];
export const TERMINAL_STATUSES: GuestStatus[] = ["SEATED", "CANCELLED", "NO_SHOW", "REMOVED"];

export type GuestSource = "WALK_IN" | "REMOTE";

export type StaffRole = "MANAGER" | "HOST";

export interface Restaurant {
  id: string;
  slug: string;
  name: string;
  timezone: string;
  phoneCountryCode: string;
  remoteJoinEnabled: boolean;
  arrivalWindowMinutes: number;
  gracePeriodMinutes: number;
  maxPartySize: number;
  baseWaitPerGroupMinutes: number;
  smsSenderName: string;
}

export interface StaffUser {
  id: string;
  restaurantId: string;
  name: string;
  email: string;
  role: StaffRole;
}

export interface WaitlistEntry {
  id: string;
  restaurantId: string;
  publicToken: string;
  customerName: string;
  phoneNumber: string;
  partySize: number;
  source: GuestSource;
  status: GuestStatus;
  estimatedWaitMinutes: number;
  manualWaitOverride: number | null;
  queuePosition: number;
  joinedAt: string;
  expectedArrivalAt: string | null;
  arrivedAt: string | null;
  notifiedAt: string | null;
  confirmedAt: string | null;
  seatedAt: string | null;
  cancelledAt: string | null;
  staffNotes: string;
}

export type SmsType = "WAITLIST_CONFIRMATION" | "TABLE_NEARLY_READY" | "CONFIRMATION_RECEIVED";

export interface SmsMessage {
  id: string;
  waitlistEntryId: string;
  phoneNumber: string;
  messageType: SmsType;
  body: string;
  status: "SENT" | "FAILED";
  sentAt: string;
}

export interface AnalyticsSummary {
  guestsServed: number;
  averageEstimatedWait: number;
  averageActualWait: number;
  cancellations: number;
  noShows: number;
  walkIns: number;
  remoteJoins: number;
  averagePartySize: number;
}

export interface JoinInput {
  customerName: string;
  phoneNumber: string;
  partySize: number;
  source: GuestSource;
  staffNotes?: string;
}

export interface PublicRestaurantInfo {
  name: string;
  slug: string;
  remoteJoinEnabled: boolean;
  maxPartySize: number;
  estimatedWaitRange: [number, number];
  partiesWaiting: number;
}
