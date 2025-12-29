import { apiGet } from "../../api/client";
import type { components } from "../../api/openapi";

type ListAdminUsersResponse = components["schemas"]["ListAdminUsersResponse"];
type AdminUserResponse = components["schemas"]["AdminUserResponse"];
type AdminUserLoginEventsResponse = components["schemas"]["AdminUserLoginEventsResponse"];

export type AdminUser = components["schemas"]["User"];
export type LoginEvent = components["schemas"]["LoginEvent"];

export async function listAdminUsers(params?: {
  limit?: number;
  offset?: number;
}): Promise<ListAdminUsersResponse> {
  const limit = params?.limit ?? 50;
  const offset = params?.offset ?? 0;
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return await apiGet<ListAdminUsersResponse>(`/api/v1/admin/users?${query.toString()}`);
}

export async function getAdminUser(userId: string): Promise<AdminUserResponse> {
  return await apiGet<AdminUserResponse>(`/api/v1/admin/users/${userId}`);
}

export async function getAdminUserLoginEvents(
  userId: string,
  params?: { limit?: number },
): Promise<AdminUserLoginEventsResponse> {
  const limit = params?.limit ?? 50;
  const query = new URLSearchParams({ limit: String(limit) });
  return await apiGet<AdminUserLoginEventsResponse>(
    `/api/v1/admin/users/${userId}/login-events?${query.toString()}`,
  );
}
