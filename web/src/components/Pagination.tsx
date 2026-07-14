import Link from "next/link";

function pageWindow(page: number, pages: number): Array<number | "gap"> {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  const out: Array<number | "gap"> = [1];
  if (page > 3) out.push("gap");
  for (let p = Math.max(2, page - 1); p <= Math.min(pages - 1, page + 1); p++) {
    out.push(p);
  }
  if (page < pages - 2) out.push("gap");
  out.push(pages);
  return out;
}

export default function Pagination({
  page,
  pages,
  params,
}: {
  page: number;
  pages: number;
  params: Record<string, string>;
}) {
  if (pages <= 1) return null;

  function href(target: number): string {
    const p = new URLSearchParams(params);
    if (target <= 1) p.delete("page");
    else p.set("page", String(target));
    const qs = p.toString();
    return qs ? `/?${qs}` : "/";
  }

  return (
    <nav className="pagination" aria-label="Pagination">
      <Link
        className={page <= 1 ? "disabled" : ""}
        aria-disabled={page <= 1}
        aria-label="Previous page"
        href={href(page - 1)}
      >
        ←
      </Link>
      {pageWindow(page, pages).map((p, i) =>
        p === "gap" ? (
          <span key={`gap-${i}`} className="gap">
            …
          </span>
        ) : (
          <Link
            key={p}
            href={href(p)}
            className={p === page ? "active" : ""}
            aria-current={p === page ? "page" : undefined}
          >
            {p}
          </Link>
        ),
      )}
      <Link
        className={page >= pages ? "disabled" : ""}
        aria-disabled={page >= pages}
        aria-label="Next page"
        href={href(page + 1)}
      >
        →
      </Link>
    </nav>
  );
}
