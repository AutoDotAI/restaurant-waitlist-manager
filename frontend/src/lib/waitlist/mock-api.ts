/**
 * MOCK BACKEND — single replacement seam.
 *
 * Every function here mimics a future HTTP/RPC call: it is async, adds a small
 * latency, and only exchanges plain serializable DTOs. When the real backend
 * exists, replace the bodies of the exported functions in `api` with fetch /
 * server-function calls. Nothing else in the app touches the store.
 */
import type {
  AnalyticsSummary,
  GuestStatus,
  JoinInput,
  PublicRestaurantInfo,
  Restaurant,
  SmsMessage,
  SmsType,
  StaffUser,
  WaitlistEntry,
} from "./types";
import { ACTIVE_STATUSES } from "./types";

const STORAGE_KEY = "waitlist-mock-db-v1";
const LATENCY = 220;

interface Db {
  restaurant: Restaurant;
  staff: StaffUser[];
  entries: WaitlistEntry[];
  sms: SmsMessage[];
  session: StaffUser | null;
}

function id(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function token() {
  return Math.random().toString(36).slice(2, 8) + Math.random().toString(36).slice(2, 8);
}

function minutesAgo(m: number) {
  return new Date(Date.now() - m * 60_000).toISOString();
}

function seed(): Db {
  const restaurant: Restaurant = {
    id: "rest_1",
    slug: "big-mamma",
    name: "Ober Mamma",
    timezone: "Europe/Paris",
    phoneCountryCode: "+33",
    remoteJoinEnabled: true,
    arrivalWindowMinutes: 30,
    gracePeriodMinutes: 10,
    maxPartySize: 12,
    baseWaitPerGroupMinutes: 7,
    smsSenderName: "OberMamma",
  };

  const staff: StaffUser[] = [
    { id: "staff_1", restaurantId: "rest_1", name: "Claire Dubois", email: "claire@obermamma.fr", role: "MANAGER" },
    { id: "staff_2", restaurantId: "rest_1", name: "Tom Réno", email: "tom@obermamma.fr", role: "HOST" },
  ];

  const base = [
    { name: "Sarah", phone: "+33 6 12 34 56 78", party: 2, source: "WALK_IN", status: "WAITING", joined: 12 },
    { name: "Julien", phone: "+33 6 22 41 09 13", party: 4, source: "REMOTE", status: "ARRIVED", joined: 22 },
    { name: "Emma", phone: "+33 6 87 55 20 44", party: 3, source: "REMOTE", status: "NOTIFIED", joined: 31 },
    { name: "David", phone: "+33 6 71 08 66 90", party: 2, source: "WALK_IN", status: "WAITING", joined: 4 },
    { name: "Léa", phone: "+33 6 45 77 31 02", party: 6, source: "REMOTE", status: "WAITING", joined: 2 },
  ] as const;

  const entries: WaitlistEntry[] = base.map((g, i) => ({
    id: id("wl"),
    restaurantId: restaurant.id,
    publicToken: token(),
    customerName: g.name,
    phoneNumber: g.phone,
    partySize: g.party,
    source: g.source,
    status: g.status as GuestStatus,
    estimatedWaitMinutes: 0,
    manualWaitOverride: null,
    queuePosition: i + 1,
    joinedAt: minutesAgo(g.joined),
    expectedArrivalAt: g.source === "REMOTE" ? minutesAgo(g.joined - 30) : null,
    arrivedAt: g.status === "ARRIVED" ? minutesAgo(2) : null,
    notifiedAt: g.status === "NOTIFIED" ? minutesAgo(6) : null,
    confirmedAt: null,
    seatedAt: null,
    cancelledAt: null,
    staffNotes: "",
  }));

  const history: WaitlistEntry[] = [
    ["Marco", 2, "SEATED", 95, "WALK_IN"],
    ["Inès", 4, "SEATED", 80, "REMOTE"],
    ["Paul", 5, "NO_SHOW", 70, "REMOTE"],
    ["Nora", 3, "SEATED", 60, "WALK_IN"],
    ["Hugo", 2, "CANCELLED", 50, "REMOTE"],
  ].map(([name, party, status, ago, source], i) => ({
    id: id("wl"),
    restaurantId: restaurant.id,
    publicToken: token(),
    customerName: name as string,
    phoneNumber: "+33 6 00 00 00 0" + i,
    partySize: party as number,
    source: source as WaitlistEntry["source"],
    status: status as GuestStatus,
    estimatedWaitMinutes: 20,
    manualWaitOverride: null,
    queuePosition: 100 + i,
    joinedAt: minutesAgo(ago as number),
    expectedArrivalAt: null,
    arrivedAt: null,
    notifiedAt: minutesAgo((ago as number) - 15),
    confirmedAt: null,
    seatedAt: status === "SEATED" ? minutesAgo((ago as number) - 22) : null,
    cancelledAt: status === "CANCELLED" ? minutesAgo((ago as number) - 10) : null,
    staffNotes: "",
  }));

  const db: Db = { restaurant, staff, entries: [...entries, ...history], sms: [], session: null };
  recalculate(db);
  return db;
}

let cache: Db | null = null;

function load(): Db {
  if (cache) return cache;
  if (typeof window !== "undefined") {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        cache = JSON.parse(raw) as Db;
        return cache;
      } catch {
        /* fall through to seed */
      }
    }
  }
  cache = seed();
  persist();
  return cache;
}

function persist() {
  if (typeof window !== "undefined" && cache) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
  }
}

function partyModifier(size: number) {
  if (size <= 2) return 1;
  if (size <= 4) return 1.2;
  if (size <= 6) return 1.5;
  return 2;
}

/** Rule-based wait estimate: parties ahead x base time x party-size modifier. */
function recalculate(db: Db) {
  const active = db.entries
    .filter((e) => ACTIVE_STATUSES.includes(e.status))
    .sort((a, b) => a.queuePosition - b.queuePosition);

  active.forEach((entry, index) => {
    entry.queuePosition = index + 1;
    const raw = index * db.restaurant.baseWaitPerGroupMinutes * partyModifier(entry.partySize);
    entry.estimatedWaitMinutes = Math.max(0, Math.round(raw));
  });
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY));
}

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T;
}

function smsBody(db: Db, entry: WaitlistEntry, type: SmsType) {
  const wait = entry.manualWaitOverride ?? entry.estimatedWaitMinutes;
  const link = `/r/status/${entry.publicToken}`;
  switch (type) {
    case "WAITLIST_CONFIRMATION":
      return `You're on the waitlist at ${db.restaurant.name}. Estimated wait: ~${wait} minutes. Track your wait: ${link}`;
    case "TABLE_NEARLY_READY":
      return `Your table at ${db.restaurant.name} is nearly ready. Please confirm you're coming: ${link}`;
    case "CONFIRMATION_RECEIVED":
      return `Thanks — we've confirmed you're coming. Please head to ${db.restaurant.name}.`;
  }
}

function sendSms(db: Db, entry: WaitlistEntry, type: SmsType) {
  db.sms.unshift({
    id: id("sms"),
    waitlistEntryId: entry.id,
    phoneNumber: entry.phoneNumber,
    messageType: type,
    body: smsBody(db, entry, type),
    status: "SENT",
    sentAt: new Date().toISOString(),
  });
}

function waitRange(db: Db): [number, number] {
  const active = db.entries.filter((e) => ACTIVE_STATUSES.includes(e.status));
  const base = active.length * db.restaurant.baseWaitPerGroupMinutes;
  return [base, Math.round(base * 1.4) + 5];
}

export const api = {
  /* ---------- auth ---------- */
  async login(email: string, _password: string) {
    const db = load();
    const user = db.staff.find((s) => s.email.toLowerCase() === email.trim().toLowerCase());
    if (!user) throw new Error("No staff account matches that email.");
    db.session = user;
    persist();
    return delay(clone(user));
  },
  async logout() {
    const db = load();
    db.session = null;
    persist();
    return delay(true);
  },
  async getSession(): Promise<StaffUser | null> {
    const db = load();
    return delay(clone(db.session));
  },

  /* ---------- restaurant ---------- */
  async getRestaurant(): Promise<Restaurant> {
    return delay(clone(load().restaurant));
  },
  async updateRestaurant(patch: Partial<Restaurant>): Promise<Restaurant> {
    const db = load();
    db.restaurant = { ...db.restaurant, ...patch };
    recalculate(db);
    persist();
    return delay(clone(db.restaurant));
  },
  async listStaff(): Promise<StaffUser[]> {
    return delay(clone(load().staff));
  },
  async addStaff(input: { name: string; email: string; role: StaffUser["role"] }): Promise<StaffUser> {
    const db = load();
    const user: StaffUser = { id: id("staff"), restaurantId: db.restaurant.id, ...input };
    db.staff.push(user);
    persist();
    return delay(clone(user));
  },
  async removeStaff(staffId: string) {
    const db = load();
    db.staff = db.staff.filter((s) => s.id !== staffId);
    persist();
    return delay(true);
  },

  /* ---------- waitlist ---------- */
  async listQueue(): Promise<WaitlistEntry[]> {
    const db = load();
    recalculate(db);
    persist();
    return delay(
      clone(
        db.entries
          .filter((e) => ACTIVE_STATUSES.includes(e.status))
          .sort((a, b) => a.queuePosition - b.queuePosition),
      ),
    );
  },
  async listHistory(): Promise<WaitlistEntry[]> {
    const db = load();
    return delay(clone(db.entries.filter((e) => !ACTIVE_STATUSES.includes(e.status))));
  },
  async addGuest(input: JoinInput): Promise<WaitlistEntry> {
    const db = load();
    if (input.partySize > db.restaurant.maxPartySize) {
      throw new Error(`Maximum party size is ${db.restaurant.maxPartySize}.`);
    }
    const duplicate = db.entries.find(
      (e) => ACTIVE_STATUSES.includes(e.status) && e.phoneNumber.replace(/\s/g, "") === input.phoneNumber.replace(/\s/g, ""),
    );
    if (duplicate) throw new Error("This phone number already has an active waitlist entry.");

    const entry: WaitlistEntry = {
      id: id("wl"),
      restaurantId: db.restaurant.id,
      publicToken: token(),
      customerName: input.customerName,
      phoneNumber: input.phoneNumber,
      partySize: input.partySize,
      source: input.source,
      status: "WAITING",
      estimatedWaitMinutes: 0,
      manualWaitOverride: null,
      queuePosition: db.entries.length + 1,
      joinedAt: new Date().toISOString(),
      expectedArrivalAt:
        input.source === "REMOTE"
          ? new Date(Date.now() + db.restaurant.arrivalWindowMinutes * 60_000).toISOString()
          : null,
      arrivedAt: null,
      notifiedAt: null,
      confirmedAt: null,
      seatedAt: null,
      cancelledAt: null,
      staffNotes: input.staffNotes ?? "",
    };
    db.entries.push(entry);
    recalculate(db);
    sendSms(db, entry, "WAITLIST_CONFIRMATION");
    persist();
    return delay(clone(entry));
  },
  async updateGuest(entryId: string, patch: Partial<WaitlistEntry>): Promise<WaitlistEntry> {
    const db = load();
    const entry = db.entries.find((e) => e.id === entryId);
    if (!entry) throw new Error("Guest not found.");
    Object.assign(entry, patch);
    recalculate(db);
    persist();
    return delay(clone(entry));
  },
  async setStatus(entryId: string, status: GuestStatus): Promise<WaitlistEntry> {
    const db = load();
    const entry = db.entries.find((e) => e.id === entryId);
    if (!entry) throw new Error("Guest not found.");
    const now = new Date().toISOString();
    entry.status = status;
    if (status === "ARRIVED") entry.arrivedAt = now;
    if (status === "NOTIFIED") {
      entry.notifiedAt = now;
      sendSms(db, entry, "TABLE_NEARLY_READY");
    }
    if (status === "CONFIRMED") {
      entry.confirmedAt = now;
      sendSms(db, entry, "CONFIRMATION_RECEIVED");
    }
    if (status === "SEATED") entry.seatedAt = now;
    if (status === "CANCELLED") entry.cancelledAt = now;
    recalculate(db);
    persist();
    return delay(clone(entry));
  },
  async reorderQueue(orderedIds: string[]): Promise<WaitlistEntry[]> {
    const db = load();
    orderedIds.forEach((entryId, index) => {
      const entry = db.entries.find((e) => e.id === entryId);
      if (entry) entry.queuePosition = index + 1;
    });
    recalculate(db);
    persist();
    return delay(
      clone(
        db.entries
          .filter((e) => ACTIVE_STATUSES.includes(e.status))
          .sort((a, b) => a.queuePosition - b.queuePosition),
      ),
    );
  },
  async listSms(): Promise<SmsMessage[]> {
    return delay(clone(load().sms.slice(0, 30)));
  },

  /* ---------- public / customer ---------- */
  async getPublicRestaurant(slug: string): Promise<PublicRestaurantInfo> {
    const db = load();
    if (db.restaurant.slug !== slug) throw new Error("Restaurant not found.");
    return delay({
      name: db.restaurant.name,
      slug: db.restaurant.slug,
      remoteJoinEnabled: db.restaurant.remoteJoinEnabled,
      maxPartySize: db.restaurant.maxPartySize,
      estimatedWaitRange: waitRange(db),
      partiesWaiting: db.entries.filter((e) => ACTIVE_STATUSES.includes(e.status)).length,
    });
  },
  async joinRemotely(slug: string, input: Omit<JoinInput, "source">): Promise<{ token: string }> {
    const db = load();
    if (db.restaurant.slug !== slug) throw new Error("Restaurant not found.");
    if (!db.restaurant.remoteJoinEnabled) throw new Error("Remote joining is currently closed.");
    const entry = await api.addGuest({ ...input, source: "REMOTE" });
    return { token: entry.publicToken };
  },
  async getPublicStatus(publicToken: string) {
    const db = load();
    const entry = db.entries.find((e) => e.publicToken === publicToken);
    if (!entry) throw new Error("This waitlist link is no longer valid.");
    return delay({
      restaurantName: db.restaurant.name,
      customerName: entry.customerName,
      partySize: entry.partySize,
      status: entry.status,
      estimatedWaitMinutes: entry.manualWaitOverride ?? entry.estimatedWaitMinutes,
      gracePeriodMinutes: db.restaurant.gracePeriodMinutes,
      notifiedAt: entry.notifiedAt,
    });
  },
  async customerConfirm(publicToken: string) {
    const db = load();
    const entry = db.entries.find((e) => e.publicToken === publicToken);
    if (!entry) throw new Error("This waitlist link is no longer valid.");
    return api.setStatus(entry.id, "CONFIRMED");
  },
  async customerCancel(publicToken: string) {
    const db = load();
    const entry = db.entries.find((e) => e.publicToken === publicToken);
    if (!entry) throw new Error("This waitlist link is no longer valid.");
    return api.setStatus(entry.id, "CANCELLED");
  },

  /* ---------- analytics ---------- */
  async getAnalytics(range: "today" | "7d" | "30d"): Promise<AnalyticsSummary> {
    const db = load();
    const windowMs = range === "today" ? 24 * 3600_000 : range === "7d" ? 7 * 24 * 3600_000 : 30 * 24 * 3600_000;
    const since = Date.now() - windowMs;
    const rows = db.entries.filter((e) => new Date(e.joinedAt).getTime() >= since);
    const seated = rows.filter((e) => e.status === "SEATED");
    const actual = seated
      .filter((e) => e.seatedAt)
      .map((e) => (new Date(e.seatedAt!).getTime() - new Date(e.joinedAt).getTime()) / 60_000);
    const avg = (n: number[]) => (n.length ? Math.round(n.reduce((a, b) => a + b, 0) / n.length) : 0);
    return delay({
      guestsServed: seated.length,
      averageEstimatedWait: avg(rows.map((e) => e.manualWaitOverride ?? e.estimatedWaitMinutes)),
      averageActualWait: avg(actual),
      cancellations: rows.filter((e) => e.status === "CANCELLED").length,
      noShows: rows.filter((e) => e.status === "NO_SHOW").length,
      walkIns: rows.filter((e) => e.source === "WALK_IN").length,
      remoteJoins: rows.filter((e) => e.source === "REMOTE").length,
      averagePartySize: Math.round(avg(rows.map((e) => e.partySize)) * 10) / 10,
    });
  },
};
