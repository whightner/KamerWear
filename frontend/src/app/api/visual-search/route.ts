import { apiUrl } from "@/lib/api-config";

// Forwards the customer's photo to FastAPI so the browser only ever talks to
// the Next.js site. Nothing is stored: the file passes through in memory.
// FastAPI does the real validation (type, size, dimensions) and the search.

const MAX_BYTES = 8 * 1024 * 1024;

function error(status: number, code: string, message: string) {
  return Response.json({ detail: { code, message } }, { status });
}

export async function POST(request: Request) {
  const length = Number(request.headers.get("content-length") ?? "0");
  if (length > MAX_BYTES + 64 * 1024) {
    return error(413, "image_too_large", "The image is larger than 8 MB. Please use a smaller photo.");
  }
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return error(400, "invalid_image", "Choose an image to search with.");
  }
  const image = form.get("image");
  if (!(image instanceof File)) {
    return error(400, "invalid_image", "Choose an image to search with.");
  }
  if (image.size > MAX_BYTES) {
    return error(413, "image_too_large", "The image is larger than 8 MB. Please use a smaller photo.");
  }
  const limit = new URL(request.url).searchParams.get("limit") ?? "12";

  const upstream = new FormData();
  upstream.set("image", image, image.name || "photo");
  const headers: Record<string, string> = { Accept: "application/json" };
  // Lets the API rate-limit per browser (it trusts this header only from us).
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) headers["X-Forwarded-For"] = forwarded;

  let response: Response;
  try {
    response = await fetch(apiUrl(`/visual-search?limit=${encodeURIComponent(limit)}`), {
      method: "POST",
      body: upstream,
      headers,
      cache: "no-store",
    });
  } catch {
    return error(503, "unavailable", "We couldn't reach KamerWear right now. Please try again.");
  }
  const body = await response.json().catch(() => null);
  if (body === null) {
    return error(503, "visual_search_unavailable", "Visual search is unavailable right now.");
  }
  return Response.json(body, { status: response.status });
}
