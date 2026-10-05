/* Thin fetch wrapper: same-origin cookies, CSRF header on writes, typed errors.
   The CSRF token lives in memory only (set after login / `GET /api/me`). */

export interface ErrorBody {
  error: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string;

  constructor(status: number, body: ErrorBody | null) {
    super(body?.message ?? `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.error ?? "http_error";
    this.details = body?.details ?? {};
    this.requestId = body?.request_id ?? "-";
  }
}

let csrfToken: string | null = null;
let onUnauthenticated: (() => void) | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function setUnauthenticatedHandler(handler: (() => void) | null): void {
  onUnauthenticated = handler;
}

const WRITE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (WRITE_METHODS.has(method) && csrfToken) headers["X-CSRF-Token"] = csrfToken;

  const init: RequestInit = { method, headers, credentials: "same-origin" };
  if (options.body !== undefined) init.body = JSON.stringify(options.body);
  if (options.signal) init.signal = options.signal;
  const response = await fetch(path, init);

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null;
    if (response.status === 401 && onUnauthenticated) onUnauthenticated();
    throw new ApiError(response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function isApiError(error: unknown, status?: number): error is ApiError {
  return error instanceof ApiError && (status === undefined || error.status === status);
}

export function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 12)}`;
}
