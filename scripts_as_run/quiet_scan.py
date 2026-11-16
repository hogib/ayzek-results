"""Feasibility scan for a stratified quiet-window draw on Greece and New Zealand.
EXPLORATORY, outside the held-out protocol. No waveform is requested: only the event
catalogues of the two test periods are downloaded again (the selection kept the request
URLs and the event count, not the events), with ayzek_heldout's own catalogue code.

    uv run --offline --project ../ayzek_heldout python -u logs/quiet_scan.py OUT [--group greece nz]

For each selected sequence's station set of selections/<group>_now/selection.json it
counts where the protocol's quiet rule can be met at all: no catalogue event within
250 km of any station of the set from 30 min before a 6 h window to 30 min after it
(heldout/select.py, quiet_windows). Two passes, as the protocol: strict, and relaxed
(events below M2 farther than 100 km from every station are disregarded).
Station coverage is NOT checked here (the draw rejected 25 of 2,059 Greek draws for it).

Per set and pass: the number of event-free gaps of at least 7 h, the share of the
period's minutes at which a window could start (= the chance that one random draw on
this set is accepted), and the most windows of this set that fit without overlapping.

Writes OUT/<group>_events.json (the catalogue as downloaded, with the download time),
OUT/scan.csv, OUT/provenance.json; temp names, renamed at the end. One log line per
group and per set. Exits nonzero if nothing is produced.
"""
import argparse, csv, datetime as dt, hashlib, json, subprocess, sys, time
from pathlib import Path

HELDOUT = Path(__file__).resolve().parents[2] / "ayzek_heldout"
sys.path.insert(0, str(HELDOUT))
from heldout import networks, select  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--group", nargs="+", default=["greece", "nz"])
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
log = lambda m: print(f"{time.strftime('%FT%TZ', time.gmtime())} {m}", flush=True)
H7 = select.QUIET_LEN + 2 * select.QUIET_MARGIN
rows, prov = [], {"argv": sys.argv, "note": "exploratory, outside the held-out protocol; no waveform requested",
                  "rule": {"radius_km": select.SCORE_RADIUS_KM, "window_h": 6, "margin_min": 30,
                           "relaxed": [select.RELAX_BELOW_M, select.RELAX_BEYOND_KM]}, "groups": {}}

for g in a.group:
    sel = json.loads((HELDOUT / f"selections/{g}_now/selection.json").read_text())
    t0, t1 = (dt.datetime.fromisoformat(x) for x in sel["period"])
    nets, (glat, glon), gradius = select.GROUPS[g]
    info = networks.get(nets[0])
    cache = out / f"{g}_events.json"
    if cache.exists():
        ev = json.loads(cache.read_text()); log(f"{g}: catalogue from {cache} ({len(ev['events'])} events)")
    else:
        log(f"{g}: downloading the catalogue {t0:%F} to {t1:%F} in weekly requests")
        events, requests = select.group_catalogue(info, t0, t1, glat, glon, gradius + select.CATALOG_MARGIN_KM)
        ev = {"downloaded_utc": time.strftime('%FT%TZ', time.gmtime()), "requests": len(requests),
              "events": [select.event_json(e) for e in events]}
        tmp = cache.with_suffix(".tmp"); tmp.write_text(json.dumps(ev)); tmp.rename(cache)
        log(f"{g}: {len(events)} events in {len(requests)} requests (the selection saw {sel['catalogue']['events']})")
    E = [(dt.datetime.fromisoformat(e["time"]), e["lat"], e["lon"], e["magnitude"]) for e in ev["events"]]
    coord = {f"{s['network']}.{s['station']}": (s["lat"], s["lon"]) for s in sel["stations"]["usable"]}
    first, last = t0 + select.QUIET_MARGIN, t1 - select.QUIET_MARGIN - select.QUIET_LEN
    span_min = (last - first).total_seconds() / 60
    had = {}
    for w in sel["quiet"]["windows"]:
        had[w["sequence"]] = had.get(w["sequence"], 0) + 1
    prov["groups"][g] = {"events": len(E), "selection_events": sel["catalogue"]["events"],
                         "downloaded_utc": ev["downloaded_utc"], "period": sel["period"]}
    for q in sel["sequences"]:
        if not q.get("selected"):
            continue
        st = [coord[c] for c in q["stations"]]
        near = {False: [], True: []}
        for t, la, lo, m in E:
            d = min(select.km(sa, so, la, lo) for sa, so in st)
            if d > select.SCORE_RADIUS_KM:
                continue
            near[False].append(t)
            if not (m is not None and m < select.RELAX_BELOW_M and d > select.RELAX_BEYOND_KM):
                near[True].append(t)
        for relaxed in (False, True):
            ts = [t0 - H7] + near[relaxed] + [t1 + H7]
            gaps = starts = fit = 0
            for x, y in zip(ts, ts[1:]):
                # a window [s, s+6 h) is accepted when no event lies in [s-30 min, s+6 h 30 min)
                lo_, hi_ = max(x + select.QUIET_MARGIN, first), min(y - select.QUIET_LEN - select.QUIET_MARGIN, last)
                if hi_ <= lo_:
                    continue
                gaps += 1
                starts += (hi_ - lo_).total_seconds() / 60
                fit += int((hi_ - lo_) / select.QUIET_LEN) + 1
            rows.append({"group": g, "sequence": q["index"], "stations": len(st), "pass": "relaxed" if relaxed else "strict",
                         "events_within_250km": len(near[relaxed]), "gaps_ge_7h": gaps,
                         "accept_share": f"{starts / span_min:.5f}", "max_nonoverlapping_windows": fit,
                         "windows_in_protocol_draw": had.get(q["index"], 0)})
            log(f"{g} seq{q['index']:03d} {rows[-1]['pass']}: {len(near[relaxed])} events near, {gaps} gaps, "
                f"accept {starts / span_min:.4%}, fits {fit}")

if not rows:
    sys.exit("nothing produced")
tmp = out / "scan.csv.tmp"
with open(tmp, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
tmp.rename(out / "scan.csv")
prov["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
prov["heldout_commit"] = subprocess.run(["git", "-C", str(HELDOUT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
prov["written_utc"] = time.strftime('%FT%TZ', time.gmtime())
(out / "provenance.json").write_text(json.dumps(prov, indent=1))
log("DONE")
