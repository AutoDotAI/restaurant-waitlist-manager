import type {
  AnalyticsSummary,
  GuestStatus,
  JoinInput,
  PublicRestaurantInfo,
  Restaurant,
  SmsMessage,
  StaffUser,
  WaitlistEntry,
} from "./types";

const API_BASE_URL = (import.meta.env["VITE_API_BASE_URL"] || "http://localhost:8001").replace(/\/+$/, "");
const TOKEN_STORAGE_KEY = "waitlist-access-token";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
}

interface LoginResponse {
  accessToken: string;
  user: StaffUser;
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

function clearAccessToken() {
  if (typeof window !== "undefined") window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let body: string | undefined;
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    ...(body === undefined ? {} : { body }),
  });

  const responseText = await response.text();
  let payload: unknown = null;
  if (responseText) {
    try {
      payload = JSON.parse(responseText) as unknown;
    } catch {
      payload = responseText;
    }
  }

  if (!response.ok) {
    const errorPayload = payload as { message?: unknown; detail?: unknown } | null;
    const message =
      typeof errorPayload?.message === "string"
        ? errorPayload.message
        : typeof errorPayload?.detail === "string"
          ? errorPayload.detail
          : `Request failed (${response.status}).`;
    throw new Error(message);
  }

  return payload as T;
}

export const api = {
  async login(email: string, password: string): Promise<StaffUser> {
    const result = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(TOKEN_STORAGE_KEY, result.accessToken);
    }
    return result.user;
  },

  async logout(): Promise<boolean> {
    if (!getAccessToken()) {
      clearAccessToken();
      return true;
    }
    try {
      await request<{ success: boolean }>("/auth/logout", { method: "POST" });
      return true;
    } finally {
      clearAccessToken();
    }
  },

  async getSession(): Promise<StaffUser | null> {
    if (!getAccessToken()) return null;
    const user = await request<StaffUser | null>("/auth/session");
    if (!user) clearAccessToken();
    return user;
  },

  getRestaurant(): Promise<Restaurant> {
    return request("/restaurant");
  },

  updateRestaurant(patch: Partial<Restaurant>): Promise<Restaurant> {
    const { id: _id, ...body } = patch;
    return request("/restaurant", { method: "PATCH", body });
  },

  listStaff(): Promise<StaffUser[]> {
    return request("/restaurant/staff");
  },

  addStaff(input: { name: string; email: string; role: StaffUser["role"]; password?: string }): Promise<StaffUser> {
    return request("/restaurant/staff", { method: "POST", body: input });
  },

  async removeStaff(staffId: string): Promise<boolean> {
    await request<{ success: boolean }>(`/restaurant/staff/${encodeURIComponent(staffId)}`, { method: "DELETE" });
    return true;
  },

  listQueue(): Promise<WaitlistEntry[]> {
    return request("/waitlist");
  },

  listHistory(): Promise<WaitlistEntry[]> {
    return request("/waitlist/history");
  },

  addGuest(input: JoinInput): Promise<WaitlistEntry> {
    return request("/waitlist", { method: "POST", body: input });
  },

  updateGuest(entryId: string, patch: Partial<WaitlistEntry>): Promise<WaitlistEntry> {
    const { id: _id, restaurantId: _restaurantId, publicToken: _publicToken, joinedAt: _joinedAt, ...body } = patch;
    return request(`/waitlist/${encodeURIComponent(entryId)}`, { method: "PATCH", body });
  },

  setStatus(entryId: string, status: GuestStatus): Promise<WaitlistEntry> {
    return request(`/waitlist/${encodeURIComponent(entryId)}/status`, { method: "PUT", body: { status } });
  },

  reorderQueue(orderedIds: string[]): Promise<WaitlistEntry[]> {
    return request("/waitlist/reorder", { method: "PUT", body: { orderedIds } });
  },

  listSms(): Promise<SmsMessage[]> {
    return request("/waitlist/sms");
  },

  getPublicRestaurant(slug: string): Promise<PublicRestaurantInfo> {
    return request(`/public/restaurants/${encodeURIComponent(slug)}`);
  },

  joinRemotely(slug: string, input: Omit<JoinInput, "source">): Promise<{ token: string }> {
    const { staffNotes: _staffNotes, ...body } = input;
    return request(`/public/restaurants/${encodeURIComponent(slug)}/waitlist`, { method: "POST", body });
  },

  getPublicStatus(token: string): Promise<PublicWaitlistStatus> {
    return request(`/public/waitlist/${encodeURIComponent(token)}`);
  },

  customerConfirm(token: string): Promise<WaitlistEntry> {
    return request(`/public/waitlist/${encodeURIComponent(token)}/confirm`, { method: "POST" });
  },

  customerCancel(token: string): Promise<WaitlistEntry> {
    return request(`/public/waitlist/${encodeURIComponent(token)}/cancel`, { method: "POST" });
  },

  getAnalytics(range: "today" | "7d" | "30d"): Promise<AnalyticsSummary> {
    return request(`/analytics?${new URLSearchParams({ range })}`);
  },
};

export interface PublicWaitlistStatus {
  restaurantName: string;
  customerName: string;
  partySize: number;
  status: GuestStatus;
  estimatedWaitMinutes: number;
  gracePeriodMinutes: number;
  notifiedAt: string | null;
}
