"""Full-period, zero-cost grid and matched one-lever comparisons."""
from itertools import product
from pathlib import Path
import json
import time
import numpy as np
import pandas as pd
import grid_search_timehunter as engine

OUT = Path(__file__).resolve().parent / 'timehunter_lever_results'
MEASURES = ['wr', 'pf', 'payout', 'mean', 'median', 'avg_win', 'avg_loss', 'n', 'worst']


def main():
    OUT.mkdir(exist_ok=True)
    started = time.monotonic()
    data, anomalies = engine.load_data('stocks')
    groups = engine.prepare(data)
    names = list(groups[0].signals)
    rows = []
    configs = list(product(engine.HOLDS, engine.DIPS, names))
    for ix, (hold, dip, entry) in enumerate(configs):
        chunks = [engine.simulate_group(g, hold, dip, entry)[0] for g in groups]
        r = np.concatenate(chunks)
        s = engine.metrics(r, 0)
        positive = r[r > 0].sum()
        negative = -r[r < 0].sum()
        s['pf'] = float(positive / negative) if negative else float('inf')
        s['tickers'] = sum(bool(len(x)) for x in chunks)
        rows.append(dict(hold=hold, fade='off' if dip is None else f'{dip:g}', entry=entry, **s))
        if (ix + 1) % 100 == 0:
            print(f'{ix+1}/{len(configs)} configurations; {time.monotonic()-started:.1f}s', flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(OUT / 'full_grid.csv', index=False)

    # Exact pairs: keep ALL other grid dimensions unchanged.
    comparisons = []
    for a, b in zip(engine.HOLDS[:-1], engine.HOLDS[1:]):
        comparisons.append(('hold', str(a), str(b), grid[grid.hold == a], grid[grid.hold == b], ['fade', 'entry']))
    for dip in engine.DIPS[1:]:
        key = f'{dip:g}'
        comparisons.append(('fade', 'off', key, grid[grid.fade == 'off'], grid[grid.fade == key], ['hold', 'entry']))
    for a, b in zip(engine.DIPS[1:-1], engine.DIPS[2:]):
        comparisons.append(('fade', f'{a:g}', f'{b:g}', grid[grid.fade == f'{a:g}'], grid[grid.fade == f'{b:g}'], ['hold', 'entry']))
    entry_pairs = [('always', 'trend_100'), ('trend_100', 'trend_100_dip_2'),
                   ('trend_100_dip_2', 'trend_100_rebound_2'),
                   ('trend_100_rebound_2', 'trend_200_rebound_2'),
                   ('trend_100_rebound_2', 'trend_100_rebound_5'),
                   ('always', 'breakout_20'), ('breakout_20', 'breakout_50')]
    for a, b in entry_pairs:
        comparisons.append(('entry', a, b, grid[grid.entry == a], grid[grid.entry == b], ['hold', 'fade']))
    paired = []
    for lever, a, b, before, after, keys in comparisons:
        pairs = before.merge(after, on=keys, suffixes=('_before', '_after'), validate='one_to_one')
        assert len(pairs) == len(before) == len(after)
        for metric in MEASURES:
            delta = pairs[metric + '_after'] - pairs[metric + '_before']
            paired.append(dict(lever=lever, before=a, after=b, metric=metric,
                               pairs=len(delta), median_delta=float(delta.median()),
                               mean_delta=float(delta.mean()), min_delta=float(delta.min()),
                               max_delta=float(delta.max()), fraction_up=float((delta > 1e-12).mean()),
                               fraction_down=float((delta < -1e-12).mean())))
    effects = pd.DataFrame(paired)
    effects.to_csv(OUT / 'matched_effects.csv', index=False)
    local = {
        'hold': grid[(grid.fade == '0.3') & (grid.entry == 'trend_100_rebound_2')].sort_values('hold'),
        'fade': grid[(grid.hold == 200) & (grid.entry == 'trend_100_rebound_2')],
        'entry': grid[(grid.hold == 200) & (grid.fade == '0.3')],
    }
    eligible = grid[(grid.n >= 200) & (grid.tickers >= 20)]
    tops = pd.concat([eligible.nlargest(5, m).assign(ranked_by=m) for m in ['wr', 'pf', 'mean']])
    tops.to_csv(OUT / 'top_configurations.csv', index=False)

    def table(df):
        lines = ['| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |',
                 '|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in df.itertuples():
            lines.append(f'| {r.hold} | {r.fade} | {r.entry} | {r.n} | {r.wr:.2%} | {r.pf:.3f} | {r.payout:.3f} | {r.mean:.2%} | {r.median:.2%} | {r.avg_win:.2%} | {r.avg_loss:.2%} | {r.worst:.2%} |')
        return '\n'.join(lines)

    report = ['# TimeHunter: pengaruh tuas pada periode gabungan',
              'Data saham harian 12 Juli 1994–15 Agustus 2025; 100 ticker; seluruh biaya nol. Fading dari Open bar berjalan; exit next tradable Open. Hold dihitung termasuk bar entry. Tidak memotong posisi pada batas 2014/2019.',
              f'Grid: {len(grid)} konfigurasi = {len(engine.HOLDS)} hold × {len(engine.DIPS)} fading × {len(names)} entry. Lolos lima kriteria numerik: {int((grid.numeric_passes == 5).sum())}. Ini pencarian in-sample, bukan validasi independen atau bukti tujuh kriteria.',
              'PF = jumlah return positif / absolut jumlah return negatif, dengan bobot notional entry sama per transaksi. Payout = rata-rata return positif / absolut rata-rata return negatif. PF ini bukan PF berbasis laba rupiah portofolio dengan ukuran posisi berubah. Mean adalah return per transaksi, bukan CAGR. Worst adalah transaksi terburuk, bukan maximum drawdown portofolio.',
              'Average loss ditampilkan sebagai magnitudo positif: makin kecil berarti kerugian rata-rata lebih kecil. Posisi akhir periode ditutup/ditandai sesuai engine sebelumnya; survivorship dan corporate action belum diverifikasi.']
    for name, subset in local.items():
        subset.to_csv(OUT / f'local_{name}.csv', index=False)
        report.extend([f'## Tuas {name}: dimensi lain tetap pada kandidat H200/fade30%/trend100-rebound2', table(subset)])
    report.extend(['## Perubahan berpasangan di seluruh grid',
                   'Delta = sesudah minus sebelum. Setiap pasangan hanya mengubah satu tuas. Median merangkum variasi konfigurasi, bukan estimasi kausal atau uji signifikansi. Persentase naik dihitung dari pasangan konfigurasi yang sangat berkorelasi.',
                   '| Tuas | Sebelum → sesudah | Metrik | Pasangan | Median delta | Proporsi naik |',
                   '|---|---|---|---:|---:|---:|'])
    for r in effects[effects.metric.isin(['wr', 'pf', 'mean'])].itertuples():
        delta = f'{r.median_delta * 100:+.2f} pp' if r.metric in ['wr', 'mean'] else f'{r.median_delta:+.3f}'
        report.append(f'| {r.lever} | {r.before} → {r.after} | {r.metric} | {r.pairs} | {delta} | {r.fraction_up:.1%} |')
    for metric in ['wr', 'pf', 'mean']:
        report.extend([f'## Lima konfigurasi tertinggi menurut {metric} (N >= 200, ticker >= 20)', table(tops[tops.ranked_by == metric])])
    (OUT / 'REPORT.md').write_text('\n\n'.join(report[:6]) + '\n' + '\n'.join(report[6:]), encoding='utf-8')
    meta = dict(configurations=len(grid), numeric_5of5=int((grid.numeric_passes == 5).sum()),
                rows=len(data), normalized_bars=len(anomalies), costs=0, full_period=True,
                elapsed_seconds=time.monotonic()-started)
    (OUT / 'summary.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta), flush=True)
    print(table(local['hold']), flush=True)
    print(table(local['fade']), flush=True)


if __name__ == '__main__':
    main()
