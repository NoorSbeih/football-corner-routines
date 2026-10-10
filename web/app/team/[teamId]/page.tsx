import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { RoutineGrid } from "@/app/components/RoutineGrid";
import { RoutinePitch } from "@/app/components/RoutinePitch";
import { TechniqueBars } from "@/app/components/TechniqueBars";
import { getTeam, getTeams, getRoutines } from "@/lib/data";
import { pct, xg } from "@/lib/format";

export function generateStaticParams() {
  return getTeams().teams.map((team) => ({ teamId: String(team.team_id) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ teamId: string }>;
}): Promise<Metadata> {
  const { teamId } = await params;
  const team = getTeam(Number(teamId));
  return { title: team ? `${team.team} corners` : "Team" };
}

export default async function TeamPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  const team = getTeam(Number(teamId));
  if (!team) notFound();
  const { cells, points, minRoutineN } = getRoutines();
  const teamCells = cells.filter((cell) => cell.team_id === team.team_id);
  const teamPoints = points.filter((point) => point.team_id === team.team_id);
  return (
    <div className="wrap">
      <p className="note">
        <Link href="/">All teams</Link>
      </p>
      <h1>{team.team}</h1>
      <p className="lede">
        {team.rankable
          ? `${team.corners} corners, enough to sit in the shot-rate ranking.`
          : `${team.corners} corners. Shown with the count, and left out of the ranking (minimum 15).`}
      </p>
      <dl className="stats">
        <div>
          <dt>Shot</dt>
          <dd>
            {pct(team.shot_pct)} <span className="small">({team.shot_n})</span>
          </dd>
        </div>
        <div>
          <dt>First contact</dt>
          <dd>{pct(team.first_shot_pct)}</dd>
        </div>
        <div>
          <dt>Second ball</dt>
          <dd>
            {pct(team.second_shot_pct)} <span className="small">({team.second_shot_n})</span>
          </dd>
        </div>
        <div>
          <dt>xG / corner</dt>
          <dd>{xg(team.xg_per_corner)}</dd>
        </div>
        <div>
          <dt>Goals</dt>
          <dd>{team.goals}</dd>
        </div>
        <div>
          <dt>Box attackers</dt>
          <dd>
            {team.median_box_attackers ?? "—"}{" "}
            <span className="small">({team.n_with_frame} frames)</span>
          </dd>
        </div>
      </dl>
      <h2>Inswing against outswing</h2>
      <p className="note">
        Each bar is every corner of that delivery, zones pooled. The fraction under the rate is
        shots over corners.
      </p>
      <TechniqueBars points={teamPoints} />
      <h2>Where the first contact was</h2>
      <RoutinePitch team={team.team} points={teamPoints} />
      <h2>Delivery by zone</h2>
      <p className="note">
        Near post and far post are the six-yard box on the flag side and the far side. Between the
        posts is the six-yard centre. Further out, the middle of the penalty box is the penalty
        spot and the wide parts are the edge.
      </p>
      <RoutineGrid cells={teamCells} minN={minRoutineN} />
    </div>
  );
}
