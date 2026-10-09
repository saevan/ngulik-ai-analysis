"""Render reproducible findings and boundary sensitivity for the frozen grids."""
from datetime import datetime, timedelta, timezone
import json
import pandas as pd
from grid_search_timehunter import OUT, FADING_REFERENCE, metrics, STOCK_COST, FOREX_COST


def pct(x):
    return f'{100*x:.2f}%'


def describe_entry(name):
    parts = name.split('_')
    if name == 'always':
        return 'Masuk pada open pertama yang tersedia saat belum memiliki posisi.'
    if parts[0] == 'breakout':
        condition = (f'close bar sinyal lebih tinggi dari high tertinggi {parts[1]} '
                     'bar sebelum bar sinyal')
    elif parts[0] == 'dip':
        condition = (f'close bar sinyal minimal {parts[2]}% di bawah high tertinggi '
                     f'{parts[1]} bar, termasuk bar sinyal')
    elif parts[0] == 'trend':
        condition = f'close bar sinyal di atas SMA{parts[1]}'
        if len(parts) > 2:
            condition += f', minimal {parts[3]}% di bawah high tertinggi 20 bar'
            if parts[2] == 'rebound':
                condition += ', dan close naik dibandingkan close sebelumnya'
    else:
        raise ValueError(f'Unknown entry rule: {name}')
    return f'Jika {condition}, beli pada open berikutnya yang dapat diperdagangkan.'


def describe_config(config):
    fading_rule = ('Tanpa fading.' if config['dip'] is None else
                   f'Fading {pct(config["dip"])} dari Open bar yang sedang berjalan; '
                   'Low menyentuh level pemicu -> jual pada open berikutnya yang dapat diperdagangkan.')
    return (describe_entry(config['entry_name']) +
            f' Time exit pada close bar ke-{config["hold"]}. ' + fading_rule)


def transfer_status(summary):
    if summary['n'] < 100 or summary['tickers'] < 3:
        return 'Belum terbukti: sampel tidak cukup'
    if summary['numeric_passes'] < 5:
        return 'Belum memenuhi lima kriteria numerik pada sampel transfer'
    return 'Lolos pada sampel transfer ini; tidak membuktikan universal'


def main():
    primary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    fading=json.loads((OUT/'fading_summary.json').read_text(encoding='utf-8'))
    method=json.loads((OUT/'methodology.json').read_text(encoding='utf-8'))
    stock_cost = method['stock_cost_per_side']
    forex_cost = method['forex_cost_per_side']
    if (stock_cost, forex_cost) != (STOCK_COST, FOREX_COST):
        raise ValueError('Artifact costs do not match the active grid; rerun the grid first')
    is_gross = stock_cost == 0 and forex_cost == 0
    basis = 'gross' if is_gross else 'net'
    for artifact in [primary, fading, method]:
        if artifact.get('fading_reference') != FADING_REFERENCE:
            raise ValueError('Artifact uses an outdated fading reference; rerun corrected grid first')
        if (artifact.get('stock_cost_per_side'), artifact.get('forex_cost_per_side')) != (stock_cost, forex_cost):
            raise ValueError('Mixed cost assumptions across grid artifacts; rerun all branches first')
        if artifact.get('result_basis') != basis:
            raise ValueError('Mixed return bases across grid artifacts; rerun all branches first')
    train=pd.read_csv(OUT/'train_grid.csv')
    validation=pd.read_csv(OUT/'validation_shortlist.csv')
    fade_validation=pd.read_csv(OUT/'fading_validation_shortlist.csv')
    train_pass=int((train.train_numeric_passes==5).sum())
    fade_pass=int(((train.train_numeric_passes==5)&train.dip.notna()).sum())
    validation_pass=int((validation.validation_numeric_passes==5).sum())
    fade_validation_pass=int((fade_validation.validation_numeric_passes==5).sum())
    fx=fading['forex_transfer']
    primary_fx=primary['forex_transfer']
    cost_description = (
        '- Seluruh fee, pajak, spread, slippage, swap, dan biaya lain dinonaktifkan. '
        'Biaya beli dan jual saham maupun forex = 0. Semua kriteria serta ranking '
        'train/validation dihitung dari return gross.'
        if is_gross else
        f'- Asumsi biaya per sisi: saham {pct(stock_cost)}, forex {pct(forex_cost)}. '
        'Return dihitung sebagai (1+return_gross)*(1-biaya_jual)/(1+biaya_beli)-1; '
        'spread dinamis, swap, dan slippage belum dimodelkan.'
    )
    run_time = datetime.now(timezone(timedelta(hours=7))).isoformat()
    lines=[
        '# Grid TimeHunter: waktu, harga, dan fading', '',
        f'Laporan dibuat (Asia/Jakarta): {run_time}. Basis hasil: **{basis}**.', '',
        f'**Pada test 2020–2025, kandidat utama memenuhi {primary["test"]["numeric_passes"]}/5 '
        f'kriteria numerik dan kandidat fading memenuhi {fading["test"]["numeric_passes"]}/5. '
        'Status lintas pasar dan kausalitas dilaporkan terpisah; skor 7/7 tidak diberikan otomatis.**', '',
        '## Definisi fading yang dikoreksi pengguna', '',
        '`Low[t] <= Open[t] * (1 - ambang)`. Acuan direset pada setiap bar baru. '
        'Harga saat entry hanya dipakai untuk menghitung PnL, bukan menentukan pemicu fading.', '',
        'Contoh entry 100, open bar baru 120, fading 5%: level pemicunya 114. '
        'Sinyal dapat muncul saat posisi masih untung. Sebaliknya, entry 100 lalu gap ke open 80 '
        'dengan low 79 belum memicu fading 5%, karena level bar tersebut 76.', '',
        'Jam/usia posisi tetap dihitung sejak entry; pergantian open tidak memulai ulang usia posisi. '
        'Model jual next-open tetap dipakai. Koreksi ini tidak mengubahnya menjadi jual intrabar.', '',
        'Hasil di `../grid_timehunter_results/` memakai acuan entry yang keliru untuk maksud pengguna. '
        'Hasil lama dipertahankan sebagai arsip, bukan sebagai hasil fading yang benar.', '',
        'Hasil dengan biaya dari `../grid_timehunter_bar_open_results/` dipertahankan sebagai '
        'arsip. Pencarian ini mengulang seluruh grid dengan asumsi biaya pada laporan ini.', '',
        '## Ruang pencarian dan pemilihan', '',
        f'- {len(train):,} kombinasi = {len(method["hold_grid"])} waktu pegang × '
        f'{len(method["dip_grid"])} pengaturan fading × {len(method["entry_grid"])} aturan entry.',
        '- Waktu pegang: '+', '.join(str(h) for h in method['hold_grid'])+' bar.',
        '- Fading: '+', '.join('tidak ada' if d is None else pct(d) for d in method['dip_grid'])+
        ' dari Open masing-masing bar.',
        '- Entry: selalu masuk, tren SMA, pullback dari high bergulir, rebound, atau breakout. '
        'Semua sinyal entry memakai bar yang sudah selesai.',
        '- Train sampai 2014: semua konfigurasi. Minimal 200 transaksi/observasi dan 20 ticker.',
        '- Shortlist 20 diurutkan menurut jumlah kriteria numerik, margin WR/payout, '
        'mean setelah membuang 1% hasil terbaik, kemudian jumlah transaksi.',
        '- Validation 2015–2019: pilih satu kandidat; minimal 100 observasi dan 20 ticker. '
        'Parameter disimpan sebelum melihat test 2020–2025.',
        '- Dua shortlist sudah ditentukan sebelum rerun koreksi: shortlist keseluruhan dan '
        'shortlist khusus fading. Keduanya memakai ranking train lalu memilih satu kandidat '
        'menggunakan validation; parameter tidak dipilih berdasarkan test.',
        '- Data 2020–2025 sudah pernah dilihat pada eksperimen sebelumnya; ini bukan holdout '
        'yang benar-benar baru untuk keseluruhan riset.',
        f'- {train_pass} konfigurasi lolos 5/5 pada train ({basis}), termasuk {fade_pass} '
        f'dengan fading. Shortlist utama: {validation_pass} dari {len(validation)} lolos '
        f'pada validation. Shortlist fading: {fade_validation_pass} dari {len(fade_validation)}.', '',
        '## Biaya, data, dan eksekusi', '',
        f'- Saham: {method["stock_rows"]:,} bar / {method["stock_tickers"]} ticker. '
        f'{method["stock_start"]} sampai {method["stock_end"]}.',
        '- Satu bar TLKM bertimestamp intrahari dikeluarkan karena status close hariannya tidak jelas. '
        f'{method["normalized_bars"]} rentang OHLC diperluas agar mencakup Open/Close; sumber CSV tidak diubah.',
        '- Tidak mengisi order pada bar saham bervolume nol; order menunggu open pertama '
        'dengan volume positif. Ini hanya pendekatan keterisian, bukan bukti likuiditas pada open.',
        '- Time exit dijadwalkan pada close bar ke-H, termasuk bar entry. Jika tidak bisa '
        'diperdagangkan, exit dapat tertunda melampaui H.',
        '- Fading: Low menyentuh ambang dari Open bar itu sebelum deadline -> order jual pada open berikutnya '
        'yang dapat diperdagangkan. Gap tidak dibatasi oleh ambang fading.',
        '- Reentry paling cepat satu bar sesudah bar penjualan, jika sinyal entry terpenuhi. '
        'Tidak menambah posisi saat rugi. Satu posisi long per ticker.',
        cost_description,
        '- Tiap periode dimulai tanpa posisi dan diakhiri dengan likuidasi pada close terakhir. '
        'Jika bar terakhir tidak dapat diperdagangkan, posisi dinilai dengan close terakhir '
        '(period_end_mark); nilai ini bukan transaksi keluar yang terlaksana.',
        '- Angka return menggabungkan transaksi dengan bobot setara. Bukan return tahunan, '
        'bukan kurva modal portofolio, dan observasi lintas saham tidak independen.', '',
        '## Kandidat yang dibekukan', '',
        '**Utama:** '+describe_config(primary['locked_config']), '',
        '**Fading:** '+describe_config(fading['locked_config']), '',
        f'| Kandidat/periode | N | WR {basis} | Payout {basis} | Mean {basis} | Median {basis} | Numerik |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for name,res in [('Utama',primary),('Fading',fading)]:
        for label in ['train','validation','test','all']:
            s=res[label]
            lines.append(f'| {name}/{label} | {s["n"]} | {pct(s["wr"])} | {s["payout"]:.2f} | '
                         f'{pct(s["mean"])} | {pct(s["median"])} | {s["numeric_passes"]}/5 |')
    lines += ['', 'All menjalankan satu simulasi kontinu; jumlahnya tidak sama dengan penjumlahan '
              'tiga periode yang masing-masing memaksa penutupan di batasnya.', '',
              '### Seberapa sering fading benar-benar bekerja', '',
              '| Periode | Proporsi exit fading | Rata-rata bar per posisi |',
              '|---|---:|---:|']
    for label in ['train','validation','test','all']:
        stat=fading[label]
        lines.append(f'| {label} | {pct(stat["fading_fraction"])} | {stat["mean_bars"]:.2f} |')
    if fading['test']['fading_fraction']==0:
        lines += ['', '**Tidak ada exit fading pada test untuk kandidat terpilih. '
                  'Hasil test tersebut tidak membuktikan manfaat tambahan fading.**']
    lines += ['',
              '## Tujuh kriteria pada kandidat fading, periode test', '',
              '| Kriteria | Bukti | Status |', '|---|---|---|']
    s=fading['test']
    assessments=[
        ('Mean > median',f'{pct(s["mean"])} > {pct(s["median"])}',s['mean']>s['median']),
        ('Rata-rata menang > rata-rata rugi',f'{pct(s["avg_win"])} > {pct(s["avg_loss"])}',s['avg_win']>s['avg_loss']),
        ('Payout >2',f'{s["payout"]:.2f}',s['payout']>2),
        ('WR >50%',pct(s['wr']),s['wr']>.5),
        ('Expectancy positif',pct(s['mean']),s['mean']>0),
    ]
    for name,evidence,passed in assessments:
        lines.append(f'| {name} | {evidence} | {"Lolos" if passed else "Gagal"} |')
    lines += [
        f'| Lintas pasar | Forex fading: {fx["n"]} observasi / {fx["tickers"]} ticker, '
        f'{fx["numeric_passes"]}/5 numerik. Utama: {primary_fx["n"]} observasi | '
        f'{transfer_status(fx)} |',
        '| Tanpa informasi masa depan | Pengujian kausalitas dan referensi simulator, '
        'gap, antrean volume nol, deadline, biaya | Lolos audit model; real fill tetap asumsi |', '',
        'Indikator harga dapat dihitung pada pasar lain, tetapi itu tidak membuktikan edge '
        'atau parameter universal. Forex yang tersedia per jam, sedangkan saham harian; '
        'jumlah bar identik bukan durasi identik. Tidak ada retuning pada forex. '
        'Batas diagnostik kecukupan sampel transfer pada laporan ini: 100 observasi dan 3 ticker; '
        'bahkan melampaui batas ini tidak membuktikan universal.', '',
        '## Risiko yang masih terlihat', '',
        f'- Kandidat fading: transaksi test terburuk {basis} {pct(s["worst"])}; '
        f'penurunan intratrade terburuk gross {pct(s["worst_adverse_excursion"])}. '
        'Ambang fading mengukur penurunan dalam satu bar, bukan kerugian kumulatif posisi. '
        'Penurunan bertahap antarbar dan gap dapat menimbulkan kerugian jauh lebih besar.',
        f'- Kandidat utama: transaksi test terburuk {basis} {pct(primary["test"]["worst"])}.',
        f'- Fading test: mean setelah menghapus 1% transaksi terbaik = {pct(s["trimmed_mean"])}. '
        'Ini hanya diagnostik konsentrasi, bukan validasi independen.',
        '- Skor tidak mengukur drawdown portofolio, durasi pemulihan modal, atau konsentrasi posisi.',
        '- Corporate action dan gap ekstrem belum diverifikasi terhadap vendor. Daftar saham '
        'juga belum terbukti bebas survivorship bias.',
        '- Ribuan percobaan meningkatkan risiko menemukan hasil kebetulan. Tidak mencari '
        'ulang parameter berdasarkan test sampai terlihat lolos.', '',
        '## Sensitivitas posisi pada batas periode', '',
        'Tabel utama mencakup posisi akhir periode. Berikut hanya exit time/fading yang '
        'terlaksana; penutupan atau penilaian karena batas data dikeluarkan. Ini diagnostik, '
        'bukan pengganti perhitungan portofolio.', '',
        '| Kandidat/periode | Mark tanpa fill | N exit biasa | WR | Payout | Mean | Numerik |',
        '|---|---:|---:|---:|---:|---:|---:|'
    ]
    sensitivity={'metadata': dict(result_basis=basis, stock_cost_per_side=stock_cost,
                                 forex_cost_per_side=forex_cost,
                                 cost_model=method['cost_model'])}
    for name,prefix in [('Utama','candidate'),('Fading','fading')]:
        for period in ['train','validation','test']:
            d=pd.read_csv(OUT/f'{prefix}_{period}_trades.csv')
            m=metrics(d.loc[~d.reason.str.startswith('period_end'),'gross_return'].to_numpy(),stock_cost)
            marks=int((d.reason=='period_end_mark').sum())
            sensitivity[f'{prefix}_{period}']=dict(unfilled_marks=marks,regular_exits=m)
            lines.append(f'| {name}/{period} | {marks} | {m["n"]} | {pct(m["wr"])} | '
                         f'{m["payout"]:.2f} | {pct(m["mean"])} | {m["numeric_passes"]}/5 |')
    lines += ['', '## Reproduksi', '', '```powershell',
              'python -m unittest -v test_grid_timehunter.py',
              'python -u grid_search_timehunter.py',
              'python -u analyze_timehunter_fading_grid.py',
              'python write_timehunter_grid_report.py', '```', '',
              'Seluruh parameter, grid train, shortlist validation, konfigurasi yang dibekukan, '
              'hasil forex, dan ledger transaksi disimpan di folder ini.']
    (OUT/'boundary_sensitivity.json').write_text(json.dumps(sensitivity,indent=2),encoding='utf-8')
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT/'REPORT.md')
    print(f'Train passes: {train_pass}; fading: {fade_pass}; validation: '
          f'{validation_pass}/{len(validation)}; fading validation: {fade_validation_pass}/{len(fade_validation)}')


if __name__=='__main__':
    main()
