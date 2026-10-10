"use client";

import { useRouter } from "next/navigation";

import type { MatchIndex } from "@/lib/types";

export function MatchPicker({
  matches,
  current,
}: {
  matches: MatchIndex[];
  current: number;
}) {
  const router = useRouter();
  return (
    <label className="picker">
      Match
      <select
        value={current}
        aria-label="Choose a match"
        onChange={(event) => router.push(`/match/${event.target.value}`)}
      >
        {matches.map((match) => (
          <option key={match.match_id} value={match.match_id}>
            {match.label} · {match.corners} corners
          </option>
        ))}
      </select>
    </label>
  );
}
