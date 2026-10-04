import {
  auditSchema,
  profileSchema,
  snapshotSchema,
  type Adapter,
  type Command,
} from "./contracts";
import { createDemo } from "./demo";
export class ServiceError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ServiceError";
  }
}
const paths = {
  message: "messages",
  select: "selections",
  confirm: "confirmations",
  change: "corrections",
  pause: "pause",
  resume: "resume",
  finalize: "finalize",
  explain_review: "messages",
};
export function requestFor(c: Command) {
  const base = "/api/v1/sessions";
  const body: Record<string, unknown> = {
    request_id: c.request_id,
    expected_revision: c.expected_revision,
  };
  if (c.action === "start") return { url: base, method: "POST", body };
  if (!c.session_id) throw Error("A session is required.");
  const session = `${base}/${encodeURIComponent(c.session_id)}`;
  if (c.action === "end") return { url: session, method: "DELETE", body };
  if (c.action === "message") body.text = c.text;
  if (c.action === "explain_review")
    body.text = "Please explain this review. I am not accepting it yet.";
  if (c.action === "select") body.option_id = c.option_id;
  if (c.action === "confirm") {
    body.proposal_id = c.proposal_id;
    body.explicit_confirmation = c.explicit_confirmation ?? false;
  }
  if (c.action === "change") body.question_id = c.question_id;
  if (c.action === "finalize") body.review_version = c.review_version;
  return { url: `${session}/${paths[c.action]}`, method: "POST", body };
}
export function createHttpAdapter(timeoutMs = 35000): Adapter {
  const catalogVersions = new Map<string, string>();
  async function request(
    url: string,
    signal?: AbortSignal,
    init: RequestInit = {},
  ) {
    const controller = new AbortController();
    let timeout = false;
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();
    const timer = setTimeout(() => {
      timeout = true;
      controller.abort();
    }, timeoutMs);
    try {
      const response = await fetch(url, {
        ...init,
        signal: controller.signal,
        cache: "no-store",
        credentials: "same-origin",
      });
      if (!response.ok) {
        if (response.status === 409)
          throw Error(
            "The session changed. Refresh its state before continuing.",
          );
        if (response.status === 404 || response.status === 410) {
          const evidenceRequest = url.endsWith("/audit");
          const sessionRequest =
            url.startsWith("/api/v1/sessions/") && !evidenceRequest;
          throw new ServiceError(
            sessionRequest
              ? "This session is no longer available. You can return to the start screen. A save already sent to the service may have completed."
              : evidenceRequest
                ? "Evidence is unavailable. This does not mean your conversation has expired."
                : "The requested service endpoint is unavailable. Check the backend configuration.",
            sessionRequest ? "SESSION_UNAVAILABLE" : "ENDPOINT_UNAVAILABLE",
            response.status,
          );
        }
        if (response.status === 422)
          throw Error(
            "The service could not accept that action. Refresh the session to review your options.",
          );
        throw Error(
          "The conversation service is unavailable. Retry or refresh the session.",
        );
      }
      try {
        return await response.json();
      } catch {
        throw Error(
          "The service returned unreadable data. No result is confirmed.",
        );
      }
    } catch (e) {
      if (timeout)
        throw Error(
          "The service took too long. Retry the same request safely, or refresh the session to check its outcome.",
        );
      if (e instanceof TypeError)
        throw Error(
          "Unable to reach the service. Check the backend and retry.",
        );
      throw e;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
    }
  }
  const snapshot = (value: unknown, sessionId?: string) => {
    const result = snapshotSchema.safeParse(value);
    if (!result.success || (sessionId && result.data.session_id !== sessionId))
      throw Error(
        "The service returned an invalid session. No result is confirmed.",
      );
    if (result.data.receipt?.simulated)
      throw Error(
        "The connected service returned a simulated receipt. Saving is not confirmed.",
      );
    if (result.data.receipt && result.data.catalog_status !== "approved")
      throw Error(
        "The service returned a saved profile using an unapproved catalog. Saving cannot be verified.",
      );
    const pinned = catalogVersions.get(result.data.session_id);
    if (pinned && pinned !== result.data.catalog_version)
      throw new ServiceError(
        "The catalog version changed during this session. Its answers cannot be safely continued; return to the start screen. A save already sent may have completed.",
        "CATALOG_CHANGED",
      );
    catalogVersions.set(result.data.session_id, result.data.catalog_version);
    return result.data;
  };
  return {
    mode: "http",
    async mutate(c, signal) {
      const r = requestFor(c);
      const s = snapshot(
        await request(r.url, signal, {
          method: r.method,
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": c.request_id,
          },
          body: JSON.stringify(r.body),
        }),
        c.session_id,
      );
      if (s.revision <= c.expected_revision)
        throw Error(
          "The service returned an outdated result. Refresh the session.",
        );
      return s;
    },
    async load(id, signal) {
      return snapshot(
        await request(`/api/v1/sessions/${encodeURIComponent(id)}`, signal),
        id,
      );
    },
    async audit(id, signal) {
      const r = auditSchema.safeParse(
        await request(
          `/api/v1/sessions/${encodeURIComponent(id)}/audit`,
          signal,
        ),
      );
      if (!r.success || r.data.session_id !== id)
        throw Error("The evidence response is invalid.");
      return r.data;
    },
    async profile(id, sessionId, signal) {
      const r = profileSchema.safeParse(
        await request(`/api/v1/profiles/${encodeURIComponent(id)}`, signal),
      );
      if (
        !r.success ||
        r.data.profile_id !== id ||
        r.data.session_id !== sessionId ||
        r.data.simulated
      )
        throw Error("The accepted-profile response is invalid.");
      return r.data;
    },
  };
}
export function createAdapter(
  mode = import.meta.env.VITE_API_MODE ?? "http",
): Adapter {
  if (mode === "demo") return createDemo();
  if (mode === "http") return createHttpAdapter();
  throw new ServiceError(
    "Frontend mode is invalid. Set VITE_API_MODE to demo or http, then restart Vite.",
    "INVALID_CONFIGURATION",
  );
}
