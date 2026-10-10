import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { MatchPicker } from "@/app/components/MatchPicker";
import { MatchTape } from "@/app/components/MatchTape";
import { getMatch, getMatchIndex } from "@/lib/data";

export function generateStaticParams() {
  return getMatchIndex().matches.map((match) => ({ matchId: String(match.match_id) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ matchId: string }>;
}): Promise<Metadata> {
  const { matchId } = await params;
  const match = getMatch(Number(matchId));
  return { title: match.label };
}

export default async function MatchPage({ params }: { params: Promise<{ matchId: string }> }) {
  const { matchId } = await params;
  const id = Number(matchId);
  const { matches } = getMatchIndex();
  if (!matches.some((match) => match.match_id === id)) notFound();
  const match = getMatch(id);
  return (
    <div className="wrap">
      <p className="note">
        <Link href="/">All teams</Link>
      </p>
      <h1>{match.label}</h1>
      <p className="lede">
        {match.stage}, {match.date}. {match.corners.length}{" "}
        {match.corners.length === 1 ? "corner" : "corners"}. The list starts with the
        match that had the most.
      </p>
      <MatchPicker matches={matches} current={id} />
      <MatchTape rows={match.corners} />
    </div>
  );
}
