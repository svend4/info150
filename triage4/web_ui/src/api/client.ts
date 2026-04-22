// Thin fetch wrapper with typed error handling.
//
// Base URL is relative by default so the Vite dev proxy (see
// web_ui/vite.config.ts) forwards every call to the FastAPI
// backend. Override via VITE_API_BASE at build time for production
// deployments where the frontend and backend live on different
// hosts.

import type { ApiError } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class BackendError extends Error {
  readonly status: number;
  readonly url: string;

  constructor(status: number, message: string, url: string) {
    super(message);
    this.status = status;
    this.url = url;
  }

  toApiError(): ApiError {
    return { status: this.status, message: this.message, url: this.url };
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : String(exc);
    throw new BackendError(0, `network: ${message}`, url);
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new BackendError(
      response.status,
      text || response.statusText || "request failed",
      url,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/plain")) {
    return (await response.text()) as unknown as T;
  }
  return (await response.json()) as T;
}

export function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { signal });
}

export function getText(path: string, signal?: AbortSignal): Promise<string> {
  return request<string>(path, { signal });
}

export { API_BASE };
