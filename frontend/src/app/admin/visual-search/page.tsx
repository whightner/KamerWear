import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { ActiveBadge } from "@/components/admin/badges";
import { RebuildIndexButton } from "@/components/admin/RebuildIndexButton";
import { adminApi } from "@/lib/admin/api";
import { adminToken } from "@/lib/admin/page";
import { formatDateTime } from "@/lib/commerce/labels";

const ENCODER_STATE = {
  loaded: "Model loaded in the API",
  not_loaded: "Model loads on the first search or index update",
  failed: "Model failed to load (see server logs)",
};

function PathList({ title, paths, hint }: { title: string; paths: string[]; hint: string }) {
  if (paths.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-bold text-ink">
        {title} ({paths.length})
      </h3>
      <p className="text-xs text-muted">{hint}</p>
      {/* Scrollable, so it must be reachable with the keyboard. */}
      <ul
        tabIndex={0}
        aria-label={title}
        className="mt-2 max-h-48 overflow-y-auto rounded-lg bg-cream/60 p-2 font-mono text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-ink"
      >
        {paths.map((path) => (
          <li key={path} className="break-all py-0.5">
            {path}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function AdminVisualSearchPage() {
  const token = await adminToken("/admin/visual-search");
  if (!token) return null;
  const result = await adminApi.visualSearchStatus(token);
  if (!result.ok) return <AdminError what="the visual search status" />;
  const s = result.data;
  const pending = s.stale_images.length + s.unindexed_images.length;

  return (
    <>
      <AdminHeading
        title="Visual search"
        description="Customers' photos are compared with these indexed product photos. New or changed photos are only searchable after the index is updated."
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_380px] xl:items-start">
        <Panel title="Index status">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <ActiveBadge active={s.ready && pending === 0} label={s.ready ? (pending ? "Ready · update needed" : "Ready") : "Not ready"} />
            <span className="text-sm text-muted">Model: <span className="font-mono text-ink">{s.model}</span></span>
          </div>
          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div><dt className="text-muted">Indexed photos</dt><dd className="text-xl font-extrabold text-ink">{s.indexed_images} / {s.active_images}</dd></div>
            <div><dt className="text-muted">Products searchable</dt><dd className="text-xl font-extrabold text-ink">{s.products_represented} / {s.active_products}</dd></div>
            <div><dt className="text-muted">Need update</dt><dd className="text-xl font-extrabold text-ink">{pending}</dd></div>
            <div><dt className="text-muted">Missing files</dt><dd className="text-xl font-extrabold text-ink">{s.missing_files.length}</dd></div>
          </dl>
          <p className="mt-3 text-xs text-muted">{ENCODER_STATE[s.encoder_state]}.</p>
          {s.last_run && (
            <p className="mt-1 text-xs text-muted">
              Last update ({s.last_run.trigger}, {s.last_run.status}):{" "}
              {formatDateTime(s.last_run.finished_at ?? s.last_run.started_at)} · {s.last_run.indexed} encoded,{" "}
              {s.last_run.unchanged} unchanged, {s.last_run.removed} removed, {s.last_run.failed} failed.
            </p>
          )}
          <div className="mt-5 space-y-4">
            <PathList title="Not indexed yet" paths={s.unindexed_images} hint="New photos (e.g. added in the admin). Update the index to make them searchable." />
            <PathList title="Changed since indexing" paths={s.stale_images} hint="The file or path changed; search still uses the old version until the index is updated." />
            <PathList title="Files not found" paths={s.missing_files} hint="These paths don't exist in the web app's public/images/products folder." />
          </div>
        </Panel>
        <Panel title="Update the index">
          <RebuildIndexButton />
          <p className="mt-4 text-xs text-muted">
            Same as running <code className="font-mono">python -m app.ai.visual_search_index</code> on the server.
          </p>
        </Panel>
      </div>
    </>
  );
}
