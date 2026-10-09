"""Rerun frozen TimeHunter candidates and baseline; no parameter selection.

Produces auditable trade ledgers, cost-aware statistics and a Markdown report.
Results are equal-weight trade observations, NOT a funded portfolio return.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grid_search_timehunter import (
    ROOT, OUT as GRID_OUT, FADING_REFERENCE, STOCK_COST,
    load_data, prepare, evaluate, metrics,
)
from write_timehunter_grid_report import describe_entry

OUT = ROOT / ('backtest_timehunter_selected_gross_results' if STOCK_COST == 0
              else 'backtest_timehunter_selected_results')


def pct(value):
    return f'{value * 100:.2f}%'


def assess(groups, config, start):
    stats, records = evaluate(groups, config, start=start, cost=STOCK_COST, detail=True)
    trades = pd.DataFrame(records)
    returns = trades.gross_return if STOCK_COST == 0 else (
        (1 + trades.gross_return) * (1 - STOCK_COST) / (1 + STOCK_COST) - 1)
    if STOCK_COST != 0:
        trades['net_return'] = returns
    assert len(trades) == stats['n']
    assert np.isclose(returns.mean(), stats['mean'])
    assert np.isclose(trades.gross_return.mean(), stats['gross']['mean'])
    assert np.isclose((returns > 0).mean(), stats['wr'])
    positive = returns.loc[returns > 0]
    negative = returns.loc[returns < 0]
    stats.update(
        wins=int((returns > 0).sum()),
        losses=int((returns < 0).sum()),
        breakeven=int((returns == 0).sum()),
        mean_bars=float(trades.bars.mean()),
        worst_intratrade_gross=float(trades.adverse_excursion.min()),
        mean_intratrade_gross=float(trades.adverse_excursion.mean()),
        profit_factor=float(positive.sum() / -negative.sum()) if len(negative) else None,
        exit_counts={str(k): int(v) for k, v in trades.reason.value_counts().items()},
        first_entry=str(trades.entry_date.min()),
        last_exit=str(trades.exit_date.max()),
        regular_exits_only=metrics(
            trades.loc[~trades.reason.str.startswith('period_end'), 'gross_return'].to_numpy(),
            STOCK_COST,
        ),
    )
    return stats, trades


def write_report(results):
    meta = results['metadata']
    config = results['configs']['selected_fading']
    cost = meta['cost_per_side']
    is_gross = cost == 0
    basis = 'gross' if is_gross else 'net'
    cost_description = (
        '- Seluruh fee, pajak, spread, slippage, dan biaya lain dinonaktifkan. '
        'Biaya beli dan jual = 0. Penilaian kriteria memakai return gross.'
        if is_gross else
        f'- Biaya ilustratif {pct(cost)} beli + {pct(cost)} jual. '
        'Spread, slippage, likuiditas order, dan pajak terpisah belum dimodelkan.'
    )
    lines = [
        '# Backtest ulang kandidat TimeHunter', '',
        f'Waktu run (Asia/Jakarta): {meta["run_time_jakarta"]}.', '',
        'Ini pengulangan kandidat yang sudah dipilih. Tidak ada grid search atau '
        'pemilihan parameter berdasarkan hasil run ini. Data periode uji pernah '
        'dilihat sebelumnya, jadi bukan validasi independen baru.', '',
        '## Aturan dan data', '',
        f'- Kandidat: `{json.dumps(config)}`.',
        '- Entry kandidat: ' + describe_entry(config['entry_name']),
        f'- Exit kandidat: close bar ke-{config["hold"]}, atau Low turun '
        f'{pct(config["dip"])} dari **Open bar yang sedang berjalan** lalu jual next-open.',
        '- Acuan fading direset setiap bar. Bukan harga entry, bukan high sebelumnya. '
        'Harga entry tetap menjadi dasar PnL.',
        '- Pembanding tanpa fading memakai entry dan hold yang sama; baseline TimeHunter '
        'memakai entry tanpa filter dan close bar ke-50.',
        '- Satu posisi long per ticker. Reentry paling cepat bar setelah penjualan dan '
        'mengikuti filter entry. Usia posisi direset hanya saat entry baru.',
        f'- Data: {meta["rows"]:,} bar dari {meta["tickers"]} ticker, '
        f'{meta["start"]} sampai {meta["end"]}.',
        cost_description,
        f'- {meta["normalized_ohlc_bars"]} rentang OHLC dinormalkan; satu bar bertimestamp '
        'intrahari dikeluarkan. Bar volume nol tidak dianggap bisa mengisi order; '
        'order menunggu open bar berikutnya dengan volume positif.',
        '- Setiap periode dimulai tanpa posisi. Posisi akhir periode ditutup/ditandai '
        'pada close terakhir. `period_end_mark` adalah penilaian tanpa fill yang terlaksana.', '',
        '## Hasil gross tanpa biaya' if is_gross else '## Hasil sebelum dan sesudah biaya', '',
    ]
    if is_gross:
        lines += ['| Periode / strategi | N | WR gross | Mean gross | Median gross | Payout gross |',
                  '|---|---:|---:|---:|---:|---:|']
    else:
        lines += ['| Periode / strategi | N | WR gross | WR net | Mean gross | Mean net | Median net | Payout net |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|']
    names = {'selected_fading': 'Kandidat + fading', 'selected_no_fading': 'Kandidat tanpa fading',
             'timehunter50': 'TimeHunter 50'}
    for period, strategies in results['periods'].items():
        for name, s in strategies.items():
            if is_gross:
                lines.append(f'| {period} / {names[name]} | {s["n"]} | {pct(s["wr"])} | '
                             f'{pct(s["mean"])} | {pct(s["median"])} | {s["payout"]:.2f} |')
            else:
                lines.append(f'| {period} / {names[name]} | {s["n"]} | {pct(s["gross"]["wr"])} | '
                             f'{pct(s["wr"])} | {pct(s["gross"]["mean"])} | {pct(s["mean"])} | '
                             f'{pct(s["median"])} | {s["payout"]:.2f} |')
    lines += ['', '**Mean adalah rata-rata persentase per transaksi/observasi, bukan return '
              'tahunan atau return portofolio.** Durasi pegang dan jumlah transaksi berbeda; '
              'mean lebih besar tidak otomatis berarti sistem lebih baik.', '',
              '## Rincian risiko dan eksekusi', '',
              f'| Periode / strategi | Avg win {basis} | Avg loss {basis} | Terburuk {basis} | Terburuk intratrade gross | Avg bar | Exit fading | Mark tanpa fill | Numerik |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for period, strategies in results['periods'].items():
        for name, s in strategies.items():
            lines.append(f'| {period} / {names[name]} | {pct(s["avg_win"])} | '
                         f'{pct(-s["avg_loss"])} | {pct(s["worst"])} | '
                         f'{pct(s["worst_intratrade_gross"])} | {s["mean_bars"]:.2f} | '
                         f'{s["exit_counts"].get("fading",0)} | '
                         f'{s["exit_counts"].get("period_end_mark",0)} | {s["numeric_passes"]}/5 |')
    test = results['periods']['2020-2025']['selected_fading']
    lines += ['', 'Penurunan intratrade dihitung dari entry ke harga terendah selama posisi '
              'masih terbuka; angka ini **bukan maximum drawdown portofolio**.', '',
              f'Pada kandidat fading periode 2020-2025 terdapat '
              f'{test["exit_counts"].get("fading",0)} exit fading. '
              f'Kesamaan ledger dengan kandidat tanpa fading: {results["test_ledgers_equal"]}.', '',
              '## Lima kriteria numerik pada kandidat periode 2020-2025', '',
              '| Kriteria | Hasil |', '|---|---|']
    checks = [
        ('Mean > median', test['mean'] > test['median']),
        ('Avg win > avg loss', test['avg_win'] > test['avg_loss']),
        ('Payout > 2', test['payout'] > 2),
        ('WR > 50%', test['wr'] > .5),
        ('Expectancy > 0', test['mean'] > 0),
    ]
    for name, passed in checks:
        lines.append(f'| {name} | {"Lolos" if passed else "Gagal"} |')
    lines += ['', 'Kausalitas dan transfer lintas pasar tidak diberi poin otomatis. '
              'Run ini hanya memakai saham; hasil transfer forex dengan asumsi yang sama '
              f'tersedia di `../{GRID_OUT.name}/REPORT.md`. Corporate action, saham delisting, dan '
              'survivorship bias belum diverifikasi. Statistik tidak menentukan alokasi '
              'modal maupun pertumbuhan suatu portofolio.', '',
              '## Reproduksi', '', '```powershell', 'python -u backtest_timehunter_selected.py',
              '```', '', 'Ringkasan mesin tersimpan di `summary.json` dan seluruh transaksi '
              'ada dalam CSV untuk masing-masing strategi/periode.']
    (OUT / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=True)
    selected = json.loads((GRID_OUT / 'fading_locked_candidate.json').read_text(encoding='utf-8'))
    method = json.loads((GRID_OUT / 'methodology.json').read_text(encoding='utf-8'))
    assert method['fading_reference'] == FADING_REFERENCE == 'current_bar_open'
    expected_basis = 'gross' if STOCK_COST == 0 else 'net'
    if method.get('stock_cost_per_side') != STOCK_COST or method.get('result_basis') != expected_basis:
        raise ValueError('Selected configuration must come from a grid using the active cost assumptions')
    fading_summary = json.loads((GRID_OUT / 'fading_summary.json').read_text(encoding='utf-8'))
    if (fading_summary.get('stock_cost_per_side') != STOCK_COST
            or fading_summary.get('result_basis') != expected_basis
            or fading_summary.get('locked_config') != selected):
        raise ValueError('Fading selection and summary do not match the active grid')
    configs = dict(selected_fading=selected,
                   selected_no_fading={**selected, 'dip': None},
                   timehunter50=dict(hold=50, dip=None, entry_name='always'))
    stocks, anomalies = load_data('stocks')
    anomalies.to_csv(OUT / 'ohlc_anomalies.csv', index=False)
    groups = prepare(stocks, dips=[selected['dip']])
    results = dict(metadata=dict(
        run_time_jakarta=datetime.now(timezone(timedelta(hours=7))).isoformat(),
        rows=len(stocks), tickers=int(stocks.Ticker.nunique()),
        start=str(stocks['Date/Time'].min()), end=str(stocks['Date/Time'].max()),
        normalized_ohlc_bars=len(anomalies), cost_per_side=STOCK_COST,
        stock_cost_per_side=STOCK_COST,
        result_basis=expected_basis, cost_model='none' if STOCK_COST == 0 else 'per_side',
        selection_source=str(GRID_OUT), selection_result_basis=method['result_basis'],
        fading_reference=FADING_REFERENCE,
        engine_sha256=hashlib.sha256((ROOT / 'grid_search_timehunter.py').read_bytes()).hexdigest(),
        parameter_selection_in_this_run=False,
    ), configs=configs, periods={})
    test_ledgers = {}
    for period, start in [('1994-2025', None), ('2020-2025', '2020-01-01')]:
        results['periods'][period] = {}
        for name, config in configs.items():
            stats, trades = assess(groups, config, start)
            trades.to_csv(OUT / f'{period}_{name}_trades.csv', index=False)
            results['periods'][period][name] = stats
            if period == '2020-2025':
                test_ledgers[name] = trades
            print(json.dumps(dict(period=period, strategy=name, n=stats['n'],
                                  wr=stats['wr'], mean=stats['mean'], gross_mean=stats['gross']['mean'],
                                  payout=stats['payout'], worst=stats['worst'],
                                  intratrade=stats['worst_intratrade_gross'], exits=stats['exit_counts'])), flush=True)
    results['test_ledgers_equal'] = test_ledgers['selected_fading'].equals(test_ledgers['selected_no_fading'])
    (OUT / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    write_report(results)
    print(f'Saved {OUT / "REPORT.md"}', flush=True)


if __name__ == '__main__':
    main()
