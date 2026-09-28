import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./mock-api";
import type { GuestStatus, JoinInput, Restaurant, StaffUser, WaitlistEntry } from "./types";

const keys = {
  session: ["session"] as const,
  restaurant: ["restaurant"] as const,
  staff: ["staff"] as const,
  queue: ["queue"] as const,
  history: ["history"] as const,
  sms: ["sms"] as const,
  analytics: (range: string) => ["analytics", range] as const,
  publicRestaurant: (slug: string) => ["public-restaurant", slug] as const,
  publicStatus: (t: string) => ["public-status", t] as const,
};

function useInvalidateAll() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: keys.queue });
    qc.invalidateQueries({ queryKey: keys.history });
    qc.invalidateQueries({ queryKey: keys.sms });
    qc.invalidateQueries({ queryKey: ["analytics"] });
  };
}

export function useSession() {
  return useQuery({ queryKey: keys.session, queryFn: () => api.getSession() });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { email: string; password: string }) => api.login(v.email, v.password),
    onSuccess: (user) => qc.setQueryData(keys.session, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => qc.setQueryData(keys.session, null),
  });
}

export function useRestaurant() {
  return useQuery({ queryKey: keys.restaurant, queryFn: () => api.getRestaurant() });
}

export function useUpdateRestaurant() {
  const qc = useQueryClient();
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (patch: Partial<Restaurant>) => api.updateRestaurant(patch),
    onSuccess: (r) => {
      qc.setQueryData(keys.restaurant, r);
      invalidate();
    },
  });
}

export function useStaff() {
  return useQuery({ queryKey: keys.staff, queryFn: () => api.listStaff() });
}

export function useAddStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { name: string; email: string; role: StaffUser["role"] }) => api.addStaff(v),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.staff }),
  });
}

export function useRemoveStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (staffId: string) => api.removeStaff(staffId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.staff }),
  });
}

export function useQueue() {
  return useQuery({ queryKey: keys.queue, queryFn: () => api.listQueue(), refetchInterval: 15_000 });
}

export function useHistory() {
  return useQuery({ queryKey: keys.history, queryFn: () => api.listHistory() });
}

export function useSmsLog() {
  return useQuery({ queryKey: keys.sms, queryFn: () => api.listSms() });
}

export function useAddGuest() {
  const invalidate = useInvalidateAll();
  return useMutation({ mutationFn: (v: JoinInput) => api.addGuest(v), onSuccess: invalidate });
}

export function useUpdateGuest() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (v: { id: string; patch: Partial<WaitlistEntry> }) => api.updateGuest(v.id, v.patch),
    onSuccess: invalidate,
  });
}

export function useSetStatus() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (v: { id: string; status: GuestStatus }) => api.setStatus(v.id, v.status),
    onSuccess: invalidate,
  });
}

export function useReorderQueue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderedIds: string[]) => api.reorderQueue(orderedIds),
    onSuccess: (rows) => qc.setQueryData(keys.queue, rows),
  });
}

export function useAnalytics(range: "today" | "7d" | "30d") {
  return useQuery({ queryKey: keys.analytics(range), queryFn: () => api.getAnalytics(range) });
}

export function usePublicRestaurant(slug: string) {
  return useQuery({ queryKey: keys.publicRestaurant(slug), queryFn: () => api.getPublicRestaurant(slug) });
}

export function useJoinRemotely(slug: string) {
  return useMutation({
    mutationFn: (v: Omit<JoinInput, "source">) => api.joinRemotely(slug, v),
  });
}

export function usePublicStatus(publicToken: string) {
  return useQuery({
    queryKey: keys.publicStatus(publicToken),
    queryFn: () => api.getPublicStatus(publicToken),
    refetchInterval: 20_000,
  });
}

export function useCustomerAction(publicToken: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: "confirm" | "cancel") =>
      action === "confirm" ? api.customerConfirm(publicToken) : api.customerCancel(publicToken),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.publicStatus(publicToken) }),
  });
}
