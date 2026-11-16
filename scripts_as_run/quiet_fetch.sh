#!/bin/sh
# Fetches the stratified quiet windows drawn by logs/quiet_draw.py (EXPLORATORY, outside
# the held-out protocol): for every set file probe, pull, catalog, validate and verify
# with ayzek_heldout's own tool, into ayzek_heldout/data/<set>/ beside the other sets.
# The windows lie in the held-out test periods; the method was frozen on 2026-10-30
# (release v1.0.0), hence --allow-test-period. One group at a time per service, the two
# groups in parallel (NOA and GeoNet are different services). A set whose directory
# already passes verify is kept.
#   sh logs/quiet_fetch.sh            (from ayzek_code/; logs: logs/quiet_fetch_<group>_2026-11-16.log)
set -u
CODE=$(cd "$(dirname "$0")/.." && pwd)
SEL=$CODE/data/runs/heldout_quietstrat
cd "$CODE/../ayzek_heldout" || exit 1
group() {
    g=$1; n=$(ls "$SEL/${g}_strat/sets"/*.toml | wc -l); i=0; ok=0; t0=$(date +%s)
    for f in "$SEL/${g}_strat/sets"/*.toml; do
        i=$((i + 1)); name=$(basename "$f" .toml)
        if [ -f "data/$name/dataset.json" ] && uv run --offline heldout verify "data/$name" > /dev/null 2>&1; then
            status=kept
        elif uv run --offline heldout probe "$f" && uv run --offline heldout pull "$f" --allow-test-period \
            && uv run --offline heldout catalog "$f" --allow-test-period \
            && uv run --offline heldout validate "$f" && uv run --offline heldout verify "data/$name"; then
            status=ok
        else
            status=FAILED
        fi
        [ "$status" != FAILED ] && ok=$((ok + 1))
        el=$(( $(date +%s) - t0 ))
        echo "$(date -u +%FT%TZ) $i/$n $name $status | elapsed $((el / 60)) min, ETA $(( el * (n - i) / i / 60 )) min"
    done
    echo "$(date -u +%FT%TZ) $g: $ok of $n sets fetched and verified"
    [ "$ok" -gt 0 ] && echo "$(date -u +%FT%TZ) DONE" || echo "$(date -u +%FT%TZ) NOTHING FETCHED"
}
group greece > "$CODE/logs/quiet_fetch_greece_2026-11-16.log" 2>&1 &
group nz > "$CODE/logs/quiet_fetch_nz_2026-11-16.log" 2>&1 &
wait
