"""Assign the D06 IXI subjects to cohorts and charm workers (K1/K2), reproducibly.

Usage: python make_assignment.py AUDIT_CSV D05_IDS_TXT OUT_CSV

Rules (provisional, K1 as test custodian):
- Subjects shared with D05 are excluded from all use here (domain-robustness test set).
- Held out: 10 intact-face test + 5 calibration subjects, site-stratified, chosen only among scans whose T1
  touches no image edge except the inferior (neck) side. Pilot subjects stay in training.
- charm on held-out subjects is K1's; the training pool is split between K1 and K2, site-balanced.
"""
import csv
import random
import sys
from collections import defaultdict

SEED = 20261103
PILOTS = {"IXI045", "IXI095", "IXI294"}          # charm pilot (EXP-002), run by K1, training pool
HELD_OUT = {"Guys": (5, 2), "HH": (3, 2), "IOP": (2, 1)}  # site: (test_face, calibration)


def assign(audit_rows, d05_ids, seed=SEED):
    t1 = {r["subject"]: r for r in audit_rows if r["modality"] == "T1"}
    rows, by_site = [], defaultdict(list)
    for subject, r in sorted(t1.items()):
        if subject in d05_ids:
            rows.append({"subject": subject, "site": r["site"], "cohort": "excluded_d05", "owner": "-",
                         "note": "shared with D05; do not use"})
            continue
        clean = all(c == "ax1_lo" for c in r["edge_contact_axes"].split())
        by_site[r["site"]].append((subject, clean))
    rng = random.Random(seed)
    train = []
    for site in sorted(by_site):
        candidates = sorted(s for s, clean in by_site[site] if clean and s not in PILOTS)
        rng.shuffle(candidates)
        n_test, n_cal = HELD_OUT.get(site, (0, 0))
        held = {s: "test_face" for s in candidates[:n_test]}
        held.update({s: "calibration" for s in candidates[n_test:n_test + n_cal]})
        for subject, _ in by_site[site]:
            if subject in held:
                rows.append({"subject": subject, "site": site, "cohort": held[subject], "owner": "K1",
                             "note": "held out; never train on it"})
            else:
                train.append((site, subject))
    # Pilots are K1's; deal the rest per site alternately so both workers get every site.
    counts = {"K1": 0, "K2": 0}
    for site in sorted({s for s, _ in train}):
        subjects = [x for st, x in train if st == site]
        rest = sorted(x for x in subjects if x not in PILOTS)
        rng.shuffle(rest)
        for subject in sorted(x for x in subjects if x in PILOTS):
            rows.append({"subject": subject, "site": site, "cohort": "train", "owner": "K1", "note": "charm pilot"})
            counts["K1"] += 1
        for subject in rest:
            owner = min(counts, key=lambda k: (counts[k], k == "K1"))  # fewer first; ties go to K2
            counts[owner] += 1
            rows.append({"subject": subject, "site": site, "cohort": "train", "owner": owner, "note": ""})
    return sorted(rows, key=lambda r: r["subject"])


def main():
    audit, d05, out = sys.argv[1:4]
    with open(audit, newline="") as f:
        audit_rows = list(csv.DictReader(f))
    d05_ids = set(open(d05).read().split())
    rows = assign(audit_rows, d05_ids)
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "site", "cohort", "owner", "note"])
        writer.writeheader()
        writer.writerows(rows)
    summary = defaultdict(int)
    for r in rows:
        summary[(r["cohort"], r["owner"])] += 1
    for key in sorted(summary):
        print(*key, summary[key])


if __name__ == "__main__":
    main()
