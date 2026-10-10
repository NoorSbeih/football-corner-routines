export type Competition = {
  key: string;
  name: string;
  competition_id: number;
  season_id: number;
  default_match_id: number;
  min_team_n: number;
  min_routine_n: number;
};

export type TeamRow = {
  team_id: number;
  team: string;
  competition: string;
  corners: number;
  short_n: number;
  deliveries: number;
  inswing_n: number;
  outswing_n: number;
  straight_n: number;
  unknown_n: number;
  short_pct: number | null;
  inswing_pct: number | null;
  outswing_pct: number | null;
  straight_pct: number | null;
  shot_n: number;
  shot_pct: number | null;
  first_shot_n: number;
  first_shot_pct: number | null;
  second_shot_n: number;
  second_shot_pct: number | null;
  xg: number;
  xg_per_corner: number | null;
  goals: number;
  median_box_attackers: number | null;
  n_with_frame: number;
  rankable: boolean;
};

export type RoutineCell = {
  team_id: number;
  team: string;
  technique: string;
  zone: string;
  n: number;
  shot_n: number;
  shot_pct: number | null;
  xg_per_corner: number | null;
  goals: number;
  reliable: boolean;
};

export type CornerPoint = {
  team_id: number;
  team: string;
  match_id: number;
  technique: string;
  zone: string;
  outcome: string;
  shot: boolean;
  goals: number;
  end_x: number | null;
  end_y: number | null;
  first_contact_x: number | null;
  first_contact_y: number | null;
  side: string;
};

export type MatchIndex = {
  match_id: number;
  date: string;
  stage: string;
  label: string;
  corners: number;
  home_team_id: number;
  away_team_id: number;
};

export type TapeRow = {
  corner_id: string;
  period: number;
  minute: number;
  second: number;
  team: string;
  team_id: number;
  taker: string | null;
  side: string;
  technique: string;
  zone: string;
  outcome: string;
  xg: number;
  goals: number;
  shot: boolean;
  has_freeze_frame: boolean;
  box_attackers: number | null;
  box_defenders: number | null;
};

export type MatchFile = {
  match_id: number;
  date: string;
  stage: string;
  home_team: string;
  away_team: string;
  home_team_id: number;
  away_team_id: number;
  home_score: number;
  away_score: number;
  label: string;
  corners: TapeRow[];
};
