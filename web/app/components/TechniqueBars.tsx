import type { CornerPoint } from "@/lib/types";
import { pct, techniqueLabel } from "@/lib/format";

const ORDER = ["inswing", "outswing", "straight", "short"] as const;

export function TechniqueBars({ points }: { points: CornerPoint[] }) {
  const groups = ORDER.map((technique) => {
    const rows = points.filter((point) => point.technique === technique);
    const shots = rows.filter((point) => point.shot).length;
    return {
      technique,
      n: rows.length,
      shots,
      rate: rows.length === 0 ? 0 : (100 * shots) / rows.length,
    };
  }).filter((group) => group.n > 0);

  if (groups.length === 0) {
    return <p className="note">No corners to compare.</p>;
  }

  return (
    <div className="bars" role="img" aria-label="Shot rate by delivery type, with the corner count">
      {groups.map((group) => (
        <div className="bar" key={group.technique}>
          <div className="bar-track" aria-hidden="true">
            <div className="bar-fill" style={{ height: `${Math.max(group.rate, 2)}%` }} />
          </div>
          <strong>{pct(Math.round(group.rate * 10) / 10)}</strong>
          <em>
            {group.shots}/{group.n}
          </em>
          <span className="name">{techniqueLabel(group.technique)}</span>
        </div>
      ))}
    </div>
  );
}
