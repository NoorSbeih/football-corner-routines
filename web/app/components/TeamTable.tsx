import Link from "next/link";

import { pct, xg } from "@/lib/format";
import type { TeamRow } from "@/lib/types";

export function TeamTable({
  teams,
  minTeamN,
}: {
  teams: TeamRow[];
  minTeamN: number;
}) {
  const ranked = teams.filter((team) => team.rankable);
  const rest = teams.filter((team) => !team.rankable);
  return (
    <>
      <section>
        <h2>Ranked on shot rate</h2>
        <p className="note">
          Only teams with at least {minTeamN} corners. Inswing and outswing are shares of
          deliveries, after short corners are taken out.
        </p>
        <RateTable teams={ranked} caption={`Teams with ${minTeamN} or more corners.`} />
      </section>
      {rest.length > 0 ? (
        <section>
          <h2>Not ranked</h2>
          <p className="note">
            Fewer than {minTeamN} corners. The rate is still shown, next to the count, and it is
            not a ranking.
          </p>
          <RateTable teams={rest} caption="Teams below the ranking floor." />
        </section>
      ) : null}
    </>
  );
}

function RateTable({ teams, caption }: { teams: TeamRow[]; caption: string }) {
  return (
    <div className="table-wrap">
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th className="team" scope="col">
              Team
            </th>
            <th scope="col">Corners</th>
            <th scope="col">Short</th>
            <th scope="col">Inswing</th>
            <th scope="col">Outswing</th>
            <th scope="col">Shot</th>
            <th scope="col">Second ball</th>
            <th scope="col">xG / corner</th>
          </tr>
        </thead>
        <tbody>
          {teams.map((team) => (
            <tr key={team.team_id}>
              <td className="team">
                <Link href={`/team/${team.team_id}`}>{team.team}</Link>
              </td>
              <td>{team.corners}</td>
              <td>{pct(team.short_pct)}</td>
              <td>{pct(team.inswing_pct)}</td>
              <td>{pct(team.outswing_pct)}</td>
              <td>
                {pct(team.shot_pct)} <span className="small">({team.shot_n})</span>
              </td>
              <td>
                {pct(team.second_shot_pct)} <span className="small">({team.second_shot_n})</span>
              </td>
              <td>{xg(team.xg_per_corner)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
