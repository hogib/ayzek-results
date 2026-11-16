"""Stratified quiet-window draw for Greece and New Zealand: the same number of windows
on every selected sequence's station set. EXPLORATORY, outside the held-out protocol;
the protocol's own 24 windows per network are not touched.

    uv run --offline --project ../ayzek_heldout python -u logs/quiet_draw.py SCAN OUT [--per-set 2]

SCAN is the output of logs/quiet_scan.py (the catalogues as downloaded for it). The rule,
fixed before the draw (user decision of 2026-11-15):
  - acceptance as the protocol's strict pass (heldout/select.py, quiet_windows): a 6 h
    window, no catalogue event within 250 km of any station of the set from 30 min before
    it to 30 min after it; every station's data cover 90 % of it (the protocol's coverage
    check, asked only for windows that pass the rest); no overlap in time with an accepted
    window that shares a station. Here also no overlap with a window of the protocol's own
    draw that shares a station, so that no data are used twice;
  - starts on the protocol's minute grid over the same period;
  - one random.Random(45) for the group; the sets are taken in sequence order; for each set
    the starts that satisfy the catalogue rule are shuffled and tried in that order until
    --per-set windows are accepted, the starts are exhausted, or --max-coverage-checks
    (500) coverage checks have been made for the set. This draws uniformly among the
    acceptable starts, as the protocol's rejection sampling does, without its limit of
    10,000 draws (the acceptance rate is 0.04 to 0.2 % on most sets);
  - a set that cannot be filled is recorded as short; nothing replaces it.

Writes OUT/<group>_strat/selection.json (the windows, per set the counts and why starts
were rejected) and OUT/<group>_strat/sets/<group>_strat_quietNN.toml in the format of
`heldout select`. One log line per set. Exits nonzero if no window is accepted.
"""
import argparse, datetime as dt, hashlib, json, math, random, subprocess, sys, time
from pathlib import Path

HELDOUT = Path(__file__).resolve().parents[2] / "ayzek_heldout"
sys.path.insert(0, str(HELDOUT))
from heldout import networks, select  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("scan"); ap.add_argument("out")
ap.add_argument("--per-set", type=int, default=2)
ap.add_argument("--seed", type=int, default=45)
ap.add_argument("--max-coverage-checks", type=int, default=500)
ap.add_argument("--group", nargs="+", default=["greece", "nz"])
a = ap.parse_args()
log = lambda m: print(f"{time.strftime('%FT%TZ', time.gmtime())} {m}", flush=True)
MIN = dt.timedelta(minutes=1)
total = 0
for g in a.group:
    sel = json.loads((HELDOUT / f"selections/{g}_now/selection.json").read_text())
    ev = json.loads((Path(a.scan) / f"{g}_events.json").read_text())
    t0, t1 = (dt.datetime.fromisoformat(x) for x in sel["period"])
    nets = select.GROUPS[g][0]
    info = networks.get(nets[0])
    covered = select.coverage_check(info, {})
    E = [(dt.datetime.fromisoformat(e["time"]), e["lat"], e["lon"]) for e in ev["events"]]
    usable = {f"{s['network']}.{s['station']}": s for s in sel["stations"]["usable"]}
    first = t0 + select.QUIET_MARGIN
    minutes = int((t1 - select.QUIET_MARGIN - select.QUIET_LEN - first).total_seconds() // 60)
    taken = [{"start": dt.datetime.fromisoformat(w["start"]), "end": dt.datetime.fromisoformat(w["end"]),
              "codes": set(w["stations"])} for w in sel["quiet"]["windows"]]      # the protocol's windows
    rng = random.Random(a.seed)
    windows, per_set = [], []
    for q in sel["sequences"]:
        if not q.get("selected"):
            continue
        stations = [usable[c] for c in q["stations"]]
        codes = set(q["stations"])
        near = sorted(t for t, la, lo in E
                      if min(select.km(s["lat"], s["lon"], la, lo) for s in stations) <= select.SCORE_RADIUS_KM)
        starts = []
        ts = [t0 - dt.timedelta(days=2)] + near + [t1 + dt.timedelta(days=2)]
        for x, y in zip(ts, ts[1:]):
            # accepted when no event e has start - 30 min <= e < start + 6 h 30 min
            lo = math.floor((x + select.QUIET_MARGIN - first) / MIN) + 1
            hi = math.floor((y - select.QUIET_LEN - select.QUIET_MARGIN - first) / MIN)
            starts.extend(range(max(lo, 0), min(hi, minutes - 1) + 1))
        n_valid = len(starts)
        rng.shuffle(starts)
        why = {"overlap": 0, "overlap with the protocol's windows": 0, "coverage": 0}
        got, checks = [], 0
        for m in starts:
            if len(got) >= a.per_set or checks >= a.max_coverage_checks:
                break
            start = first + m * MIN; end = start + select.QUIET_LEN
            if any(w["start"] < end and start < w["end"] and w["codes"] & codes for w in windows):
                why["overlap"] += 1; continue
            if any(w["start"] < end and start < w["end"] and w["codes"] & codes for w in taken):
                why["overlap with the protocol's windows"] += 1; continue
            checks += 1
            if not covered(stations, start, end):
                why["coverage"] += 1; continue
            w = {"start": start, "end": end, "stations": stations, "codes": codes, "sequence": q["index"],
                 "order": len(windows) + 1}
            got.append(w); windows.append(w)
        per_set.append({"sequence": q["index"], "stations": q["stations"], "acceptable_starts": n_valid,
                        "accepted": len(got), "short": len(got) < a.per_set, "coverage_checks": checks, "rejected": why})
        log(f"{g} seq{q['index']:03d}: {n_valid} acceptable starts, accepted {len(got)} of {a.per_set} "
            f"({checks} coverage checks; {why})")
    base = Path(a.out) / f"{g}_strat"; sets = base / "sets"; sets.mkdir(parents=True, exist_ok=True)
    tag = f"{g}_strat"
    for j, w in enumerate(windows, 1):
        lat, lon = select.centroid(w["stations"])
        r = max(select.km(lat, lon, s["lat"], s["lon"]) for s in w["stations"]) + 10.0
        (sets / f"{tag}_quiet{j:02d}.toml").write_text(select.set_toml(
            f"{tag}_quiet{j:02d}", nets, w["start"], w["end"], (lat, lon), r, w["stations"],
            f"logs/quiet_draw.py {g}: stratified quiet window {j} of {len(windows)}, exploratory, "
            f"on the stations of sequence {w['sequence']}"))
    record = {"group": g, "name": "strat", "note": "exploratory, outside the held-out protocol",
              "argv": sys.argv, "seed": a.seed, "per_set": a.per_set, "period": sel["period"],
              "catalogue": {"events": len(E), "downloaded_utc": ev["downloaded_utc"]},
              "sets": per_set,
              "quiet": {"windows": [{"start": w["start"].isoformat(), "end": w["end"].isoformat(),
                                     "sequence": w["sequence"], "order": w["order"],
                                     "stations": sorted(w["codes"])} for w in windows]},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "heldout_commit": subprocess.run(["git", "-C", str(HELDOUT), "rev-parse", "HEAD"],
                                               capture_output=True, text=True).stdout.strip(),
              "drawn_utc": time.strftime('%FT%TZ', time.gmtime())}
    tmp = base / "selection.json.tmp"; tmp.write_text(json.dumps(record, indent=1)); tmp.rename(base / "selection.json")
    log(f"{g}: {len(windows)} windows -> {sets}")
    total += len(windows)
if not total:
    sys.exit("no window accepted")
log("DONE")
