import Image from "next/image";
import { t } from "@/lib/i18n";

/**
 * The league crest. It is decorative next to the wordmark, so the image itself
 * carries no alternative text and the lockup as a whole announces the league.
 */
export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand-lockup" role="img" aria-label="Văn Minh Fantasy League">
      <Image
        src="/vmf.png"
        alt=""
        width={44}
        height={44}
        className="brand-mark"
        priority
        sizes="44px"
      />
      {!compact && (
        <span className="brand-copy">
          <strong>VMF League</strong>
          <small>{t("brand.tagline")}</small>
        </span>
      )}
    </span>
  );
}
