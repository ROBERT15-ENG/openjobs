import Link from "next/link";

export default function NotFound() {
  return (
    <div className="empty-state">
      <h3>Page not found</h3>
      <p>The page you’re looking for doesn’t exist or has expired.</p>
      <p style={{ marginTop: "1.5rem" }}>
        <Link className="btn btn-primary" href="/">
          Browse jobs
        </Link>
      </p>
    </div>
  );
}
