export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand-lockup" role="img" aria-label="Văn Minh Fantasy League">
      <svg className="brand-mark" viewBox="0 0 44 44" aria-hidden="true">
        <path
          d="M4 6.5 12.5 37h6.4L22 25.8 25.1 37h6.4L40 6.5h-7.8l-4 17.1L24 9.2h-4l-4.2 14.4-4-17.1H4Z"
          fill="currentColor"
        />
        <path d="M8 5h28" stroke="var(--coral)" strokeWidth="2.5" />
      </svg>
      {!compact && (
        <span className="brand-copy">
          <strong>VMF League</strong>
          <small>Văn Minh Fantasy</small>
        </span>
      )}
    </span>
  );
}
