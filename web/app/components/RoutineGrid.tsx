import type { RoutineCell } from "@/lib/types";
import { pct, techniqueLabel, zoneLabel } from "@/lib/format";

const TECHNIQUES = ["inswing", "outswing", "straight", "unknown", "short"];
const ZONES = [
  "near_post",
  "far_post",
  "six_yard",
  "penalty_spot",
  "edge",
  "recycled",
  "short",
  "unknown",
];

export function RoutineGrid({ cells, minN }: { cells: RoutineCell[]; minN: number }) {
  const techniques = TECHNIQUES.filter((technique) =>
    cells.some((cell) => cell.technique === technique),
  );
  const zones = ZONES.filter((zone) => cells.some((cell) => cell.zone === zone));
  const lookup = new Map(cells.map((cell) => [`${cell.technique}:${cell.zone}`, cell]));

  return (
    <div className="table-wrap">
      <table>
        <caption>
          Shot rate by delivery and first-contact zone. A cell under {minN} corners says “n too
          small” instead of a percentage.
        </caption>
        <thead>
          <tr>
            <th className="team" scope="col">
              Delivery
            </th>
            {zones.map((zone) => (
              <th key={zone} scope="col">
                {zoneLabel(zone)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {techniques.map((technique) => (
            <tr key={technique}>
              <th className="team" scope="row">
                {techniqueLabel(technique)}
              </th>
              {zones.map((zone) => {
                const cell = lookup.get(`${technique}:${zone}`);
                if (!cell) return <td key={zone}>—</td>;
                return (
                  <td key={zone}>
                    {cell.reliable ? (
                      <>
                        {pct(cell.shot_pct)}{" "}
                        <span className="small">
                          ({cell.shot_n}/{cell.n})
                        </span>
                      </>
                    ) : (
                      <>
                        {cell.n} <span className="small">n too small</span>
                      </>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
