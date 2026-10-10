import fs from "fs";
import path from "path";

import type {
  Competition,
  CornerPoint,
  MatchFile,
  MatchIndex,
  RoutineCell,
  TeamRow,
} from "./types";

function readJson<T>(relative: string): T {
  const full = path.join(process.cwd(), "public", "data", relative);
  return JSON.parse(fs.readFileSync(full, "utf8")) as T;
}

export function getCompetition(): Competition {
  const file = readJson<{ competitions: Competition[] }>("competitions.json");
  return file.competitions[0];
}

export function getTeams(): { minTeamN: number; name: string; teams: TeamRow[] } {
  const file = readJson<{ name: string; min_team_n: number; teams: TeamRow[] }>(
    "teams/wc2022.json",
  );
  return { minTeamN: file.min_team_n, name: file.name, teams: file.teams };
}

export function getTeam(teamId: number): TeamRow | undefined {
  return getTeams().teams.find((team) => team.team_id === teamId);
}

export function getRoutines(): { minRoutineN: number; cells: RoutineCell[]; points: CornerPoint[] } {
  const file = readJson<{
    min_routine_n: number;
    cells: RoutineCell[];
    points: CornerPoint[];
  }>("routines/wc2022.json");
  return { minRoutineN: file.min_routine_n, cells: file.cells, points: file.points };
}

export function getMatchIndex(): { defaultMatchId: number; matches: MatchIndex[] } {
  const file = readJson<{ default_match_id: number; matches: MatchIndex[] }>(
    "matches/index.json",
  );
  return { defaultMatchId: file.default_match_id, matches: file.matches };
}

export function getMatch(matchId: number): MatchFile {
  return readJson<MatchFile>(`matches/${matchId}.json`);
}
