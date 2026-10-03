"use client";

import { useEffect, useState } from "react";

function secondsUntilMidnight(): number {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  return Math.floor((midnight.getTime() - now.getTime()) / 1000);
}

const pad = (value: number) => String(value).padStart(2, "0");

// Demo countdown to local midnight. It renders "--" on the server and fills in
// after hydration, so server and client HTML always match.
export function Countdown() {
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  useEffect(() => {
    const id = setInterval(() => setSecondsLeft(secondsUntilMidnight()), 1000);
    const first = setTimeout(() => setSecondsLeft(secondsUntilMidnight()), 0);
    return () => {
      clearInterval(id);
      clearTimeout(first);
    };
  }, []);

  const parts =
    secondsLeft === null
      ? ["--", "--", "--"]
      : [
          Math.floor(secondsLeft / 3600),
          Math.floor((secondsLeft % 3600) / 60),
          secondsLeft % 60,
        ].map(pad);

  const label =
    secondsLeft === null
      ? "Sale ends at midnight"
      : `Sale ends in ${parts[0]} hours ${parts[1]} minutes`;

  return (
    <div
      role="timer"
      aria-label={label}
      className="flex items-center gap-1 font-mono text-sm font-bold"
    >
      {parts.map((part, index) => (
        <span key={index} className="flex items-center gap-1">
          <span
            aria-hidden="true"
            className="min-w-8 rounded-md bg-ink px-1.5 py-1 text-center text-white"
          >
            {part}
          </span>
          {index < 2 && (
            <span aria-hidden="true" className="text-ink">
              :
            </span>
          )}
        </span>
      ))}
    </div>
  );
}
