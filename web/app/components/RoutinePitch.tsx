import type { CornerPoint } from "@/lib/types";
import { techniqueLabel, zoneLabel } from "@/lib/format";

const X_MIN = 78;
const X_MAX = 120;
const Y_MAX = 80;
const SCALE = 4.5;
const TOP = 16;
const SIDE = 12;
const BOTTOM = 10;

function sx(y: number): number {
  return SIDE + (Y_MAX - y) * SCALE;
}

function sy(x: number): number {
  return TOP + (X_MAX - x) * SCALE;
}

const WIDTH = SIDE * 2 + Y_MAX * SCALE;
const HEIGHT = TOP + (X_MAX - X_MIN) * SCALE + BOTTOM;
const YARD = SCALE;

function inside(x: number | null, y: number | null): x is number {
  return x != null && y != null && x >= X_MIN && x <= X_MAX && y >= 0 && y <= Y_MAX;
}

export function RoutinePitch({
  team,
  points,
}: {
  team: string;
  points: CornerPoint[];
}) {
  const shots = points.filter((point) => point.shot).length;
  const offFrame = points.filter(
    (point) => !inside(point.first_contact_x, point.first_contact_y),
  ).length;
  return (
    <figure className="pitch-block">
      <svg
        className="pitch"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`${team}: ${shots} of ${points.length} corners produced a shot. Dots are first contacts in the attacking third.`}
      >
        <line className="pitch-line" x1={sx(80)} y1={sy(120)} x2={sx(0)} y2={sy(120)} />
        <line className="pitch-line" x1={sx(80)} y1={sy(120)} x2={sx(80)} y2={sy(X_MIN)} />
        <line className="pitch-line" x1={sx(0)} y1={sy(120)} x2={sx(0)} y2={sy(X_MIN)} />
        <rect
          className="pitch-goal"
          x={sx(44)}
          y={sy(120) - 2 * YARD}
          width={8 * YARD}
          height={2 * YARD}
        />
        <rect
          className="pitch-line"
          x={sx(62)}
          y={sy(120)}
          width={(62 - 18) * SCALE}
          height={(120 - 102) * SCALE}
        />
        <rect
          className="pitch-line"
          x={sx(50)}
          y={sy(120)}
          width={(50 - 30) * SCALE}
          height={(120 - 114) * SCALE}
        />
        <path
          className="pitch-line"
          d={`M ${sx(48)} ${sy(102)} A ${10 * YARD} ${10 * YARD} 0 0 1 ${sx(32)} ${sy(102)}`}
        />
        <circle className="pitch-spot" cx={sx(40)} cy={sy(108)} r={1.5} />
        <path
          className="pitch-line"
          d={`M ${sx(79)} ${sy(120)} A ${YARD} ${YARD} 0 0 1 ${sx(80)} ${sy(119)}`}
        />
        <path
          className="pitch-line"
          d={`M ${sx(1)} ${sy(120)} A ${YARD} ${YARD} 0 0 0 ${sx(0)} ${sy(119)}`}
        />
        {points.map((point, index) =>
          inside(point.end_x, point.end_y) ? (
            <circle
              key={`end-${index}`}
              className="end-mark"
              cx={sx(point.end_y as number)}
              cy={sy(point.end_x as number)}
              r={5}
            />
          ) : null,
        )}
        {points.map((point, index) => {
          if (!inside(point.first_contact_x, point.first_contact_y)) return null;
          const goal = point.goals > 0;
          const className = goal ? "dot-goal" : point.shot ? "dot-shot" : "dot-quiet";
          return (
            <circle
              key={`contact-${index}`}
              className={className}
              cx={sx(point.first_contact_y as number)}
              cy={sy(point.first_contact_x as number)}
              r={4.5}
            >
              <title>
                {techniqueLabel(point.technique)}, {zoneLabel(point.zone)}
                {point.shot ? ", shot" : ", no shot"}
              </title>
            </circle>
          );
        })}
      </svg>
      <figcaption className="note">
        Goal line at the top. Left side of the picture is the attacker&apos;s left flag. Open
        rings are where the corner was aimed. Filled dots are the first contact.
        {offFrame > 0
          ? ` ${offFrame} first ${offFrame === 1 ? "contact was" : "contacts were"} outside this frame.`
          : ""}
      </figcaption>
      <div className="legend">
        <span>
          <i className="swatch ring" aria-hidden="true" /> Delivery end
        </span>
        <span>
          <i className="swatch" aria-hidden="true" /> No shot
        </span>
        <span>
          <i className="swatch shot" aria-hidden="true" /> Shot or goal
        </span>
      </div>
    </figure>
  );
}
