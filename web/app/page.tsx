import { TeamTable } from "./components/TeamTable";
import { getCompetition, getTeams } from "@/lib/data";

export default function HomePage() {
  const competition = getCompetition();
  const { teams, minTeamN } = getTeams();
  const corners = teams.reduce((sum, team) => sum + team.corners, 0);
  return (
    <div className="wrap">
      <h1>What the corner actually was</h1>
      <p className="lede">
        {competition.name}. {corners} corners, each kept as a short sequence: the delivery, the
        first contact, and the second ball. A count of corners cannot say which of those patterns
        produced a shot.
      </p>
      <p className="note">
        Rates sit next to their counts. xG is StatsBomb&apos;s number summed inside the sequence,
        not a model trained here. Freeze-frame packing is on the team page when a 360 frame exists.
      </p>
      <TeamTable teams={teams} minTeamN={minTeamN} />
    </div>
  );
}
