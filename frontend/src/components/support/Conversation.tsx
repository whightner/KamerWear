"use client";

import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Send } from "lucide-react";
import { ensureSession } from "@/lib/auth/actions";
import { MESSAGE_MAX_LENGTH, POLL_INTERVAL_MS } from "@/lib/after-sales/labels";
import type {
  ConversationStatus,
  NewMessages,
  SenderRole,
  SupportMessage,
} from "@/lib/after-sales/types";

const timeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Africa/Douala",
});

interface ConversationProps {
  /** "customer" posts as the customer; "admin" replies as the store. */
  mode: "customer" | "admin";
  number: string;
  initialMessages: SupportMessage[];
  initialLastId: number;
  status: ConversationStatus;
}

/**
 * Message history + composer. While the page is open (and the tab visible) it
 * asks for messages newer than the last one it has, every few seconds; one
 * request at a time, and a failed poll keeps what is already shown.
 */
export function Conversation({ mode, number, initialMessages, initialLastId, status }: ConversationProps) {
  const router = useRouter();
  const own: SenderRole = mode === "customer" ? "customer" : "store";
  const endpoint = `${mode === "admin" ? "/api/admin/support" : "/api/support"}/${encodeURIComponent(number)}/messages`;
  const [messages, setMessages] = useState(initialMessages);
  const [currentStatus, setCurrentStatus] = useState(status);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const lastId = useRef(initialLastId);
  const statusRef = useRef(status);
  const polling = useRef(false);
  const listRef = useRef<HTMLOListElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const inputId = useId();
  const hintId = useId();

  const append = useCallback((incoming: SupportMessage[]) => {
    if (incoming.length === 0) return;
    setMessages((existing) => {
      const known = new Set(existing.map((m) => m.id));
      const fresh = incoming.filter((m) => !known.has(m.id));
      return fresh.length ? [...existing, ...fresh] : existing;
    });
    lastId.current = Math.max(lastId.current, ...incoming.map((m) => m.id));
  }, []);

  /** fetch through our route handler; renews an expired session once. */
  const request = useCallback(
    async (init?: RequestInit): Promise<Response | null> => {
      for (let attempt = 0; attempt < 2; attempt++) {
        const url = init?.method === "POST" ? endpoint : `${endpoint}?after_id=${lastId.current}`;
        const response = await fetch(url, { ...init, cache: "no-store" });
        if (response.status !== 401) return response;
        if (attempt === 0 && (await ensureSession())) continue;
        break;
      }
      router.push(`/login?next=${encodeURIComponent(window.location.pathname)}&reason=expired`);
      return null;
    },
    [endpoint, router],
  );

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;
    async function poll() {
      if (!polling.current && !document.hidden) {
        polling.current = true;
        try {
          const response = await request();
          if (response?.ok) {
            const data = (await response.json()) as NewMessages;
            const fromOthers = data.messages.filter((m) => m.sender_role !== own);
            append(data.messages);
            if (data.status !== statusRef.current) {
              statusRef.current = data.status;
              setCurrentStatus(data.status);
              router.refresh(); // header and close/reopen buttons follow
            }
            if (fromOthers.length) {
              const last = fromOthers[fromOthers.length - 1];
              setAnnouncement(`New message from ${last.sender_name}: ${last.body.slice(0, 120)}`);
            }
            setOffline(false);
          } else if (response) {
            setOffline(true);
          }
        } catch {
          setOffline(true); // keep the messages already shown
        } finally {
          polling.current = false;
        }
      }
      if (!stopped) timer = setTimeout(poll, POLL_INTERVAL_MS);
    }
    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [append, own, request, router]);

  // Keep the newest message in view.
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages.length]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const body = draft.trim();
    if (!body) {
      setError("Please write a message.");
      inputRef.current?.focus();
      return;
    }
    if (body.length > MESSAGE_MAX_LENGTH) {
      setError(`Messages can be at most ${MESSAGE_MAX_LENGTH} characters.`);
      return;
    }
    setSending(true);
    setError("");
    try {
      const response = await request({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      if (!response) return;
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        setError(data?.detail?.message ?? "Your message couldn't be sent. Please try again.");
        if (data?.detail?.code === "conversation_closed") setCurrentStatus("closed");
        return;
      }
      append([data as SupportMessage]);
      setDraft("");
      setAnnouncement("Message sent.");
    } catch {
      setError("Your message couldn't be sent. Check your connection and try again.");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  const closed = currentStatus === "closed";

  return (
    <div className="flex min-w-0 flex-col">
      <ol
        ref={listRef}
        aria-label="Messages"
        tabIndex={0}
        className="max-h-[60vh] min-h-48 space-y-3 overflow-y-auto rounded-xl border border-line bg-white p-3 outline-none focus-visible:ring-2 focus-visible:ring-ink sm:p-4"
      >
        {messages.map((message) => {
          const mine = message.sender_role === own;
          const store = message.sender_role === "store";
          return (
            <li
              key={message.id}
              className={`rounded-lg border-l-4 px-3 py-2 ${
                store ? "border-fit bg-fit-soft/60" : "border-sand bg-cream"
              } ${mine ? "sm:ml-10" : "sm:mr-10"}`}
            >
              <p className="flex flex-wrap items-baseline justify-between gap-x-3 text-xs">
                <span className="font-bold text-ink">
                  {message.sender_name}
                  {mine && <span className="font-normal text-muted"> (you)</span>}
                </span>
                <time dateTime={message.created_at} className="text-muted">
                  {timeFormat.format(new Date(message.created_at))}
                </time>
              </p>
              {/* Plain text: React escapes it; line breaks are kept. */}
              <p className="mt-1 whitespace-pre-wrap break-words text-sm text-ink">{message.body}</p>
            </li>
          );
        })}
      </ol>

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
      {offline && (
        <p role="status" className="mt-2 text-xs text-muted">
          Connection problem: new messages will appear when it&apos;s back.
        </p>
      )}

      {closed ? (
        <p className="mt-4 rounded-lg bg-sand px-4 py-3 text-sm text-ink">
          This conversation is closed. Reopen it to send another message.
        </p>
      ) : (
        <form onSubmit={submit} className="mt-4" noValidate>
          <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ink">
            {mode === "admin" ? "Reply as KamerWear support" : "Your message"}
          </label>
          <textarea
            ref={inputRef}
            id={inputId}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={3}
            maxLength={MESSAGE_MAX_LENGTH}
            aria-describedby={hintId}
            aria-invalid={error ? true : undefined}
            className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
            <p id={hintId} className="text-xs text-muted">
              {error ? (
                <span role="alert" className="font-medium text-deal-dark">
                  {error}
                </span>
              ) : (
                `Plain text, up to ${MESSAGE_MAX_LENGTH} characters (${draft.length}/${MESSAGE_MAX_LENGTH}).`
              )}
            </p>
            <button
              type="submit"
              disabled={sending}
              aria-busy={sending || undefined}
              className="inline-flex h-11 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black disabled:opacity-70"
            >
              {sending ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="size-4" aria-hidden="true" />
              )}
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
