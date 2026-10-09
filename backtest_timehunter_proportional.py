"""Shrink TimeHunter horizons proportionally; keep execution unchanged."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine

OUT = Path(__file__).resolve().parent / 'timehunter_proportional_results'


def signal(frame, sma, window, depth):
    c = frame.Close
    condition = ((c > c.rolling(sma).mean()) &
                 (1 - c / frame.High.rolling(window).max() >= depth) &
                 (c > c.shift(1)))
    return condition.shift(1, fill_value=False).to_numpy(bool)


def main():
    OUT.mkdir(exist_ok=True)
    df, _ = engine.load_data('stocks')
    # Integer windows preserve exactly H:SMA:High-window = 10:5:1.
    configs = []
    for mode in ['time_only', 'time_and_thresholds']:
        for window in range(20, 0, -1):
            scale = window / 20
            configs.append(dict(mode=mode, scale=scale, hold=10*window,
                                sma=5*window, high_window=window,
                                pullback=.02 if mode == 'time_only' else .02*scale,
                                fade=.30 if mode == 'time_only' else .30*scale))
    groups = engine.prepare(df, dips=sorted({c['fade'] for c in configs}))
    frames = {str(k): f.reset_index(drop=True) for k, f in df.groupby('Ticker', sort=True)}
    rows = []
    for cfg in configs:
        records = []
        chunks = []
        for g in groups:
            s = signal(frames[g.ticker], cfg['sma'], cfg['high_window'], cfg['pullback'])
            n = len(s)
            g.next_entry['scaled'] = np.minimum.accumulate(np.where(s, np.arange(n), n)[::-1])[::-1]
            if cfg['scale'] == 1:
                assert np.array_equal(s, g.signals['trend_100_rebound_2'])
            p, rec = engine.simulate_group(g, cfg['hold'], cfg['fade'], 'scaled', detail=True)
            chunks.append(p)
            records.extend(rec)
        r = np.concatenate(chunks)
        trades = pd.DataFrame(records)
        s = engine.metrics(r, 0)
        loss_sum = -r[r < 0].sum()
        s['pf'] = float(r[r > 0].sum()/loss_sum) if loss_sum else float('inf')
        s['avg_bars'] = float(trades.bars.mean())
        s['fade_exits'] = int((trades.reason == 'fading').sum())
        s['period_end_exits'] = int(trades.reason.str.startswith('period_end').sum())
        s['worst_intratrade'] = float(trades.adverse_excursion.min())
        rows.append(dict(**cfg, **s))
        trades.to_csv(OUT / f"{cfg['mode']}_scale_{cfg['scale']:.2f}_trades.csv", index=False)
        print(f"{cfg['mode']} {cfg['scale']:.2f}: n={len(r)}, WR={s['wr']:.4f}, PF={s['pf']:.3f}, numeric={s['numeric_passes']}/5", flush=True)
    results = pd.DataFrame(rows)
    baseline = results[(results['mode'] == 'time_only') & (results.scale == 1)].iloc[0]
    assert baseline.n == 1974
    assert np.isclose(baseline['mean'], .2625687848471162)
    results['trade_multiple'] = results.n / baseline.n
    results.to_csv(OUT / 'comparison.csv', index=False)
    passing = results[(results['mode'] == 'time_only') & (results.numeric_passes == 5)]
    fastest = passing.sort_values('n', ascending=False).iloc[0]
    (OUT / 'summary.json').write_text(json.dumps(dict(configurations=len(results),
        interpretation='Main: time windows scaled equally; alternate: percentage thresholds also scaled.',
        fastest_time_only_passing=fastest.to_dict(), costs=0), indent=2), encoding='utf-8')
    lines = ['# TimeHunter: proportional compression',
        'Periode kontinu 12 Juli 1994–15 Agustus 2025, 100 saham, biaya nol. H:SMA:High-window selalu 10:5:1. Entry tetap trend + pullback + rebound; beli next tradable Open. Fading selalu relatif Open bar terbaru, jual next tradable Open. Rebound satu bar dan delay eksekusi satu bar tetap karena resolusi data harian.',
        'Eksperimen utama time_only hanya memperpendek tiga periode; pullback 2% dan fading 30% tetap. Eksperimen alternatif time_and_thresholds turut mengalikan kedua persentase dengan faktor sama. Itu sensitivitas tambahan, bukan asumsi bahwa harga harus berskala linear terhadap waktu.',
        'N adalah jumlah transaksi gabungan; multiple membandingkan N dengan 1.974 transaksi baseline. Mean adalah return per transaksi, bukan return tahunan/portofolio. PF dihitung dari jumlah return positif dibagi absolut jumlah return negatif (notional entry sama), bukan payout. Avg loss adalah magnitudo positif. Worst intratrade bukan drawdown portofolio.',
        'Pencarian seluruh periode bersifat in-sample. Lolos 5/5 numerik tidak berarti 7/7 tervalidasi atau hasil sama di semua periode/pasar. Shorter horizons do not preserve statistical performance automatically. Corporate action dan survivorship belum diverifikasi.']
    for mode in ['time_only', 'time_and_thresholds']:
        lines.extend([f'## {mode}', '| Scale | H/SMA/High | Pullback | Fade | N | Multiple | WR | PF | Payout | Mean | Median | Avg loss | Avg bars | Numerik |',
                      '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'])
        for r in results[results['mode'] == mode].itertuples():
            lines.append(f'| {r.scale:.2f} | {r.hold}/{r.sma}/{r.high_window} | {r.pullback:.2%} | {r.fade:.2%} | {r.n} | {r.trade_multiple:.2f}x | {r.wr:.2%} | {r.pf:.3f} | {r.payout:.3f} | {r.mean:.2%} | {r.median:.2%} | {r.avg_loss:.2%} | {r.avg_bars:.1f} | {r.numeric_passes}/5 |')
    (OUT / 'REPORT.md').write_text('\n\n'.join(lines[:5])+'\n'+'\n'.join(lines[5:]), encoding='utf-8')
    print('FASTEST TIME-ONLY 5/5:', fastest.to_json(), flush=True)


if __name__ == '__main__':
    main()
