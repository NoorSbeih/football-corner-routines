export function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toFixed(1)}%`;
}

export function xg(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(3);
}

export function countRate(count: number, total: number): string {
  return `${count}/${total}`;
}

const TECHNIQUE: Record<string, string> = {
  short: "Short",
  inswing: "Inswing",
  outswing: "Outswing",
  straight: "Straight",
  unknown: "Unmarked",
};

const ZONE: Record<string, string> = {
  short: "Short",
  near_post: "Near post",
  far_post: "Far post",
  six_yard: "Six-yard",
  penalty_spot: "Penalty spot",
  edge: "Edge",
  recycled: "Recycled",
  unknown: "No contact",
};

const OUTCOME: Record<string, string> = {
  shot_first: "Shot, first contact",
  goal_first: "Goal, first contact",
  second_ball_shot: "Shot, second ball",
  second_ball_goal: "Goal, second ball",
  short_then_cross: "Short, then cross",
  cleared: "Cleared",
};

const SIDE: Record<string, string> = {
  left: "Left",
  right: "Right",
};

export function techniqueLabel(value: string): string {
  return TECHNIQUE[value] ?? value;
}

export function zoneLabel(value: string): string {
  return ZONE[value] ?? value;
}

export function outcomeLabel(value: string): string {
  return OUTCOME[value] ?? value;
}

export function sideLabel(value: string): string {
  return SIDE[value] ?? value;
}

export function clock(minute: number, second: number): string {
  return `${minute}:${String(second).padStart(2, "0")}`;
}
