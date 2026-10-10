# Event fields (FIFA World Cup 2022)

Written from the open-data cache, not from the documentation guesses.
Match used for the worked example: **3857254**, Denmark 0–0 Tunisia, 22 November 2022, 20 corners.
Tournament totals below are all 64 matches, periods 1–4.

## Corner

A corner is a `Pass` with `pass_type = 'Corner'`.

| Column | What it holds |
|---|---|
| `id` | Event UUID. This becomes `corner_id`. |
| `match_id`, `period`, `index` | Identity and order. `index` is the order key, not `minute`. |
| `timestamp` | Clock inside the period, `HH:MM:SS.mmm`. Period 2 resets toward `00:00`. |
| `minute`, `second` | Match clock, for the tape only. |
| `team`, `team_id`, `player`, `player_id` | The taking team and the taker. |
| `location` | JSON string `[x, y]`. Every corner starts on the goal line. |
| `pass_end_location` | JSON string `[x, y]` in the taker's frame. Where the pass arrived or was aimed. |
| `pass_outcome` | `NULL` means complete. Otherwise `Incomplete` (317), `Out` (8), or `Unknown` (7). |
| `pass_technique` | `Inswinging` (234), `Outswinging` (206), `Straight` (20), or null (109). |
| `pass_height` | `High Pass` on swung and straight corners. The null-technique corners are all `Ground Pass`. |
| `pass_inswinging`, `pass_outswinging`, `pass_straight` | Booleans that match `pass_technique`. The pipeline uses the name, not the flags. |
| `play_pattern` | `From Corner` on the corner itself and on the events that follow until the pattern changes. |

569 corners. None of them are in period 5. Period 5 is the shootout and is dropped in `staging.events`.

## Which goal is x = 120

StatsBomb stores every event in the frame of the team performing it. That team always attacks toward x = 120 on a 120 × 80 pitch. y = 0 is the bottom touchline, y = 80 the top.

Corner starts are only two points:

| Start | Count | Side |
|---|---|---|
| `[120.0, 80.0]` | 288 | `left` — the attacker's left, the high-y flag |
| `[120.0, 0.1]` | 281 | `right` — the attacker's right |

`side` is `left` when start y ≥ 40. The 0.1 instead of 0.0 is how the dump marks the bottom flag, still on the goal line.

The other team's next touch is **not** in that frame. Denmark's first corner ends at `[110.9, 37.0]`. Tunisia's clearance is stored at `[9.2, 43.1]`. Flipping it with `(120 − x, 80 − y)` lands on `[110.8, 36.9]`, the same spot as the pass. Zones use the flipped coordinate. Freeze frames on the corner event are already in the taker's frame, so those are not flipped.

```
y = 80   left flag (120, 80)
         | six-yard: x >= 114, y 30–50
         | penalty:  x >= 102, y 18–62
         | posts at y = 36 and y = 44
y = 0    right flag (120, 0.1)          goal line x = 120
```

Near post is the six-yard box on the flag's side of the goal (outside the posts). Far post is the opposite side. The strip between the posts is `six_yard`. Outside the six-yard box but inside the penalty box, the same central strip is `penalty_spot` and the wide channels are `edge`.

## Short vs delivery

Null technique and `Ground Pass` travel a median 11.7 yards (minimum 3.5). Inswinging and outswinging passes start at about 23 yards. The short rule is therefore: the pass is complete, the end point is outside the penalty box, and it is within **20 yards** of the flag. 20 sits in the gap between those two clusters. An incomplete pass that dies near the flag is a failed delivery, not a short corner.

A worked short corner from this match: Tunisia, index 2089, `[120.0, 0.1]` → `[116.3, 8.8]`, ground pass, 9.5 yards, technique null, recipient Anis Ben Slimane.

## What follows a corner

The first on-ball event after the corner is the first contact. On-ball types in this dump, in the six events after a corner: `Ball Receipt*`, `Pass`, `Carry`, `Clearance`, `Ball Recovery`, `Shot`, `Block`, `Miscontrol`, `Dribble`, `Dispossessed`, `Interception`, `50/50`, `Shield`, plus a goalkeeper punch / claim / sweep / smother / save.

Not a contact: `Pressure`, `Duel`, `Foul Committed`, `Shot Faced` (the keeper event that duplicates a shot already recorded).

Worked sequence, corner `cf306b75-1e23-40f4-a54e-369dc2ca5480`:

1. Pass, Corner, Inswinging, complete, end `[114.7, 29.6]`.
2. `Ball Receipt*` by Youssef Msakni at the same point.
3. `Shot` by Msakni, outcome `Off T`, `shot_statsbomb_xg = 0.043661`.
4. `Goal Keeper` / `Shot Faced` by Kasper Schmeichel.
5. `Pass` / `Goal Kick` — the sequence stops before this.

The receipt and the shot are the same player, so the shot is `shot_first`. The zone is `edge`: x is inside the six-yard depth, y = 29.6 is just outside the six-yard box (y ≥ 30) and wide of the goal.

A header (or any other player's touch) before the shot is `second_ball_shot`. `shot_outcome = 'Goal'` on that first shot is `goal_first`. A goal on a later shot is `second_ball_goal`.

`Own Goal For` is the event that benefits the attacking team (location already in their frame, three of them in the tournament, none from a corner in this reading). `Own Goal Against` is the paired event for the other side and is not counted again.

## 360

`sb.frames(match_id)` reads `data/three-sixty/{match_id}.json`. A missing file is HTTP 404; the pipeline writes an empty parquet and does not invent positions.

One frame:

```json
{
  "event_uuid": "520755b6-bb38-4271-932d-826ea2a910f6",
  "visible_area": [100.43, 68.80, 82.25, 57.31, 105.34, 0.0, 120.0, 0.0, 120.0, 47.37, 100.43, 68.80],
  "freeze_frame": [
    {"teammate": true, "actor": false, "keeper": false, "location": [94.19, 30.72]}
  ]
}
```

`teammate: true` means the taker's team, because the actor of a corner is the taker. On this straight corner the box holds 5 attackers and 9 defenders, with 1 attacker in the six-yard box. Only 8 of the 20 corners in match 3857254 have a frame on the corner event. The rest stay null unless the first shot in the sequence has a frame. Team medians ignore the nulls.
