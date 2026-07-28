export default function Loading() {
  return (
    <div className="loading-page" role="status" aria-live="polite">
      <div className="loading-heading" />
      <div className="loading-subheading" />
      <div className="loading-grid">
        {[1, 2, 3, 4].map((item) => (
          <div className="loading-card" key={item} />
        ))}
      </div>
      <span className="sr-only">Đang tải dữ liệu…</span>
    </div>
  );
}
