"use client";

import { useEffect, useState } from "react";
import { formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";

function remaining(target: number, now: number) {
  const seconds = Math.max(0, Math.floor((target - now) / 1000));
  return {
    passed: seconds === 0,
    days: Math.floor(seconds / 86400),
    hours: Math.floor((seconds % 86400) / 3600),
    minutes: Math.floor((seconds % 3600) / 60),
    seconds: seconds % 60
  };
}

/**
 * How long until the squad locks.
 *
 * Before a Gameweek this is the only number a manager actually needs, and it
 * is the one thing a server-rendered page cannot express: "22 Aug, 00:30" is
 * a lookup, "in 4h 12m" is an answer. It renders the timestamp on the server
 * and upgrades to a ticking countdown once mounted, so it is never blank and
 * never disagrees with the clock.
 */
export function DeadlineCountdown({ deadline }: { deadline: string }) {
  const target = new Date(deadline).getTime();
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (now === null) {
    return (
      <div className="countdown" data-state="pending">
        <span className="countdown__label">{t("countdown.deadline")}</span>
        <strong className="countdown__static">{formatDateTime(deadline)}</strong>
      </div>
    );
  }

  const left = remaining(target, now);
  if (left.passed) {
    return (
      <div className="countdown" data-state="locked">
        <span className="countdown__label">{t("countdown.locked")}</span>
        <strong className="countdown__static">{t("countdown.lockedDetail")}</strong>
      </div>
    );
  }

  // Under an hour the seconds matter; before that they are just noise.
  const urgent = left.days === 0 && left.hours === 0;
  const parts: Array<[number, string]> = urgent
    ? [
        [left.minutes, t("countdown.minutes")],
        [left.seconds, t("countdown.seconds")]
      ]
    : left.days > 0
      ? [
          [left.days, t("countdown.days")],
          [left.hours, t("countdown.hours")],
          [left.minutes, t("countdown.minutes")]
        ]
      : [
          [left.hours, t("countdown.hours")],
          [left.minutes, t("countdown.minutes")],
          [left.seconds, t("countdown.seconds")]
        ];

  return (
    <div className="countdown" data-state={urgent ? "urgent" : "counting"}>
      <span className="countdown__label">{t("countdown.deadline")}</span>
      <span className="countdown__clock">
        {parts.map(([value, unit]) => (
          <span className="countdown__unit" key={unit}>
            <strong>{String(value).padStart(2, "0")}</strong>
            <small>{unit}</small>
          </span>
        ))}
      </span>
      <time className="countdown__at" dateTime={deadline}>
        {formatDateTime(deadline)}
      </time>
    </div>
  );
}
