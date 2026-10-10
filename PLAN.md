# Football Corner Routines — build plan (prompt this file)

This is **not** the pitchboard, **not** the gegenpress clock, and **not** the game-state / scoreline project.

Paste this file into this repo and tell the agent:

> Follow `PLAN.md`. Start at Phase 0. Stop after each phase and show how to run it. Do not build pass maps, gegenpress windows, or winning/drawing/losing game state. Inspect a real StatsBomb corner (and a 360 freeze frame if the match has one) before writing SQL.

Repo name: **`football-corner-routines`**

Pitch (one paragraph): Corner routines, not corner counts. From StatsBomb open data, take each corner delivery, label how it was taken (short / inswing / outswing / straight), where the first contact is, whether a shot or a second ball follows, and — where 360 data exists — how the box was packed. The output is “this team’s corners look like this, and this pattern is the one that produces shots,” which a tally of corners cannot say.

---

## Context (do not ignore)

Builder: **Noor Sbeih** — backend/full-stack (Django, React/Next.js, Postgres), public portfolio for remote-first / Spain–EU roles.

Already shipped or planned:

- **Track A:** https://github.com/NoorSbeih/football-data-explorations  
  Shots, xG, and completed passes on a pitch. **Do not rebuild that.**
- **Gegenpress (separate repo):** eight seconds after losing the ball. **Do not rebuild that.**
- **Track B:** https://github.com/NoorSbeih/city-weather-pipeline  
  Reuse the habits: layers, idempotent rebuilds, SQL, mocked tests, CI, honest README.

This project is football analysis #3: **set pieces as sequences**. Coaches already know “they take a lot of corners.” The interesting part is the routine and the second ball.

Honest baseline: corners are rare (a team might have 4–8 per match). Tournament samples are small. Report counts next to every rate. Descriptive, not causal. Do not invent a predictive model in v1.

---

## The analytical question

When a team takes a corner, what do they actually do, and which of those patterns become a shot — including the second ball, not only the first contact?

Three numbers that are not “corners taken”:

1. **Routine mix** — share of corners that are short, inswinging, outswinging, or straight.
2. **First-contact zone** — near post, far post, penalty spot, six-yard, edge of the box, or short.
3. **Yield** — share of corners that produce a shot on the first contact, and share that produce a shot from the second ball, per delivery type.

Interview soundbite: “The pitchboard showed open-play shots. This one treats a corner as a short sequence: delivery, first contact, second ball, shot or clearance — and shows which routine a team repeats.”

---

## Locked stack (do not re-decide)

| Layer | Choice |
|---|---|
| Language | Python 3.11+, `src/` layout, `pyproject.toml`, ruff, pytest |
| Source | StatsBomb open data via `statsbombpy` (events). 360 freeze frames from the open-data 360 files where the match has them |
| Raw cache | Parquet (events) and JSON or Parquet (360) under `data/raw/` (**gitignored**) |
| Warehouse | **DuckDB** locally. SQL in `sql/` |
| Layers | `raw` → `staging` → `marts` |
| Orchestration | **Prefect 2.x**: extract → load → transform → export |
| Serving | **No always-on API.** JSON in `web/public/data/`. Static Next.js (App Router, TypeScript) on **Vercel free** |
| Pitch | One simple SVG pitch. Draw delivery end-point and first-contact zone. Do not import Track A components |
| Charts | One library only (Recharts or a small bar chart in SVG) |
| CI | GitHub Actions: ruff + pytest + `next lint` + `next build` |

**Do not add:** Kafka, Spark, paid cloud DB, an xG model, player scouting pages, pass networks, gegenpress windows, game-state scorelines.

---

## Data scope

v1: **FIFA World Cup 2022**.

Confirm competition and season IDs with `sb.competitions()` and store them in `config/competitions.yaml`.

WC 2022 is the right first tournament because StatsBomb published **360 data** for it (freeze frames: every player’s x/y at the event, plus teammate/actor flags). Not every open-data competition has 360. The pipeline must still run on events alone if a match has no 360 file.

Later (only after v1 is live): Euro 2024 or Women’s World Cup, if 360 or at least corner events exist. Do not block v1 on a second tournament.

---

## Definitions (lock with tests; verify field names on a real dump)

Write `docs/event-fields.md` in Phase 1 from one real corner-heavy match. Map the names you actually see. Do not guess.

### What is a corner

A **corner** is a `Pass` whose pass type is `Corner` (confirm the exact column: often `pass_type` or a nested pass object).

Keep, per corner:

- `match_id`, `period`, `index`, `timestamp_s` (seconds; do not use `minute` for ordering)
- attacking team, taker (`player`)
- side of the pitch: **left** or **right** corner. Derive from the pass start `y` (StatsBomb pitch is 120×80; the corner is at x≈120). Near the top touchline vs bottom. Document the rule after looking at real coordinates.
- `technique`: inswinging, outswinging, straight, or unknown — from pass technique. If the field is missing, technique = `unknown`, do not drop the corner.
- `end_x`, `end_y` of the pass (where it was aimed / where it arrived)
- `outcome`: complete or incomplete

### Short corner vs delivery into the box

Classify **before** zone-of-contact:

- **Short** if the pass is complete and the end location is outside the penalty box and close to the corner (rule to lock after seeing coordinates; a working start is `end_x < 102` or end within ~18 yards of the corner flag). Short corners are a routine, not a “failed cross.”
- **Delivery** otherwise (aimed into or across the box).

A short corner that is then crossed counts as **one corner sequence** whose delivery type is `short`, and the subsequent cross is the **second action**, not a new corner. Do not double-count.

### The corner sequence

The sequence starts at the corner pass and ends at the first of:

- a goal
- the ball goes dead (throw, goal kick, another corner, free kick, kick-off)
- possession is clearly settled in open play for **more than 8 seconds** after the first contact without a shot (tunable; store the cutoff in config)
- period ends

Events inside the sequence stay attached to that `corner_id`.

### First contact

The **first contact** is the first event after the corner pass that is an on-ball action by either team: a touch, header, shot, clearance, or the recipient controlling a complete pass.

- If the corner pass is incomplete and the next event is a defensive clearance or a header, that is the first contact.
- Zone of that contact, in the **attacking** frame (attacking goal at x = 120):

| Zone | Rule (attacking direction; confirm on a plot before trusting it) |
|---|---|
| `short` | the corner was classified short (contact is the layoff receiver, not a box zone) |
| `near_post` | inside the six-yard box, y on the **same** side as the corner flag |
| `far_post` | inside the six-yard box, y on the **opposite** side |
| `six_yard` | inside the six-yard box but not clearly near/far (central) |
| `penalty_spot` | inside the penalty box, outside the six-yard box, central corridor |
| `edge` | inside the penalty box, outside the six-yard box, wider than the central corridor |
| `recycled` | first contact outside the box (except a deliberate short corner) |

Six-yard box on a 120×80 pitch is approximately x ≥ 114 and 30 ≤ y ≤ 50. Penalty box is approximately x ≥ 102 and 18 ≤ y ≤ 62. **Plot ten real corners and fix these constants in one config file** if the dump shows different coordinates. Tests use the constants, not magic numbers in SQL.

### Outcomes

| Outcome | Rule |
|---|---|
| `shot_first` | a shot by the attacking team in the sequence **before** a second contact |
| `goal_first` | that shot is a goal |
| `second_ball_shot` | first contact is not a shot, then a shot by the attacking team still inside the sequence |
| `second_ball_goal` | that later shot is a goal |
| `cleared` | sequence ends with the ball leaving the box / going dead and no attacking shot |
| `short_then_cross` | delivery type `short` and a later pass in the sequence enters the box |

Shots in the sequence use StatsBomb `shot_statsbomb_xg` when present. Sum xG per corner. **Do not train an xG model.**

Own goals and deflections: if the shot outcome or a separate own-goal event benefits the attacking team inside the sequence, count it as a goal for the attacking team and test it once.

Ignore **period 5** (penalty shootout). A shootout is not a corner routine.

### 360 / freeze frames (only when the file exists)

For matches with 360 data, at the **corner event** (or, if the corner event has no frame, at the first shot in the sequence):

- Count attackers vs defenders inside the penalty box (`teammate` flag + location).
- Count players in the six-yard box.
- Store `box_attackers`, `box_defenders`, `six_yard_attackers`.
- If no frame: nulls, and `has_freeze_frame = false`. Never invent positions.

This is a **descriptor of the routine** (packed box vs sparse), not a tracking model.

### Headline metrics (per team, per competition)

Rates are **per corner**, with the count beside them.

| Metric | Definition |
|---|---|
| Corners | Count of corner sequences (short + delivery) |
| Short % | Short corners / corners |
| Inswing / outswing / straight % | Among **deliveries** (not shorts), share of each technique |
| First-contact zone mix | Share of deliveries whose first contact is near post, far post, penalty spot, edge |
| Shot % | Corners with `shot_first` or `second_ball_shot` / corners |
| First-contact shot % | `shot_first` / corners |
| Second-ball shot % | `second_ball_shot` / corners |
| xG per corner | Sum of sequence xG / corners |
| Goals | Count (show the raw number; do not rank on goals alone) |
| Box packing | Median `box_attackers` on corners that have a freeze frame; also report how many corners had no frame |

**The non-obvious cut:** shot % **by routine**, not overall. Example: “inswing to the near post, 18 corners, 7 shots” versus “outswing to the far post, 22 corners, 3 shots.” Hide a cell when that routine has **fewer than 8 corners**.

Sample size for a team page: show everyone, but do not rank a team on shot % if they have **fewer than 15 corners**.

### What not to claim

- A high shot % on 6 corners is noise. The UI must show N.
- Opponent marking quality is not in the event data. Freeze-frame counts are a proxy for packing, not for who was marked.
- xG on set pieces is noisy. Show it as a secondary number, not the title of the page.

---

## Warehouse model (DuckDB)

```
raw.matches
raw.events
raw.freeze_frames          one row per player per event that has a 360 frame
                           (match_id, event_uuid or index, x, y, teammate, actor)

staging.corners            one row per corner pass (not yet grouped)
staging.corner_sequences   one row per corner sequence:
                           corner_id, match_id, team, side, technique,
                           is_short, end_x, end_y,
                           first_contact_x, first_contact_y, first_contact_zone,
                           outcome, shot_xg, goals, has_freeze_frame,
                           box_attackers, box_defenders

marts.team_corners         team, competition, the headline rates, N
marts.team_routines        team, technique, first_contact_zone, N, shot %, xG per corner
marts.match_corners        match_id, list of sequences for the match tape
```

`CREATE OR REPLACE TABLE` — full rebuild, the data is small.

---

## Repo layout

```
football-corner-routines/
  PLAN.md
  pyproject.toml
  README.md
  LICENSE                          MIT, Noor Sbeih
  .gitignore                       data/raw, *.duckdb, .venv, node_modules, .next
  config/competitions.yaml
  config/pitch.yaml                box and six-yard constants, short-corner rule, sequence cutoff seconds
  src/corner_routines/
    config.py
    extract.py                     events → parquet; 360 → parquet; skip if cached
    load.py
    transform.py                   runs sql/ in order
    export.py                      marts → web/public/data/*.json
    flows.py                       Prefect
    cli.py                         `corner-routines build [--competition wc2022]`
  sql/
    staging/01_events.sql
    staging/02_corners.sql
    staging/03_sequences.sql
    marts/10_team_corners.sql
    marts/11_team_routines.sql
  tests/
    fixtures/                      tiny event lists, no network
    test_short_vs_delivery.py
    test_first_contact_zone.py
    test_second_ball.py
    test_freeze_frame_counts.py
  docs/event-fields.md             written in Phase 1 from a real dump
  web/                             Next.js App Router + TS
    public/data/                   committed JSON
  .github/workflows/ci.yml
```

---

## UI (thin)

WC 2022 only. Three views:

1. **Routine table** — teams as rows. Columns: corners, short %, inswing %, outswing %, shot %, second-ball shot %, xG per corner, N. Sort by shot % only among teams with enough corners. A footnote states the minimum N.
2. **Team routine** — one team. A pitch with first-contact dots coloured by outcome (shot / no shot), and a small table of technique × zone with N and shot %. Insufficient cells say “n too small,” they do not show a percentage.
3. **Match tape** — one match, each corner as a row: minute, side, technique or short, first-contact zone, outcome, xG. Default match: pick **after** looking at which match has the most corners, do not hardcode a story.

No player rankings in v1. No open-play shot map.

JSON:

- `competitions.json`
- `teams/wc2022.json`
- `routines/wc2022.json` (team × technique × zone, already filtered or flagged)
- `matches/{match_id}.json`

---

## Tests (no network)

Hand-built fixtures, using the same pitch constants as `config/pitch.yaml`:

- A pass with type Corner becomes one sequence.
- Inswinging vs outswinging vs missing technique (`unknown` is kept).
- End location near the corner flag → `short`; end location in the box → delivery.
- A short corner followed by a cross is **one** sequence, outcome `short_then_cross` if no shot, not two corners.
- First contact in the six-yard box on the same side as the flag → `near_post`; opposite side → `far_post`.
- Shot as the first on-ball action → `shot_first`. A header then a shot → `second_ball_shot`, not `shot_first`.
- Sequence ends when the next event is a goal kick; later shots are not credited to the corner.
- Period 5 produces no corners.
- Freeze frame with 4 attackers and 6 defenders inside the box → those counts; a corner with no frame → nulls, and team medians ignore it.
- A routine cell with 3 corners is flagged `reliable = false`.

If real StatsBomb names differ, fix the mapping and update the fixture to the real names. Do not weaken the tests to match a bug.

---

## CI

On push and pull request to `main`:

- `ruff check` and `ruff format --check`
- `pytest` (no live StatsBomb calls)
- `npm ci`, `npm run lint`, `npm run build` in `web/`

---

## Deploy

Vercel, static `web/`. Commit the generated JSON so the site does not need DuckDB at runtime. Put the live URL and a short GIF in the README. No paid database.

---

## Phases (stop after each)

### Phase 0 — scaffold

Layout, MIT license, `.gitignore`, `pyproject.toml`, empty package, Next.js hello page, CI, first commit.

**Done when:** CI is green on the skeleton.

### Phase 1 — extract, and write down the real fields

Cache WC 2022 events and 360 files. Load `raw`. Print match count, event count, and how many matches have 360.

From **one match that contains corners**, write `docs/event-fields.md`: the actual pass-type value for a corner, technique values, location columns, how a corner’s end point looks, and one freeze-frame row. Include a coordinate sketch note (which goal is x = 120).

**Done when:** a second build does not refetch, and the field note exists because you read the data.

### Phase 2 — corners and sequences

Implement short vs delivery, first-contact zone, and outcomes including the second ball. Run the unit tests.

Print tournament totals: corners, short %, shot %, second-ball shot %. If shot % is above ~50% or near 0, the sequence rules are wrong — fix them before any UI.

**Done when:** tests pass and the tournament rates are believable.

### Phase 3 — team and routine marts

`team_corners` and `team_routines` with the sample-size flags. Print the top routines by shot % among cells with N ≥ 8. Read them as a fan. If every team has the same mix, the zone constants are probably wrong — plot ten corners and fix `config/pitch.yaml`.

**Done when:** at least one routine difference is visible and you can explain it from the definitions.

### Phase 4 — export and UI

JSON export and the three views. Pitches use binned or per-corner points (a tournament of corners is small enough to send points).

**Done when:** a local build shows one team’s inswing vs outswing with N on the screen.

### Phase 5 — ship

README with the question, the sequence rules, the zone diagram, sample-size rules, and limitations. Deploy to Vercel. Record a short GIF of the team page.

**Done when:** the live URL is in the README and CI is green.

---

## README outline

1. The question, in one sentence, and the live link.
2. Why this is not a corner count and not a pass map.
3. How a sequence is cut: corner, short vs delivery, first contact, second ball, stop rules.
4. Zone diagram (near post, far post, penalty spot, edge).
5. What 360 is used for, and what happens when a match has no frame.
6. Sample sizes and what you refuse to rank.
7. Architecture: StatsBomb events + 360 → Parquet → DuckDB → JSON → Next.js.
8. How to run it locally.

---

## Definition of done (v1)

- [ ] Public repo, MIT license, method-first README
- [ ] WC 2022 corner sequences in DuckDB, including second-ball shots
- [ ] Tests for short corners, zones, second ball, shootouts, missing freeze frames
- [ ] Team table, team pitch, match tape, with N visible
- [ ] CI green
- [ ] Live Vercel URL

---

## Agent rules while building

- First commit early. One phase at a time.
- Do not copy the football-data-explorations UI.
- Do not implement gegenpress or scoreline game state.
- Read a real corner and a real 360 frame before writing the zone SQL.
- Keep pitch constants in `config/pitch.yaml` only.
- Never commit Parquet, raw 360 dumps, or the DuckDB file.
- There are no secrets in this project. Do not add any.

## How to run (target)

```bash
python -m venv .venv
pip install -e ".[dev]"
corner-routines build --competition wc2022
cd web && npm ci && npm run dev
```

The first build downloads StatsBomb data. Later builds use the cache.
