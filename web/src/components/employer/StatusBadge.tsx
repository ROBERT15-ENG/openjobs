export default function StatusBadge({ status }: { status: string }) {
  const key = status?.toLowerCase().replace(/[^a-z]/g, "") || "pending";
  return <span className={`status-badge status-${key}`}>{status}</span>;
}
