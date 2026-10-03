import { forwardJson, readBody } from "@/lib/api/forward";

// The customer's conversation: GET polls for messages after `after_id`,
// POST sends a message. FastAPI checks that the conversation is theirs.

export async function GET(request: Request, ctx: RouteContext<"/api/support/[number]/messages">) {
  const { number } = await ctx.params;
  const afterId = Number(new URL(request.url).searchParams.get("after_id")) || 0;
  return forwardJson(
    `/support/conversations/${encodeURIComponent(number)}/messages?after_id=${afterId}`,
  );
}

export async function POST(request: Request, ctx: RouteContext<"/api/support/[number]/messages">) {
  const { number } = await ctx.params;
  const body = (await readBody(request)) as { body?: unknown } | undefined;
  if (!body || typeof body.body !== "string") {
    return Response.json(
      { detail: { code: "message_too_long", message: "This message is too long." } },
      { status: 422 },
    );
  }
  return forwardJson(`/support/conversations/${encodeURIComponent(number)}/messages`, {
    method: "POST",
    body: { body: body.body },
  });
}
