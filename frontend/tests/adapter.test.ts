import { describe, it, expect, vi, afterEach } from "vitest";
import { createDemo } from "../src/api/demo";
import {
  createAdapter,
  createHttpAdapter,
  requestFor,
} from "../src/api/client";
import {
  snapshotSchema,
  type Command,
  type Snapshot,
} from "../src/api/contracts";
import { scenarios } from "../src/api/fixtures";
function journey() {
  const adapter = createDemo(0);
  let s: Snapshot;
  const send = async (
    action: Command["action"],
    extra: Partial<Command> = {},
  ) => {
    s = await adapter.mutate({
      action,
      request_id: crypto.randomUUID(),
      expected_revision: s?.revision ?? 0,
      ...(s ? { session_id: s.session_id } : {}),
      ...extra,
    });
    return s;
  };
  return { adapter, send, get: () => s };
}
async function complete(j: ReturnType<typeof journey>) {
  await j.send("start");
  for (let i = 0; i < 6; i++) {
    const s = await j.send("select", {
      option_id: j.get().active_question!.options[i === 2 ? 2 : 0].option_id,
    });
    await j.send("confirm", {
      proposal_id: s.pending_proposal!.proposal_id,
      explicit_confirmation: true,
    });
  }
  return j.get();
}
afterEach(() => vi.unstubAllGlobals());
describe("provisional six-question adapter", () => {
  it("requires six separate confirmations and preserves confirmed Unsure in review", async () => {
    const j = journey();
    const s = await complete(j);
    expect(s.state).toBe("REVIEW");
    expect(s.confirmed_answers).toHaveLength(6);
    expect(s.review!.statements[2].is_unsure).toBe(true);
    const accepted = await j.send("finalize", {
      review_version: s.review_version!,
    });
    expect(accepted.receipt?.simulated).toBe(true);
    expect(accepted.receipt?.answers).toEqual(s.confirmed_answers);
  });
  it("rejects early save, foreign options, stale proposals and missing safety checks", async () => {
    const j = journey();
    await j.send("start");
    await expect(
      j.send("finalize", { review_version: "fake" }),
    ).rejects.toThrow();
    await expect(j.send("select", { option_id: "foreign" })).rejects.toThrow();
    await j.send("select", {
      option_id: j.get().active_question!.options[0].option_id,
    });
    await expect(j.send("confirm", { proposal_id: "stale" })).rejects.toThrow();
    for (let i = 0; i < 2; i++) {
      if (i)
        await j.send("select", {
          option_id: j.get().active_question!.options[0].option_id,
        });
      await j.send("confirm", {
        proposal_id: j.get().pending_proposal!.proposal_id,
      });
    }
    await j.send("select", {
      option_id: j.get().active_question!.options[0].option_id,
    });
    await expect(
      j.send("confirm", { proposal_id: j.get().pending_proposal!.proposal_id }),
    ).rejects.toThrow();
  });
  it("invalidates only the edited answer and old review, then requires reconfirmation", async () => {
    const j = journey();
    const s = await complete(j);
    const old = s.review_version;
    const corrected = await j.send("change", { question_id: "Q4" });
    expect(corrected.confirmed_answers).toHaveLength(5);
    expect(corrected.review_version).toBeNull();
    await j.send("select", {
      option_id: j.get().active_question!.options[1].option_id,
    });
    await j.send("confirm", {
      proposal_id: j.get().pending_proposal!.proposal_id,
      explicit_confirmation: true,
    });
    expect(j.get().review_version).not.toBe(old);
    await expect(
      j.send("finalize", { review_version: old! }),
    ).rejects.toThrow();
  });
  it("pause clears proposal, resume re-asks and end clears temporary answers and audit", async () => {
    const j = journey();
    await j.send("start");
    await j.send("select", {
      option_id: j.get().active_question!.options[0].option_id,
    });
    await j.send("pause");
    expect(j.get().pending_proposal).toBeNull();
    await j.send("resume");
    expect(j.get().state).toBe("ASKING");
    await j.send("end");
    expect(j.get().confirmed_answers).toEqual([]);
    expect((await j.adapter.audit(j.get().session_id)).events).toEqual([]);
  });
  it("pause from review invalidates review version and resume builds a new one", async () => {
    const j = journey();
    const old = (await complete(j)).review_version;
    await j.send("pause");
    expect(j.get().review_version).toBeNull();
    await j.send("resume");
    expect(j.get().review_version).not.toBe(old);
    expect(j.get().state).toBe("REVIEW");
  });
  it("refusal is incomplete, never silently converted to Unsure", async () => {
    const j = journey();
    await j.send("start");
    await j.send("message", { text: scenarios.refusal });
    expect(j.get().allowed_actions).toEqual(["pause", "end"]);
    expect(j.get().confirmed_answers).toEqual([]);
    expect(j.get().pending_proposal).toBeNull();
  });
  it("returns one receipt for duplicate acceptance and rejects conflicting request reuse", async () => {
    const j = journey();
    const s = await complete(j);
    const c: Command = {
      action: "finalize",
      session_id: s.session_id,
      request_id: "same",
      expected_revision: s.revision,
      review_version: s.review_version!,
    };
    const first = await j.adapter.mutate(c);
    expect(await j.adapter.mutate(c)).toEqual(first);
    await expect(
      j.adapter.mutate({ ...c, review_version: "changed" }),
    ).rejects.toThrow(/Conflicting/);
  });
  it("cancelled demo response cannot change state", async () => {
    const j = journey();
    await j.send("start");
    const before = j.get();
    const controller = new AbortController();
    controller.abort();
    await expect(
      j.adapter.mutate(
        {
          action: "message",
          session_id: before.session_id,
          request_id: "cancelled",
          expected_revision: before.revision,
          text: "Fictional reply",
        },
        controller.signal,
      ),
    ).rejects.toThrow();
    expect(await j.adapter.load(before.session_id)).toEqual(before);
  });
});
describe("versioned HTTP integration", () => {
  it("sends proposal/review IDs and expected revisions to spec routes", () => {
    expect(
      requestFor({
        action: "confirm",
        session_id: "s",
        request_id: "r",
        expected_revision: 4,
        proposal_id: "p",
        explicit_confirmation: true,
      }),
    ).toEqual({
      url: "/api/v1/sessions/s/confirmations",
      method: "POST",
      body: {
        request_id: "r",
        expected_revision: 4,
        proposal_id: "p",
        explicit_confirmation: true,
      },
    });
    expect(
      requestFor({
        action: "finalize",
        session_id: "s",
        request_id: "r",
        expected_revision: 12,
        review_version: "v",
      }).body,
    ).toEqual({ request_id: "r", expected_revision: 12, review_version: "v" });
    expect(
      requestFor({
        action: "end",
        session_id: "s",
        request_id: "r",
        expected_revision: 1,
      }).method,
    ).toBe("DELETE");
  });
  it("rejects malformed data, stale responses and simulated live receipts", async () => {
    const j = journey();
    const s = await complete(j);
    const http = createHttpAdapter();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({}) })),
    );
    await expect(http.load("s")).rejects.toThrow(/invalid/);
    const saved = await j.send("finalize", {
      review_version: s.review_version!,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => saved })),
    );
    await expect(http.load(saved.session_id)).rejects.toThrow(/simulated/);
    expect(
      snapshotSchema.safeParse({
        ...s,
        confirmed_answers: s.confirmed_answers.slice(1),
      }).success,
    ).toBe(false);
  });
  it("rejects catalog playback mismatches and a review that rewrites confirmed answers", async () => {
    const j = journey();
    await j.send("start");
    const p = await j.send("select", {
      option_id: j.get().active_question!.options[0].option_id,
    });
    expect(
      snapshotSchema.safeParse({
        ...p,
        pending_proposal: { ...p.pending_proposal, playback: "invented" },
      }).success,
    ).toBe(false);
    const k = journey();
    const s = await complete(k);
    s.review!.statements[0].playback = "invented";
    expect(snapshotSchema.safeParse(s).success).toBe(false);
  });
  it("handles timeouts and unavailable services without claiming success", async () => {
    const http = createHttpAdapter(5);
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url, init) =>
          new Promise((_resolve, reject) =>
            init.signal.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            ),
          ),
      ),
    );
    await expect(http.load("s")).rejects.toThrow(/too long/);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("offline");
      }),
    );
    await expect(http.load("s")).rejects.toThrow(/Unable/);
  });
});

describe("configuration and recovery", () => {
  it("does not treat unavailable evidence as proof that the session expired", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 404 })),
    );
    await expect(
      createHttpAdapter().audit("fictional-session"),
    ).rejects.toMatchObject({
      code: "ENDPOINT_UNAVAILABLE",
      message:
        "Evidence is unavailable. This does not mean your conversation has expired.",
    });
  });
  it("requires an explicit supported mode instead of silently using demo data", () => {
    expect(createAdapter("demo").mode).toBe("demo");
    expect(createAdapter("http").mode).toBe("http");
    expect(() => createAdapter("hptt")).toThrow(/mode is invalid/);
  });
  it.each([404, 410])(
    "marks missing/expired session responses as terminal (%s)",
    async (status) => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => ({ ok: false, status })),
      );
      const http = createHttpAdapter();
      await expect(http.load("expired-fictional")).rejects.toMatchObject({
        code: "SESSION_UNAVAILABLE",
        status,
      });
      await expect(
        http.mutate({
          action: "start",
          request_id: "fictional-start",
          expected_revision: 0,
        }),
      ).rejects.toMatchObject({ code: "ENDPOINT_UNAVAILABLE" });
    },
  );
  it("rejects a catalog change within a session", async () => {
    const j = journey();
    const original = await j.send("start");
    const http = createHttpAdapter();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => original })),
    );
    await http.load(original.session_id);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          ...original,
          catalog_version: "different-version",
          revision: 2,
        }),
      })),
    );
    await expect(http.load(original.session_id)).rejects.toMatchObject({
      code: "CATALOG_CHANGED",
    });
  });
});
