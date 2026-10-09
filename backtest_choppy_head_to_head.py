"""Matched market-choppy entry eligibility; preserve Swinger ideal fills."""
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
import backtest_prototype_swinger as swinger
from backtest_choppy_inverted_signals import inverted_builders
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_head_to_head_results'

def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    allowed=set(proxy.index[proxy.regime=='sideways'])
    original=swinger.signals
    def gated_signals(f,swing=5):
        s=original(f,swing).copy()
        s['buy']=s.buy & f['Date/Time'].isin(allowed)
        return s
    rows=[]
    for name in ['swinger_original_control','swinger_market_choppy','inverse_market_choppy','inverse_market_stock_choppy']:
        if name.startswith('swinger'):
            with patch.object(swinger,'signals',gated_signals if name=='swinger_market_choppy' else original):
                c,t,_=swinger.run_portfolio(frames,'afl_ideal')
            if name=='swinger_original_control':
                old=pd.read_csv(ROOT/'prototype_swinger_benchmark_results/afl_ideal_net_equity.csv')
                np.testing.assert_allclose(c.equity,old.equity,rtol=1e-10)
        else:
            variant='market' if name=='inverse_market_choppy' else 'market_stock'
            entry,exit_signal=inverted_builders((variant,0),allowed)
            with np.errstate(invalid='ignore'):
                c,t,_=portfolio(frames,hold=None,fade=float('inf'),entry_builder=entry,exit_builder=exit_signal,cost_model=Costs())
            old=pd.read_csv(ROOT/f'choppy_inverted_signal_results/full_fees_{variant}_0_equity.csv')
            np.testing.assert_allclose(c.equity,old.equity,rtol=1e-10)
        if name!='swinger_original_control':assert t.entry_date.isin(allowed).all()
        stats,daily=attribute(c,proxy,'stocks',name);s=stats[stats.regime=='sideways'].iloc[0]
        d=daily[daily.regime=='sideways'];g=t[t.entry_date.isin(allowed)];r=g.net_return
        monthly=c.new_high.groupby(c.index.to_period('M')).any()
        rows.append(dict(system=name,choppy_days=len(d),sideways_annual=s.conditional_annualized,
            sideways_records=s.months_record,sideways_months=s.months_present,
            cash=(d.cash/d.equity).mean(),positions=d.positions.mean(),positive_days=(d.equity_return>0).mean(),
            n=len(g),wr=(r>0).mean(),avg_win=r[r>0].mean(),avg_loss=-r[r<0].mean(),mean_return=r.mean(),
            mean_bars=g.bars.mean(),winner_bars=g.loc[r>0,'bars'].mean(),loser_bars=g.loc[r<0,'bars'].mean(),
            full_cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,
            full_mdd=c.drawdown.min(),full_records=int(monthly.sum()),full_months=len(monthly)))
        c.to_csv(OUT/f'{name}_equity.csv');t.to_csv(OUT/f'{name}_trades.csv',index=False)
        d.to_csv(OUT/f'{name}_choppy_days.csv')
        pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        print(name,rows[-1],flush=True)
    (OUT/'METHOD.md').write_text('''# Perbandingan hanya pasar choppy

4 Januari2000–15Agustus2025,100saham yang sama,ER20 proxy pasar equal-weight<0.30 diketahui dari bar pasar sebelumnya. Tidak memotong OHLC atau menyambung ulang bar choppy untuk menghitung indikator. Keduanya entry hanya pada tanggal eligible yang sama; sinyal/exit masing-masing tetap. Exit boleh pada hari trending, posisi tidak dipaksa tutup saat regime berubah. Bukan strategi selalu-flat di luar choppy.

ModalRp1miliar,10slot,10%equity sebelumnya cashcap compounding,fee buy0.15%/sell0.25%,tanpa spread untuk kedua pihak. Swinger original ideal fill dipertahankan; hanya Buy digate, TSL/state/Sell tetap. Inverse market uses raw primary Sell(SMA30/fade2) as entry, raw Buy(breakout20+stockER>=.3) as exit nextOpen; tanpa stop tambahan. Inverse market_stock adalah versi sebelumnya dengan tambahanstockER<.3; dilaporkan terpisah. Tidak mengubah main/AFL.

Statistik utama sideways_annual/cash/positions/records hanya pada hari equity yang berlabel choppy. Sideways_annual adalah annualisasi atribusi logreturn pada interval kalender tanggal choppy yang terpisah, bukan CAGR portofolio mandiri. Record month adalah bulan dengan all-time closing equity high pada setidaknya satu hari choppy; denominator280bulan yang memuat hari choppy; peak tidak direset. Trade metrics dikelompokkan menurut rezim entry dengan full lifetime return, bisa meliputi hari trending. Full_cagr/full_mdd hanya konteks portofolio gated sepanjang kalender, jangan dilabeli hasil murni harichoppy.

Original Swinger rerun diregresikan keequity benchmark tersimpan; kedua inverse diregresikan kehasil sebelumnya. Semua entry varian gated diperiksa eligible. CSVchoppy_days menyimpan attribution dates agar dapat diaudit. Benchmark original control tetapentrysemuaregime; bukan kolom utama perbandingan gated. Penelitian memakai riwayat yang sudah dilihat, bukan validasi independen atau nativeAmiBroker. Data survivorship, corporate action danliquiditylimitations tetap.
''',encoding='utf-8')

if __name__=='__main__':main()
