"""Combine all primary test rows (families A-D, W1-W4), compute Benjamini-Hochberg q-values over the 62 pre-registered
tests and classify each test with the PLAN.md criteria. Usability (criterion 4) needs judgement and is set in USABLE
below with a reason; the decay flag (not a PLAN criterion, reported for information) marks tests whose 2021-25 effect
has the opposite sign or less than a quarter of the MAIN magnitude. Writes results/ALL_classified.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mpstats import bh_fdr

FAMILIES = ['A', 'B', 'C', 'D', 'W1', 'W2', 'W3', 'W4']
PRIMARY = (['A1.%d' % i for i in range(1, 9)] + ['B%d' % i for i in range(1, 7)] + ['C%d' % i for i in range(1, 9)]
           + ['D%d' % i for i in range(1, 13)] + ['W1.%d' % i for i in range(1, 11)] + ['W2.%d' % i for i in range(1, 6)]
           + ['W3.%d' % i for i in range(1, 8)] + ['W4.%d' % i for i in range(1, 7)])
# criterion 4 (usability) with reason; tests not listed are judged by the generic rule in usable()
USABLE = {}


def usable(r):
    if r.test_id in USABLE:
        return USABLE[r.test_id]
    return (None, 'not judged yet')


def main():
    frames = []
    for f in FAMILIES:
        p = HERE / 'results' / f'{f}_tests.csv'
        if p.exists():
            frames.append(pd.read_csv(p))
    d = pd.concat(frames, ignore_index=True)
    d = d[d.test_id.isin(PRIMARY)].copy()
    missing = sorted(set(PRIMARY) - set(d.test_id))
    d['q_BH'] = bh_fdr(d.p_MAIN.values)
    d['c1_significant'] = (d.t_MAIN.abs() >= 3) & (d.q_BH <= .05)
    d['c2_stable'] = d.signs_P1_P4 >= 3
    d['c3_pre2018'] = d.pass_pre2018.astype(bool)
    u = d.apply(usable, axis=1)
    d['c4_usable'] = [x[0] for x in u]
    d['c4_reason'] = [x[1] for x in u]
    d['decayed_2021_25'] = (np.sign(d.eff_P4) != np.sign(d.eff_MAIN)) | (d.eff_P4.abs() < .25 * d.eff_MAIN.abs())

    def cls(r):
        if not r.c1_significant:
            return 'NOT_SUPPORTED'
        if not r.c2_stable:
            return 'REGIME_DEPENDENT'
        if not r.c3_pre2018:
            return 'NOT_ROBUST_TO_UNIVERSE'
        return 'ROBUST_USABLE' if r.c4_usable else 'ROBUST_NOT_USABLE_ALONE'
    d['class'] = d.apply(cls, axis=1)
    d.to_csv(HERE / 'results' / 'ALL_classified.csv', index=False)
    show = ['test_id', 'unit', 'eff_MAIN', 't_MAIN', 'q_BH', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
            'signs_P1_P4', 'decayed_2021_25', 'survivorship_risk', 'class']
    pd.set_option('display.width', 260)
    pd.set_option('display.max_rows', 100)
    print(d[show].round(3).to_string(index=False))
    print('missing primary tests:', missing)
    print(d['class'].value_counts().to_string())


if __name__ == '__main__':
    main()
