import { forwardJson, readBody } from "@/lib/api/forward";

// Staff side of a conversation: GET polls, POST replies as the store.
// FastAPI allows these endpoints only for ADMIN accounts.

export async function GET(
  request: Request,
  ctx: RouteContext<"/api/admin/support/[number]/messages">,
) {
  const { number } = await ctx.params;
  const afterId = Number(new URL(request.url).searchParams.get("after_id")) || 0;
  return forwardJson(
    `/admin/support/conversations/${encodeURIComponent(number)}/messages?after_id=${afterId}`,
  );
}

export async function POST(
  request: Request,
  ctx: RouteContext<"/api/admin/support/[number]/messages">,
) {
  const { number } = await ctx.params;
  const body = (await readBody(request)) as { body?: unknown } | undefined;
  if (!body || typeof body.body !== "string") {
    return Response.json(
      { detail: { code: "message_too_long", message: "This message is too long." } },
      { status: 422 },
    );
  }
  return forwardJson(`/admin/support/conversations/${encodeURIComponent(number)}/messages`, {
    method: "POST",
    body: { body: body.body },
  });
}
