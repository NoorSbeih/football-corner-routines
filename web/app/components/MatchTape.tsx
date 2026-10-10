import Link from "next/link";

import { clock, outcomeLabel, sideLabel, techniqueLabel, xg, zoneLabel } from "@/lib/format";
import type { TapeRow } from "@/lib/types";

export function MatchTape({ rows }: { rows: TapeRow[] }) {
  return (
    <div className="table-wrap">
      <table>
        <caption>Each row is one corner sequence. xG is the sum of StatsBomb xG inside it.</caption>
        <thead>
          <tr>
            <th className="team" scope="col">
              Time
            </th>
            <th className="team" scope="col">
              Team
            </th>
            <th scope="col">Side</th>
            <th className="team" scope="col">
              Delivery
            </th>
            <th className="team" scope="col">
              First contact
            </th>
            <th className="team" scope="col">
              Outcome
            </th>
            <th scope="col">xG</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.corner_id}>
              <td className="team">
                {clock(row.minute, row.second)}
                {row.period > 2 ? ` p${row.period}` : ""}
              </td>
              <td className="team">
                <Link href={`/team/${row.team_id}`}>{row.team}</Link>
              </td>
              <td>{sideLabel(row.side)}</td>
              <td className="team">{techniqueLabel(row.technique)}</td>
              <td className="team">{zoneLabel(row.zone)}</td>
              <td className="team">{outcomeLabel(row.outcome)}</td>
              <td>{xg(row.xg)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
