"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState
} from "react";
import { shortAgo } from "@/lib/format";
import { t } from "@/lib/i18n";

/**
 * How often a running Gameweek is re-read.
 *
 * The pipeline pulls FPL every five minutes and the server caches a response
 * for sixty seconds, so polling faster than this cannot surface a newer number
 * and only costs requests. Sixty seconds is the point where the page is never
 * more than one cache window behind what the database actually holds.
 */
const LIVE_INTERVAL_MS = 60_000;

interface LiveState {
  /** Increments on every refresh, for panels that hold their own fetched data. */
  tick: number;
  live: boolean;
  refreshedAt: number | null;
}

const LiveContext = createContext<LiveState>({ tick: 0, live: false, refreshedAt: null });

export function useLive(): LiveState {
  return useContext(LiveContext);
}

/**
 * Keeps a live Gameweek moving without the reader pressing reload.
 *
 * Scores are the reason this site exists, and a score that silently stops
 * updating is worse than no score at all: it looks current. This re-reads the
 * server-rendered page on a timer and publishes a tick so open squad panels,
 * which fetch their own detail, can follow.
 *
 * It only runs while a Gameweek is live. Outside one there is nothing to poll
 * for, and forty-six browsers asking anyway would be pure noise.
 */
export function LiveRefresh({
  live,
  intervalMs = LIVE_INTERVAL_MS,
  children
}: {
  live: boolean;
  intervalMs?: number;
  children: ReactNode;
}) {
  const router = useRouter();
  const [tick, setTick] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState<number | null>(null);
  const lastPulled = useRef(0);

  const pull = useCallback(() => {
    lastPulled.current = Date.now();
    setRefreshedAt(lastPulled.current);
    setTick((value) => value + 1);
    router.refresh();
  }, [router]);

  useEffect(() => {
    if (!live) return;

    const timer = window.setInterval(() => {
      // A backgrounded tab is not being read. Forty-six of them polling
      // through a Saturday afternoon is load that helps nobody.
      if (!document.hidden) pull();
    }, intervalMs);

    const onVisibilityChange = () => {
      // Coming back to a tab that sat hidden for a while should show the
      // current score at once, but flicking between tabs should not refetch
      // on every switch.
      if (document.hidden) return;
      if (Date.now() - lastPulled.current >= intervalMs) pull();
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [live, intervalMs, pull]);

  return (
    <LiveContext.Provider value={{ tick, live, refreshedAt }}>{children}</LiveContext.Provider>
  );
}

/**
 * Says that the page is keeping itself current, and how current it is.
 *
 * Without this the refresh is invisible, and a reader has no way to tell a
 * score that has not changed from a page that has stopped updating. The
 * relative time is rendered only after mount, so the server and the browser
 * cannot disagree about what "now" is.
 */
export function LiveIndicator() {
  const { live, refreshedAt } = useLive();
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    if (!live) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => window.clearInterval(timer);
  }, [live]);

  if (!live) return null;

  return (
    <div className="live-indicator" role="status" aria-live="polite">
      <span className="live-indicator__pulse" aria-hidden="true" />
      <span className="live-indicator__label">{t("live.autoUpdating")}</span>
      {refreshedAt !== null && now !== null && (
        <span className="live-indicator__time">
          {t("live.checked", { ago: shortAgo(now - refreshedAt) })}
        </span>
      )}
    </div>
  );
}
