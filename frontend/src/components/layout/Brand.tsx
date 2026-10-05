/* The supplied identity: sigil + wordmark lockup. Never substituted. */

interface BrandProps {
  compact?: boolean;
  large?: boolean;
}

export function Brand({ compact = false, large = false }: BrandProps) {
  if (large) {
    return (
      <div className="brand brand--large">
        <img src="/brand/istari-sigil.png" alt="" width={96} height={96} className="brand__sigil" />
        <img src="/brand/istari-wordmark.webp" alt="Istari" className="brand__wordmark" />
        <p className="brand__tagline">Knowledge, earned.</p>
      </div>
    );
  }
  return (
    <span className="brand">
      <img src="/brand/istari-sigil.png" alt="" width={28} height={28} className="brand__sigil" />
      {!compact && (
        <img src="/brand/istari-wordmark.webp" alt="Istari" className="brand__wordmark" />
      )}
      {compact && <span className="sr-only">Istari</span>}
    </span>
  );
}
