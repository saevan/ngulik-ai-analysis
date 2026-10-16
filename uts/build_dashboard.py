"""Build the single-file UTS dashboard (uts/output/UTS_NIM_Nama.html) from uts/output/*.csv and results.json.
No external resources: CSS, JS, charts (inline SVG) and all data (JSON) are embedded."""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from .data import load_stocks

OUT=Path(__file__).resolve().parent/'output'


def clean(o):
    if isinstance(o,dict):return {str(k):clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)):return [clean(v) for v in o]
    if isinstance(o,(float,np.floating)):return None if not math.isfinite(float(o)) else round(float(o),10)
    if isinstance(o,(np.integer,)):return int(o)
    if isinstance(o,(np.bool_,)):return bool(o)
    return o


def main():
    res=json.load(open(OUT/'results.json'))
    eq=pd.read_csv(OUT/'equity_main.csv',parse_dates=['date']).set_index('date')
    bench=pd.read_csv(OUT/'benchmark.csv',parse_dates=[0]).set_index(pd.read_csv(OUT/'benchmark.csv').columns[0] if False else None) if False else pd.read_csv(OUT/'benchmark.csv',index_col=0,parse_dates=True).iloc[:,0]
    b=bench.reindex(eq.index).ffill();b=b/b.iloc[0]*res['meta']['capital']
    EQ=[[str(d.date()),round(float(r.equity),2),round(float(r.drawdown),6),int(r.positions),round(float(r.market_value/r.equity),4),round(float(b.loc[d]),2)] for d,r in eq.iterrows()]
    tr=pd.read_csv(OUT/'trades_main.csv')
    TR=[[i+1,r.ticker,str(r.entry_date)[:10],r.entry_time,round(r.entry_price,4),str(r.exit_date)[:10],r.exit_time,round(r.exit_price,4),int(round(r.shares/100)),
         round(r.buy_fee+r.sell_fee,2),round(r.spread_cost,2),round(r.gross_pnl,2),round(r.pnl,2),round(r.net_return,6),int(r.days),int(r.bars),r.reason,round(r.notional,2)]
        for i,r in enumerate(tr.sort_values(['entry_date','ticker']).itertuples())]
    op=pd.read_csv(OUT/'open_positions_main.csv') if (OUT/'open_positions_main.csv').stat().st_size>5 else pd.DataFrame()
    OP=[[r.ticker,str(r.entry_date)[:10],r.entry_time,round(r.entry_price,4),int(round(r.shares/100)),round(r.last_close,4),round(r.market_value,2),round(r.unrealized_pnl,2),round(r.unrealized_return,6),str(r.pending_exit) if isinstance(r.pending_exit,str) else '']
        for r in op.itertuples()] if len(op) else []
    isg=pd.read_csv(OUT/'is_grid.csv')
    ISG=[[int(r.channel),r.er_min,int(r.sma_exit),r.fade_atr,r.gap,r.cagr,r.mdd,int(r.trades),r.smoothed_cagr] for r in isg.itertuples()]
    st=load_stocks();nonint=int((abs(st.Open-st.Open.round())>1e-6).sum())
    res['data_facts']=dict(rows=int(len(st)),tickers=int(st.Ticker.nunique()),noninteger_opens=nonint,first=str(st['Date/Time'].min().date()),last=str(st['Date/Time'].max().date()),
        tickers_ending_before_2025=int((st.groupby('Ticker')['Date/Time'].max()<'2025-01-01').sum()),tickers_listed_after_2005=int((st.groupby('Ticker')['Date/Time'].min()>'2005-12-31').sum()))
    fw=OUT/'forward_results.json'
    if fw.exists():res['forward']=json.load(open(fw))
    payload=dict(RES=clean(res),EQ=EQ,TR=clean(TR),OP=clean(OP),ISG=clean(ISG),WFC=clean(res.get('walk_forward_curve',[])))
    html=TEMPLATE
    for k,v in payload.items():
        html=html.replace(f'/*__{k}__*/null',json.dumps(v,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
    path=OUT/'UTS_NIM_Nama.html';path.write_text(html,encoding='utf-8')
    print(path,round(path.stat().st_size/1e6,2),'MB')


TEMPLATE=r"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UTS Dashboard — Breakout Stop ER</title>
<style>
:root{--bg:#f6f7f4;--panel:#ffffff;--ink:#1d2421;--muted:#5d6762;--line:#dfe3df;--accent:#0f6b5c;--accent2:#b5651d;--bench:#7d858a;--good:#1f7a3f;--bad:#b42318;--warn:#a15c07;--soft:#eef2ee;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#121514;--panel:#1a1f1d;--ink:#e6ebe8;--muted:#9aa5a0;--line:#2c3431;--accent:#46c2a8;--accent2:#e3a35a;--bench:#9aa3a8;--good:#5fd08a;--bad:#ff7b6e;--warn:#f0b35a;--soft:#222a27;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans)}
header.top{padding:28px max(16px,4vw) 18px;border-bottom:1px solid var(--line);background:var(--panel)}
header.top h1{margin:0 0 4px;font-size:26px;letter-spacing:-.01em;text-wrap:balance}
header.top .sub{color:var(--muted);max-width:80ch}
.ident{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px 18px;margin-top:14px;font-size:14px}
.ident div span{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.ph{background:#fff3c4;color:#5a4300;padding:0 4px;border-radius:3px}
@media (prefers-color-scheme:dark){.ph{background:#4a3d0f;color:#ffe9a8}}
nav{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--line);display:flex;gap:4px;overflow-x:auto;padding:6px max(16px,4vw)}
nav a{color:var(--muted);text-decoration:none;font-size:13px;padding:6px 10px;border-radius:6px;white-space:nowrap}
nav a:hover,nav a:focus{background:var(--soft);color:var(--ink);outline:none}
main{padding:20px max(16px,4vw) 60px;display:flex;flex-direction:column;gap:22px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px;min-width:0}
section>h2{margin:0 0 4px;font-size:20px}
h3{font-size:16px;margin:18px 0 6px}
.note{color:var(--muted);font-size:13px;margin:2px 0 12px;max-width:95ch}
p{max-width:95ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
.card{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--bg)}
.card .k{font-size:12px;color:var(--muted)}
.card .v{font-size:22px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:2px}
.card .s{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.card.main .v{color:var(--accent)}
.tw{overflow-x:auto;max-width:100%}
table{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums;width:100%}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{color:var(--muted);font-weight:600;background:var(--panel);position:sticky;top:0}
td.l,th.l{text-align:left}
tr.hl td{background:var(--soft);font-weight:600}
.pos{color:var(--good)}.neg{color:var(--bad)}
.badge{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;font-weight:600}
.b-ok{background:#dff3e6;color:#145c2e}.b-no{background:#fde4e1;color:#8a1c12}.b-warn{background:#fff0d4;color:#7a4500}
@media (prefers-color-scheme:dark){.b-ok{background:#16351f;color:#8fe0a9}.b-no{background:#3d1712;color:#ffb1a6}.b-warn{background:#3d2a0b;color:#ffd38a}}
.chart{width:100%;position:relative}
.chart svg{width:100%;height:auto;display:block}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--muted);margin:4px 0}
.legend i{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:5px;border-radius:2px}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:4px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.12);white-space:nowrap}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:18px}
.rules li{margin:3px 0}
code,.mono{font-family:var(--mono);font-size:12.5px}
input[type=search]{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);width:min(420px,100%)}
.logwrap{max-height:560px;overflow:auto;border:1px solid var(--line);border-radius:8px}
.heat td{min-width:64px;color:#111}
.small{font-size:12px;color:var(--muted)}
details summary{cursor:pointer;color:var(--accent);margin:6px 0}
</style>
</head>
<body>
<header class="top">
  <h1>Breakout Stop ER — Dashboard Backtest Algoritma Trading</h1>
  <div class="sub">Breakout harian saham BEI Kompas100 dengan order buy stop di level tertinggi 20 hari, filter Efficiency Ratio, keluar saat momentum pudar. Semua angka sesudah fee dan spread kecuali disebut lain.</div>
  <div class="ident">
    <div><span>Nama</span><b class="ph">[isi nama]</b></div>
    <div><span>NIM</span><b class="ph">[isi NIM]</b></div>
    <div><span>Kelas</span><b class="ph">[isi kelas]</b></div>
    <div><span>Strategi</span><b>Breakout Stop ER</b></div>
    <div><span>Tanggal pembekuan</span><b id="freeze"></b></div>
    <div><span>Periode backtest</span><b id="period"></b></div>
  </div>
</header>
<nav aria-label="Navigasi bagian">
  <a href="#ringkasan">Ringkasan</a><a href="#aturan">Aturan</a><a href="#ekuitas">Ekuitas</a><a href="#bulanan">Return bulanan</a><a href="#histogram">Histogram</a>
  <a href="#val-a">A. Anti-overfitting</a><a href="#val-b">B. Forward test</a><a href="#val-c">C. Look-ahead</a><a href="#val-d">D. Eksekusi</a>
  <a href="#bahaya">Tanda bahaya</a><a href="#log">Log trade</a><a href="#keterbatasan">Keterbatasan</a><a href="#ai">Keaslian &amp; AI</a><a href="#pelajaran">Pelajaran</a><a href="#checklist">Checklist</a>
</nav>
<main>
<section id="ringkasan">
  <h2>Ringkasan metrik</h2>
  <p class="note" id="sumnote"></p>
  <h3>Metrik utama</h3><div class="cards" id="cards-main"></div>
  <h3>Metrik pelengkap</h3><div class="cards" id="cards-sup"></div>
  <h3>Metrik tambahan</h3><div class="cards" id="cards-bonus"></div>
  <h3>In-sample, out-of-sample, dan periode penuh</h3>
  <p class="note">In-sample = 70% awal rentang kalender, out-of-sample = 30% akhir. Dua versi ditampilkan. (1) Run terpisah: mulai lagi dari modal awal yang sama (indikator dihangatkan dengan data sebelumnya); karena batas likuiditas 5% bergantung pada ukuran akun, run ini tidak sama dengan potongan run utama. (2) Potongan kontinu: sub-periode dari satu run utama tanpa reset modal (dapat dihitung ulang dari kurva ekuitas dan log trade di file ini). Parameter hanya dipilih dari in-sample.</p>
  <div class="tw"><table id="t-isoos"></table></div>
  <h3>Hitung ulang dari data tertanam</h3>
  <p class="note">Angka di bawah dihitung ulang oleh browser langsung dari JSON log trade dan kurva ekuitas harian di file ini, lalu dibandingkan dengan hasil Python.</p>
  <div class="tw"><table id="t-recalc"></table></div>
</section>

<section id="aturan">
  <h2>Aturan strategi</h2>
  <p class="note">Ditulis agar bisa ditiru tanpa penilaian subjektif. i = hari perdagangan saat order dieksekusi; semua informasi yang dipakai sebelum Open hari i berasal dari bar i−1 atau lebih awal.</p>
  <div class="grid2">
  <div>
  <h3>Masuk (buy stop)</h3>
  <ol class="rules">
    <li>Sebelum Open hari i, untuk setiap saham yang belum dipegang: <b>level</b> = High tertinggi <b>N</b> bar sebelumnya (bar i−N … i−1).</li>
    <li>Saham <b>siap</b> bila Close[i−1] ≤ level dan Efficiency Ratio 20 bar (Kaufman) pada Close[i−1] ≥ <b>θ</b>.</li>
    <li>Saham siap diurutkan menurut momentum 120 hari yang melewati 20 hari terakhir: ln(Close[i−21] ÷ Close[i−141]); terbesar dahulu.</li>
    <li>Order buy stop di harga level dipasang untuk K saham teratas, K = slot kosong saat Open. Saham yang Open-nya &gt; level × (1+<b>g</b>) dilewati (order dibatalkan saat Open) dan slot ordernya diberikan ke saham berikutnya.</li>
    <li>Order terisi hanya bila High[i] &gt; level. Harga acuan = max(Open[i], level): bila Open sudah di atas level (gap), order terisi di Open. Tidak pernah diisi di High/Low bar.</li>
  </ol>
  <h3>Keluar</h3>
  <ol class="rules">
    <li>Dinilai di Close hari j: (a) <b>fading</b> bila Open[j] − Low[j] ≥ <b>k</b> × ATR14 (ATR Wilder yang diketahui sebelum bar j); atau (b) Close[j] &lt; SMA(<b>M</b>) Close.</li>
    <li>Dijual di Open hari perdagangan berikutnya. Bila Open itu gap turun lebih dari <b>g</b> di bawah Close sebelumnya, penjualan dipindah ke Close hari itu (sesi penutupan).</li>
    <li>Tidak ada stop intrahari pada hari pembelian; tidak ada short, margin, atau leverage.</li>
  </ol>
  </div>
  <div>
  <h3>Ukuran posisi dan portofolio</h3>
  <ul class="rules">
    <li>Modal awal <b id="cap"></b>, maksimal <b>10 posisi</b>, satu posisi per saham.</li>
    <li>Tiap pembelian = ekuitas Close hari sebelumnya ÷ 10, dibatasi kas tersedia dan <b>5% rata-rata nilai transaksi harian 20 hari terakhir</b> (Close × Volume, bar i−20 … i−1).</li>
    <li>Jumlah saham dibulatkan ke bawah ke kelipatan 1 lot (100 lembar). Keuntungan diputar kembali (compounding).</li>
  </ul>
  <h3>Parameter</h3>
  <div class="tw"><table id="t-params"></table></div>
  <p class="small">Parameter tetap (tidak dioptimasi): ER 20 bar, ATR 14, momentum 120/20 hari, 10 slot, 10% per posisi.</p>
  <h3>Universe, data, periode</h3>
  <ul class="rules" id="datafacts"></ul>
  </div>
  </div>
</section>

<section id="ekuitas">
  <h2>Kurva ekuitas dan drawdown</h2>
  <p class="note">Skala logaritmik. Pembanding beli-dan-tahan = 1% modal per saham dari 100 saham yang sama, dibeli sekali dan ditahan tanpa rebalancing (jatah saham yang baru tercatat ditahan tunai sampai ada harga). IHSG tidak tersedia di lingkungan ini; pembanding ini membawa survivorship bias universe. Sebagai referensi terpisah, indeks equal-weight yang di-rebalance harian tanpa biaya (bukan buy-and-hold, tidak bisa dieksekusi) ditampilkan di tabel bawah. Garis putus-putus = batas in-sample/out-of-sample.</p>
  <div class="legend"><span><i style="background:var(--accent)"></i>Strategi (sesudah biaya)</span><span><i style="background:var(--bench)"></i>Beli-dan-tahan 100 saham (tanpa rebalancing)</span></div>
  <div class="chart" id="c-eq"></div>
  <div class="chart" id="c-dd"></div>
  <div class="tw"><table id="t-bh"></table></div>
</section>

<section id="bulanan">
  <h2>Return bulanan dan tahunan</h2>
  <p class="note">Return bulanan = ekuitas akhir bulan ÷ ekuitas akhir bulan sebelumnya − 1 (bulan pertama terhadap modal awal). Kolom “Tahun” = return kalender tahunan.</p>
  <div class="tw"><table id="t-month"></table></div>
  <h3>Return per tahun: strategi vs beli-dan-tahan</h3>
  <div class="chart" id="c-year"></div>
</section>

<section id="histogram">
  <h2>Histogram hasil trade</h2>
  <p class="note">Hasil bersih per trade tertutup (% terhadap modal yang dipakai trade itu, sesudah fee dan spread). Bin 2%.</p>
  <div class="chart" id="c-hist"></div>
</section>

<section id="val-a">
  <h2>A. Anti-overfitting</h2>
  <h3>In-sample vs out-of-sample</h3>
  <p class="note" id="selnote"></p>
  <div class="tw"><table id="t-isoos2"></table></div>
  <details><summary>Lihat seluruh 243 kombinasi grid in-sample</summary><div class="tw" style="max-height:420px"><table id="t-isgrid"></table></div></details>
  <h3>Walk-forward (6 jendela)</h3>
  <p class="note">Tiap jendela: parameter dipilih di 6 tahun latih dengan aturan yang sama (CAGR rata-rata titik grid dan tetangganya), lalu diuji tanpa diubah di 3 tahun berikutnya. Kurva gabungan out-of-sample = return jendela uji yang disambung.</p>
  <div class="tw"><table id="t-wf"></table></div>
  <div class="chart" id="c-wf"></div>
  <h3>Sensitivitas parameter ±20% dan ±50%</h3>
  <p class="note">Satu parameter diubah, lainnya tetap di nilai terpilih. CAGR periode penuh dan out-of-sample sesudah biaya.</p>
  <div class="tw"><table id="t-sens"></table></div>
  <h3>Heatmap CAGR periode penuh: N (channel) × θ (ER minimum)</h3>
  <div class="tw"><table id="t-heat" class="heat"></table></div>
  <p class="small" id="plateau"></p>
  <h3>Uji ketahanan</h3>
  <div class="tw"><table id="t-robust"></table></div>
  <h3>Pembanding entry acak</h3>
  <p class="note">20 run dengan entry acak (urutan acak, sinyal acak per saham per hari), memakai aturan keluar, ukuran posisi, dan biaya yang sama. Peringatan: entry acak menghasilkan jauh lebih banyak trade yang sebagian besar keluar setelah 1 bar, sehingga perbandingan ini terutama mengukur beban biaya perputaran, bukan bukti kuat tentang nilai tambah sinyal.</p>
  <div class="chart" id="c-rand"></div>
  <h3>Pasar lain dengan parameter yang sama</h3>
  <div class="tw"><table id="t-other"></table></div>
  <p class="small" id="combos"></p>
</section>

<section id="val-b">
  <h2>B. Forward test</h2>
  <div id="fwd"></div>
</section>

<section id="val-c">
  <h2>C. Bebas look-ahead bias</h2>
  <h3>Uji pemotongan data</h3>
  <p class="note">Data dipotong pada tanggal tertentu dan seluruh indikator dihitung ulang hanya dari data terpotong. Bila ada keputusan yang memakai data masa depan, ekuitas atau trade sebelum tanggal potong akan berbeda dari run data penuh.</p>
  <div class="tw"><table id="t-trunc"></table></div>
  <h3>Uji keterlambatan 1 bar</h3>
  <p class="note">Semua pengisian digeser satu bar: stop yang tersentuh dibeli di Open hari berikutnya, penjualan dilakukan satu Open lebih lambat.</p>
  <div class="tw"><table id="t-delay"></table></div>
  <h3>Pemeriksaan aturan</h3>
  <ul class="rules" id="lacheck"></ul>
</section>

<section id="val-d">
  <h2>D. Eksekusi realistis</h2>
  <h3>Sebelum biaya, sesudah biaya, biaya dua kali lipat</h3>
  <div class="tw"><table id="t-cost"></table></div>
  <h3>Asumsi eksekusi</h3>
  <ul class="rules" id="execlist"></ul>
  <h3>Kapasitas dan diagnosa aturan</h3>
  <p class="note">Batas likuiditas 5% nilai transaksi membuat ukuran posisi tidak bisa terus membesar mengikuti ekuitas; tabel ini menunjukkan dampaknya.</p>
  <div class="tw"><table id="t-cap"></table></div>
</section>

<section id="bahaya">
  <h2>Tanda bahaya</h2>
  <div class="tw"><table id="t-flags"></table></div>
</section>

<section id="log">
  <h2>Log trade</h2>
  <p class="note">Jam: “09:00” = terisi di harga pembukaan, “intraday” = buy stop terisi di level selama sesi (jam pasti tidak tercatat di data harian), “16:00” = sesi penutupan. Biaya = fee beli + fee jual; spread = selisih harga offer/bid terhadap harga acuan. Hasil Rp bersih sesudah fee dan spread.</p>
  <input type="search" id="q" placeholder="Cari saham, tanggal (YYYY-MM-DD), atau alasan keluar…" aria-label="Cari log trade">
  <span class="small" id="qcount"></span>
  <div class="logwrap"><table id="t-log"></table></div>
  <h3>Posisi masih terbuka di akhir periode</h3>
  <p class="note">Dinilai pada harga penutupan terakhir dan tidak dihitung sebagai trade tertutup.</p>
  <div class="tw"><table id="t-open"></table></div>
</section>

<section id="keterbatasan">
  <h2>Keterbatasan dan risiko</h2>
  <ul class="rules" id="limits"></ul>
</section>

<section id="ai">
  <h2>Pernyataan keaslian dan penggunaan AI</h2>
  <p><span class="ph">[Tulis pernyataan keaslian Anda sendiri di sini.]</span></p>
  <p>Alat AI yang dipakai: <b>Claude Code (Anthropic)</b>. Bagian yang dibantu AI: penulisan kode backtest Python (folder <code>uts/</code>: data, indikator, mesin eksekusi, metrik, pengujian), pembuatan dashboard HTML ini, serta penyusunan teks penjelasan. Ide strategi, pilihan aset, dan arahan riset berasal dari pengguna; seluruh angka berasal dari kode yang dilampirkan dan dapat dijalankan ulang (<code>python -m uts.run_uts</code> lalu <code>python -m uts.build_dashboard</code>).</p>
</section>

<section id="pelajaran">
  <h2>Pelajaran yang didapat</h2>
  <ul class="rules">
    <li>Hasil terbaik dari satu run tidak cukup: angka resmi baru bermakna setelah ada biaya nyata, pembatas likuiditas, uji tunda 1 bar, dan uji potong data.</li>
    <li>Aturan eksekusi sangat menentukan: tanpa penyeleksian order sebelum Open, pilihan saham memakai informasi intrahari (look-ahead) dan hasil tampak lebih bagus dari yang bisa dieksekusi.</li>
    <li>Definisi metrik harus dinyatakan: persentase bulan rekor berubah bila puncak dihitung dari harian atau akhir bulan, dan beli-dan-tahan berbeda jauh dari indeks yang di-rebalance harian.</li>
    <li>Pemisahan data hanya melindungi parameter, bukan bentuk strategi yang dipilih setelah melihat data yang sama; forward test sesudah tanggal beku adalah satu-satunya bukti yang benar-benar baru.</li>
  </ul>
</section>
<section id="checklist">
  <h2>Daftar periksa sebelum upload</h2>
  <div class="tw"><table id="t-check"></table></div>
</section>
</main>

<script type="application/json" id="d-res">/*__RES__*/null</script>
<script type="application/json" id="d-eq">/*__EQ__*/null</script>
<script type="application/json" id="d-tr">/*__TR__*/null</script>
<script type="application/json" id="d-op">/*__OP__*/null</script>
<script type="application/json" id="d-isg">/*__ISG__*/null</script>
<script type="application/json" id="d-wfc">/*__WFC__*/null</script>
<script>
(function(){
const J=id=>JSON.parse(document.getElementById(id).textContent);
const R=J('d-res'),EQ=J('d-eq'),TR=J('d-tr'),OP=J('d-op'),ISG=J('d-isg'),WFC=J('d-wfc');
const $=id=>document.getElementById(id);
const nf=(d)=>new Intl.NumberFormat('id-ID',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(x,d=1)=>x==null?'—':nf(d).format(x*100)+'%';
const num=(x,d=2)=>x==null?'—':nf(d).format(x);
const rp=x=>{if(x==null)return '—';const a=Math.abs(x),s=x<0?'−':'';if(a>=1e12)return s+'Rp'+nf(2).format(a/1e12)+' T';if(a>=1e9)return s+'Rp'+nf(2).format(a/1e9)+' M';if(a>=1e6)return s+'Rp'+nf(1).format(a/1e6)+' jt';return s+'Rp'+nf(0).format(a)};
const cls=x=>x==null?'':(x>0?'pos':(x<0?'neg':''));
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const M=R.main,meta=R.meta,CH=R.chosen;
$('freeze').textContent=meta.freeze_date;$('period').textContent=meta.start+' s.d. '+meta.end;$('cap').textContent=rp(meta.capital);
function table(el,head,rows,opt={}){const t=$(el);let h='<thead><tr>'+head.map((c,i)=>`<th class="${i<(opt.left||1)?'l':''}">${c}</th>`).join('')+'</tr></thead><tbody>';
 for(const r of rows){h+=`<tr class="${r.hl?'hl':''}">`+r.c.map((c,i)=>`<td class="${i<(opt.left||1)?'l':''} ${c&&c.cl||''}">${c&&c.v!==undefined?c.v:c}</td>`).join('')+'</tr>'}t.innerHTML=h+'</tbody>'}
const V=(v,cl='')=>({v,cl});
function cards(el,items){$(el).innerHTML=items.map(([k,v,s,main])=>`<div class="card ${main?'main':''}"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s||''}</div></div>`).join('')}
cards('cards-main',[['CAGR',pct(M.cagr,2),'(akhir ÷ awal)^(1/tahun) − 1',1],['Win ratio',pct(M.win_ratio),M.trades+' trade tertutup',1],
 ['Avg profit',pct(M.avg_profit_pct,2),rp(M.avg_profit_rp)+' per trade untung',1],['Avg loss',pct(M.avg_loss_pct,2),rp(M.avg_loss_rp)+' per trade rugi',1],
 ['Profit factor',num(M.profit_factor),'laba trade untung ÷ |rugi trade rugi| (Rp)',1],['% bulan rekor baru',pct(M.record_month_pct),M.record_months+' dari '+M.months+' bulan',1]]);
cards('cards-sup',[['Max drawdown',pct(M.mdd,1),'ekuitas harian, mark-to-market'],['Bulan terlama tanpa rekor',num(M.longest_months_without_record,1)+' bln',M.longest_without_record_open?'masih berjalan di akhir periode':'sudah berakhir (ekuitas puncak baru)'],
 ['% bulan rekor baru',pct(M.record_month_pct)+'',M.record_months+' dari '+M.months+' bln · ekuitas akhir bulan ≥ puncak harian sampai akhir bulan lalu; versi longgar (hanya bandingkan akhir bulan) = '+M.record_months_monthend_only],['Jumlah trade',M.trades,num(M.trades_per_year,1)+' per tahun'+(M.small_sample?' · sampel kecil':'')],['Rata-rata hari memegang',num(M.avg_hold_days,1)+' hari',num(M.avg_hold_bars,1)+' bar'],
 ['Expectancy',pct(M.expectancy_pct,2),'per trade'],['Payoff ratio',num(M.payoff_ratio),'avg profit ÷ |avg loss|'],['Sharpe (bulanan)',num(M.sharpe_rf0),'rf 0% · rf 3%: '+num(M.sharpe_rf3)+' · rf 6%: '+num(M.sharpe_rf6)],['Calmar',num(M.calmar),'CAGR ÷ |MDD|'],
 ['Exposure',pct(M.exposure_days_pct),'hari dengan posisi terbuka'],['Modal terpakai',pct(M.avg_capital_used),'rata-rata nilai pasar ÷ ekuitas'],
 ['Beli-dan-tahan 100 saham',pct(M.bh_cagr,2),'MDD '+pct(M.bh_mdd)],['Porsi biaya',pct(M.cost_share_of_gross_profit),'(fee+spread) ÷ laba kotor sebelum biaya, trade tertutup saja']]);
cards('cards-bonus',[['Sortino (bulanan)',num(M.sortino_rf0),'rf = 0%'],['Kekalahan beruntun terpanjang',M.longest_losing_streak+' trade','diurut menurut tanggal keluar lalu tanggal masuk'],
 ['Kontribusi 10 trade terbaik',pct(M.top10_share_of_net_profit),'dari laba bersih trade tertutup'],['Tahun rugi',M.losing_years+' dari '+M.years_count,''],
 ['Ekuitas akhir',rp(M.equity_end),'dari '+rp(M.equity_start)],['Posisi terbuka di akhir',M.open_positions,'unrealized '+rp(M.open_unrealized_pnl)]]);
$('sumnote').textContent=`Periode penuh ${M.start} s.d. ${M.end} (${num(M.years,2)} tahun). Eksekusi resmi: fee beli 0,15% dan jual 0,25%, beli di offer dan jual di bid (1 fraksi harga), lot 100, ARA/ARB, batas likuiditas 5% ADV20 (hanya order beli; penjualan tidak dibatasi), modal ${rp(meta.capital)}, compounding.`;
const isoRow=(n,m)=>({c:[n,V(pct(m.cagr,2),cls(m.cagr)),pct(m.win_ratio),pct(m.avg_profit_pct,2),V(pct(m.avg_loss_pct,2),'neg'),num(m.profit_factor),pct(m.record_month_pct),pct(m.mdd),num(m.sharpe_rf0),m.trades,m.start+' – '+m.end]});
const isoHead=['Bagian','CAGR','Win ratio','Avg profit','Avg loss','PF','% bulan rekor','MDD','Sharpe','Trade','Periode'];
table('t-isoos',isoHead,[isoRow('In-sample (70%) · run terpisah',R.in_sample),isoRow('Out-of-sample (30%) · run terpisah',R.out_of_sample),isoRow('In-sample · potongan kontinu',R.in_sample_continuous),isoRow('Out-of-sample · potongan kontinu',R.out_of_sample_continuous),{...isoRow('Periode penuh',M),hl:1}]);
table('t-isoos2',isoHead,[isoRow('In-sample (70%) · run terpisah',R.in_sample),isoRow('Out-of-sample (30%) · run terpisah',R.out_of_sample),isoRow('In-sample · potongan kontinu',R.in_sample_continuous),isoRow('Out-of-sample · potongan kontinu',R.out_of_sample_continuous)]);
// Recalculation in the browser.
(function(){const cap=meta.capital,n=TR.length;const pnl=TR.map(t=>t[12]),ret=TR.map(t=>t[13]);const w=pnl.filter(x=>x>0),l=pnl.filter(x=>x<0);
 const wr=w.length/n,pf=w.reduce((a,b)=>a+b,0)/-l.reduce((a,b)=>a+b,0);const ap=ret.filter((r,i)=>pnl[i]>0),al=ret.filter((r,i)=>pnl[i]<0);
 const mean=a=>a.reduce((x,y)=>x+y,0)/a.length;const d0=new Date(EQ[0][0]),d1=new Date(EQ[EQ.length-1][0]);const yrs=(d1-d0)/864e5/365.25;
 const cg=Math.pow(EQ[EQ.length-1][1]/cap,1/yrs)-1;let pk=-1,mdd=0;for(const e of EQ){pk=Math.max(pk,e[1]);mdd=Math.min(mdd,e[1]/pk-1)}
 const me={};for(const e of EQ)me[e[0].slice(0,7)]=e[1];const ks=Object.keys(me).sort();let prev=cap,rec=0;for(const k of ks){if(me[k]>=prev)rec++;prev=Math.max(prev,me[k])}
 const rows=[['CAGR',cg,M.cagr,4],['Win ratio',wr,M.win_ratio,6],['Avg profit (%)',mean(ap),M.avg_profit_pct,6],['Avg loss (%)',mean(al),M.avg_loss_pct,6],['Profit factor',pf,M.profit_factor,6],['% bulan rekor',rec/ks.length,M.record_month_pct,6],['MDD',mdd,M.mdd,6]];
 table('t-recalc',['Metrik','Dihitung browser','Hasil Python','Cocok'],rows.map(([k,a,b,d])=>({c:[k,num(a,d),num(b,d),Math.abs(a-b)<1e-6*Math.max(1,Math.abs(b))?'<span class="badge b-ok">cocok</span>':'<span class="badge b-no">beda</span>']})))})();
// Parameters.
const PN={channel:['N','Panjang channel HHV'],er_min:['θ','ER minimum'],sma_exit:['M','SMA keluar'],fade_atr:['k','Fading ATR'],gap:['g','Batas gap']};
table('t-params',['Simbol','Parameter','Terpilih (in-sample)','Grid dicoba'],Object.keys(PN).map(k=>({c:[PN[k][0],PN[k][1],V('<b>'+(k=='gap'?pct(CH[k],1):CH[k])+'</b>'),meta.grid[k].map(v=>k=='gap'?pct(v,0):v).join(' · ')]})),{left:2});
const DF=R.data_facts;$('datafacts').innerHTML=[`Universe: ${DF.tickers} saham dalam file <code>Data kompas 100.csv</code> (${num(DF.rows,0)} bar harian, ${DF.first} s.d. ${DF.last}).`,
 `Sumber data: <span class="ph">[isi sumber, mis. export AmiBroker/TradingView/Yahoo, dan tanggal unduh]</span>.`,`Timeframe: harian. Periode: ${meta.start} s.d. ${meta.end}; in-sample s.d. ${meta.is_end}, out-of-sample mulai ${meta.oos_start}.`,
 `Pembersihan: bar bercap waktu intrahari dibuang; High = max(OHLC), Low = min(OHLC); bar dengan Volume 0 dianggap tidak bisa diperdagangkan.`,
 `Harga tampak sudah disesuaikan aksi korporasi: ${num(DF.noninteger_opens,0)} harga Open bukan bilangan bulat. Penyesuaian diasumsikan konsisten dari sumber; faktor penyesuaian mentah tidak tersedia.`].map(x=>'<li>'+x+'</li>').join('');
// ---------- Charts ----------
const NS='http://www.w3.org/2000/svg';
function svg(w,h){const s=document.createElementNS(NS,'svg');s.setAttribute('viewBox',`0 0 ${w} ${h}`);s.setAttribute('role','img');return s}
function el(n,a,p){const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function txt(p,x,y,t,a={}){const e=el('text',{x,y,'font-size':11,fill:css('--muted'),...a},p);e.textContent=t;return e}
function lineChart(host,series,{log=false,h=320,yfmt=v=>v,ref=null,marker=null}={}){
 const box=$(host);box.innerHTML='';const W=Math.max(320,box.clientWidth||900),H=h,ml=70,mr=12,mt=10,mb=26;const s=svg(W,H);box.appendChild(s);
 const all=series.flatMap(x=>x.pts);const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]).filter(v=>v>0||!log);
 const x0=Math.min(...xs),x1=Math.max(...xs);let y0=Math.min(...ys),y1=Math.max(...ys);if(ref!=null){y0=Math.min(y0,ref);y1=Math.max(y1,ref)}
 const f=log?Math.log10:v=>v;const fy0=f(y0)-(f(y1)-f(y0))*.03,fy1=f(y1)+(f(y1)-f(y0))*.03;
 const X=t=>ml+(t-x0)/(x1-x0)*(W-ml-mr),Y=v=>mt+(1-(f(v)-fy0)/(fy1-fy0))*(H-mt-mb);
 let ticks=[];if(log){for(let e=Math.floor(fy0);e<=Math.ceil(fy1);e++)for(const m of [1,2,5]){const v=m*Math.pow(10,e);if(f(v)>=fy0&&f(v)<=fy1)ticks.push(v)}if(ticks.length>8)ticks=ticks.filter(v=>Math.abs(Math.log10(v)%1)<1e-9)}
 else{const st=(fy1-fy0)/5;for(let i=0;i<=5;i++)ticks.push(fy0+st*i)}
 for(const v of ticks){const y=Y(v);el('line',{x1:ml,x2:W-mr,y1:y,y2:y,stroke:css('--line')},s);txt(s,ml-6,y+4,yfmt(v),{'text-anchor':'end'})}
 const y0d=new Date(x0).getFullYear(),y1d=new Date(x1).getFullYear();const stp=Math.max(1,Math.ceil((y1d-y0d)/Math.floor((W-ml)/60)));
 for(let y=y0d;y<=y1d;y+=stp){const t=Date.UTC(y,0,1);if(t<x0)continue;txt(s,X(t),H-8,String(y),{'text-anchor':'middle'})}
 if(marker!=null){const xm=X(marker);el('line',{x1:xm,x2:xm,y1:mt,y2:H-mb,stroke:css('--muted'),'stroke-dasharray':'4 4'},s)}
 for(const sr of series){let d='';sr.pts.forEach((p,i)=>{if(log&&p[1]<=0)return;d+=(d?'L':'M')+X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)});el('path',{d,fill:'none',stroke:sr.color,'stroke-width':sr.w||1.8,'stroke-linejoin':'round'},s)}
 const tip=document.createElement('div');tip.className='tip';tip.hidden=true;box.appendChild(tip);const vl=el('line',{y1:mt,y2:H-mb,stroke:css('--muted'),visibility:'hidden'},s);
 s.addEventListener('pointermove',ev=>{const r=s.getBoundingClientRect();const px=(ev.clientX-r.left)*W/r.width;const t=x0+(px-ml)/(W-ml-mr)*(x1-x0);
  const pts=series.map(sr=>{let lo=0,hi=sr.pts.length-1;while(hi-lo>1){const m=(lo+hi)>>1;if(sr.pts[m][0]<t)lo=m;else hi=m}return [sr,sr.pts[hi]]});
  if(!pts[0][1])return;vl.setAttribute('x1',X(pts[0][1][0]));vl.setAttribute('x2',X(pts[0][1][0]));vl.setAttribute('visibility','visible');
  tip.innerHTML='<b>'+new Date(pts[0][1][0]).toISOString().slice(0,10)+'</b><br>'+pts.map(([sr,p])=>`<span style="color:${sr.color}">■</span> ${sr.name}: ${yfmt(p[1])}`).join('<br>');
  tip.hidden=false;const lx=ev.clientX-r.left;tip.style.left=Math.min(lx+12,r.width-tip.offsetWidth-4)+'px';tip.style.top='8px'});
 s.addEventListener('pointerleave',()=>{tip.hidden=true;vl.setAttribute('visibility','hidden')});return s}
function barChart(host,cats,series,{h=260,yfmt=v=>pct(v,0)}={}){
 const box=$(host);box.innerHTML='';const W=Math.max(320,box.clientWidth||900),H=h,ml=56,mr=10,mt=10,mb=26;const s=svg(W,H);box.appendChild(s);
 const vals=series.flatMap(x=>x.v).filter(v=>v!=null);let y0=Math.min(0,...vals),y1=Math.max(0,...vals);const pad=(y1-y0)*.05;y0-=pad;y1+=pad;
 const Y=v=>mt+(1-(v-y0)/(y1-y0))*(H-mt-mb);const bw=(W-ml-mr)/cats.length;
 for(let i=0;i<=5;i++){const v=y0+(y1-y0)*i/5;el('line',{x1:ml,x2:W-mr,y1:Y(v),y2:Y(v),stroke:css('--line')},s);txt(s,ml-6,Y(v)+4,yfmt(v),{'text-anchor':'end'})}
 el('line',{x1:ml,x2:W-mr,y1:Y(0),y2:Y(0),stroke:css('--muted')},s);
 const gw=bw*.8/series.length;const step=Math.max(1,Math.ceil(cats.length/Math.floor((W-ml)/40)));
 cats.forEach((c,i)=>{series.forEach((sr,j)=>{const v=sr.v[i];if(v==null)return;const x=ml+i*bw+bw*.1+j*gw;const y=Y(Math.max(v,0)),hh=Math.abs(Y(v)-Y(0));
  const r=el('rect',{x,y,width:Math.max(1,gw-1),height:Math.max(.5,hh),fill:sr.color,rx:1.5},s);const t=el('title',{},r);t.textContent=c+' · '+sr.name+': '+yfmt(v)});
  if(i%step==0)txt(s,ml+i*bw+bw/2,H-8,String(c),{'text-anchor':'middle'})});return s}
const T=d=>Date.parse(d+'T00:00:00Z');
lineChart('c-eq',[{name:'Strategi',color:css('--accent'),w:2.2,pts:EQ.map(e=>[T(e[0]),e[1]])},{name:'Beli-dan-tahan 100 saham (tanpa rebalancing)',color:css('--bench'),pts:EQ.map(e=>[T(e[0]),e[5]])}],{log:true,h:340,yfmt:rp,marker:T(meta.is_end)});
(function(){const box=$('c-dd');const W=Math.max(320,box.clientWidth||900),H=150,ml=70,mr=12,mt=8,mb=22;const s=svg(W,H);box.appendChild(s);
 const x0=T(EQ[0][0]),x1=T(EQ[EQ.length-1][0]);const mn=Math.min(...EQ.map(e=>e[2]));const X=t=>ml+(t-x0)/(x1-x0)*(W-ml-mr),Y=v=>mt+(v/mn)*(H-mt-mb);
 let pk=-1;const bd=EQ.map(e=>{pk=Math.max(pk,e[5]);return e[5]/pk-1});
 for(const v of [0,mn/2,mn]){el('line',{x1:ml,x2:W-mr,y1:Y(v),y2:Y(v),stroke:css('--line')},s);txt(s,ml-6,Y(v)+4,pct(v,0),{'text-anchor':'end'})}
 let d='M'+X(x0)+','+Y(0);EQ.forEach(e=>d+='L'+X(T(e[0])).toFixed(1)+','+Y(e[2]).toFixed(1));d+='L'+X(x1)+','+Y(0)+'Z';el('path',{d,fill:css('--accent'),opacity:.35},s);
 let d2='';EQ.forEach((e,i)=>d2+=(i?'L':'M')+X(T(e[0])).toFixed(1)+','+Y(Math.max(bd[i],mn)).toFixed(1));el('path',{d:d2,fill:'none',stroke:css('--bench'),'stroke-width':1},s);
 txt(s,ml+4,mt+12,'Drawdown strategi (area) dan beli-dan-tahan (garis)')})();
table('t-bh',['Seri','CAGR','MDD'],[{c:['Strategi (sesudah biaya)',pct(M.cagr,2),pct(M.mdd)]},{c:['Beli-dan-tahan 100 saham (tanpa rebalancing)',pct(M.bh_cagr,2),pct(M.bh_mdd)]},{c:['Referensi: equal-weight rebalance harian tanpa biaya',pct(R.bench_rebal_cagr,2),pct(R.bench_rebal_mdd)]}]);
// Monthly table.
(function(){const mr=R.monthly_returns,yr=R.yearly_returns;const years=[...new Set(Object.keys(mr).map(k=>k.slice(0,4)))];const mo=['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
 const col=v=>{if(v==null)return '';const a=Math.min(1,Math.abs(v)/.15);return v>=0?`background:rgba(31,122,63,${.12+.5*a})`:`background:rgba(180,35,24,${.12+.5*a})`};
 let h='<thead><tr><th class="l">Tahun</th>'+mo.map(m=>'<th>'+m+'</th>').join('')+'<th>Tahun</th></tr></thead><tbody>';
 for(const y of years){h+='<tr><td class="l">'+y+'</td>';for(let m=1;m<=12;m++){const k=Object.keys(mr).find(x=>x.startsWith(y+'-'+String(m).padStart(2,'0')));const v=k?mr[k]:null;h+=`<td style="${col(v)}">${v==null?'':pct(v,1)}</td>`}
  h+=`<td style="${col(yr[y])};font-weight:600">${pct(yr[y],1)}</td></tr>`}$('t-month').innerHTML=h+'</tbody>'})();
barChart('c-year',Object.keys(R.yearly_returns),[{name:'Strategi',color:css('--accent'),v:Object.values(R.yearly_returns)},{name:'Beli-dan-tahan 100 saham (tanpa rebalancing)',color:css('--bench'),v:Object.keys(R.yearly_returns).map(y=>R.bench_yearly[y]??null)}]);
// Histogram.
(function(){const bins={};for(const t of TR){const b=Math.floor(t[13]/.02)*.02;bins[b.toFixed(2)]=(bins[b.toFixed(2)]||0)+1}
 const ks=Object.keys(bins).map(Number).sort((a,b)=>a-b);const lo=Math.max(ks[0],-.3),hi=Math.min(ks[ks.length-1],1);const cats=[],v=[];
 let under=0,over=0;for(const k of ks){if(k<lo)under+=bins[k.toFixed(2)];if(k>hi)over+=bins[k.toFixed(2)]}
 for(let b=lo;b<=hi+1e-9;b+=.02){cats.push(pct(b,0));v.push((bins[b.toFixed(2)]||0)+(Math.abs(b-lo)<1e-9?under:0)+(Math.abs(b-hi)<1e-9?over:0))}
 barChart('c-hist',cats,[{name:'Jumlah trade',color:css('--accent2'),v}],{yfmt:x=>num(x,0)})})();
// A. selection, grid, walk-forward, sensitivity, heatmap, robustness.
$('selnote').innerHTML=`Grid ${Object.values(meta.grid).map(a=>a.length).join('×')} = ${ISG.length} kombinasi, hanya dijalankan pada in-sample (${meta.start} s.d. ${meta.is_end}) sesudah biaya. Aturan pilih ditulis sebelum dijalankan: CAGR rata-rata kombinasi dan tetangga grid satu langkah (mencari dataran, bukan puncak), syarat ≥100 trade dan MDD &gt; −50%. Terpilih: N=${CH.channel}, θ=${CH.er_min}, M=${CH.sma_exit}, k=${CH.fade_atr}, g=${pct(CH.gap,0)}.`;
table('t-isgrid',['N','θ','M','k','g','CAGR IS','MDD IS','Trade','CAGR tetangga'],ISG.sort((a,b)=>b[8]-a[8]).map(r=>({hl:r[0]==CH.channel&&r[1]==CH.er_min&&r[2]==CH.sma_exit&&r[3]==CH.fade_atr&&r[4]==CH.gap,c:[r[0],r[1],r[2],r[3],pct(r[4],0),V(pct(r[5],2),cls(r[5])),pct(r[6]),r[7],pct(r[8],2)]})),{left:0});
table('t-wf',['Jendela latih','Jendela uji','Parameter terpilih (N, θ, M, k, g)','CAGR latih','CAGR uji','MDD uji','Trade','Win ratio','PF','% bln rekor'],R.walk_forward.map(w=>({c:[w.train,w.test,`${w.params.channel}, ${w.params.er_min}, ${w.params.sma_exit}, ${w.params.fade_atr}, ${pct(w.params.gap,0)}`,pct(w.train_cagr,1),V(pct(w.test_cagr,1),cls(w.test_cagr)),pct(w.test_mdd),w.test_trades,pct(w.test_win_ratio),num(w.test_pf),pct(w.test_record_pct)]})),{left:3});
const WC=R.walk_forward_combined;
lineChart('c-wf',[{name:'Gabungan out-of-sample walk-forward',color:css('--accent2'),w:2,pts:WFC.map(e=>[T(e[0]),e[1]])}],{log:true,h:260,yfmt:rp});
$('c-wf').insertAdjacentHTML('beforeend',`<p class="small">Kurva gabungan out-of-sample ${WC.start} s.d. ${WC.end}: CAGR ${pct(WC.cagr,2)}, MDD ${pct(WC.mdd)}.</p>`);
table('t-sens',['Parameter','Pengali','Nilai','CAGR penuh','CAGR OOS','MDD penuh','% bln rekor','Trade'],R.sensitivity.map(s=>({hl:s.mult==1,c:[PN[s.param][1]+' ('+PN[s.param][0]+')',num(s.mult,1)+'×',s.param=='gap'?pct(s.value,1):s.value,V(pct(s.cagr,2),cls(s.cagr)),V(pct(s.oos_cagr,2),cls(s.oos_cagr)),pct(s.mdd),pct(s.record_pct),s.trades]})),{left:1});
(function(){const H=R.heatmap;const cm=[...new Set(H.map(h=>h.ch_mult))],em=[...new Set(H.map(h=>h.er_mult))];const vs=H.map(h=>h.cagr);const lo=Math.min(...vs),hi=Math.max(...vs);
 const col=v=>{const a=(v-lo)/(hi-lo||1);return v<0?`background:rgba(220,60,40,.55)`:`background:rgba(${Math.round(240-150*a)},${Math.round(240-60*a)},${Math.round(220-120*a)},1)`};
 let h='<thead><tr><th class="l">N \\ θ</th>'+em.map(m=>{const x=H.find(h=>h.er_mult==m);return `<th>${x.er_min} (${m}×)</th>`}).join('')+'</tr></thead><tbody>';
 for(const c of cm){const x=H.find(h=>h.ch_mult==c);h+=`<tr><td class="l">${x.channel} (${c}×)</td>`+em.map(m=>{const y=H.find(h=>h.ch_mult==c&&h.er_mult==m);return `<td style="${col(y.cagr)}${c==1&&m==1?';outline:2px solid #111':''}">${pct(y.cagr,1)}</td>`}).join('')+'</tr>'}
 $('t-heat').innerHTML=h+'</tbody>';const allpos=R.sensitivity.every(s=>s.cagr>0)&&H.every(h=>h.cagr>0);
 $('plateau').innerHTML=`Semua ${R.sensitivity.length} varian satu-parameter dan ${H.length} sel heatmap memiliki CAGR ${allpos?'positif':'tidak semuanya positif'}; rentang CAGR heatmap ${pct(lo,1)} s.d. ${pct(hi,1)}. ${allpos?'<span class="badge b-ok">dataran positif</span>':'<span class="badge b-warn">periksa</span>'}`})();
const WT=R.without_top5,BS=R.bootstrap;
table('t-robust',['Uji','Hasil','Keterangan'],[{c:['Tanpa 5 trade terbaik',`CAGR ≈ ${pct(WT.cagr,2)} · PF ${num(WT.profit_factor)} · expectancy ${pct(WT.expectancy_pct,2)}`,`5 trade terbaik (${WT.tickers.join(', ')}) menyumbang ${rp(WT.removed_pnl)}; CAGR didekati dengan menskalakan ekuitas akhir (1 − laba trade ÷ ekuitas saat trade ditutup)`]},
 {c:['Tahun rugi',`${M.losing_years} dari ${M.years_count} tahun`,Object.entries(R.yearly_returns).filter(([y,v])=>v<0).map(([y,v])=>y+' ('+pct(v,1)+')').join(', ')]},
 {c:['Bootstrap urutan trade',`CAGR p5 ${pct(BS.cagr_p5,2)} · median ${pct(BS.cagr_p50,2)} · MDD p5 ${pct(BS.mdd_p5,1)}`,`${BS.n} resampling trade dengan pengembalian; efek trade = laba ÷ ekuitas saat masuk, tumpang tindih posisi diabaikan. Catatan: bootstrap mengacak urutan sehingga MDD p5 lebih ringan dari MDD nyata ${pct(M.mdd,1)}; MDD nyata (periode krisis berkelompok) adalah angka yang berlaku`]}],{left:1});
(function(){const RE=R.random_entry.runs.map(r=>r.cagr).sort((a,b)=>a-b);const box=$('c-rand');box.innerHTML='';
 barChart('c-rand',RE.map((_,i)=>'#'+(i+1)),[{name:'Entry acak',color:css('--bench'),v:RE}],{h:200});
 const better=RE.filter(v=>v>=M.cagr).length;box.insertAdjacentHTML('beforeend',`<p class="small">CAGR strategi ${pct(M.cagr,2)} vs entry acak median ${pct(RE[Math.floor(RE.length/2)],2)} (min ${pct(RE[0],2)}, maks ${pct(RE[RE.length-1],2)}); ${better} dari ${RE.length} run acak menyamai atau melampaui strategi.</p>`)})();
table('t-other',['Pasar','Periode','CAGR','MDD','Trade','Win ratio','PF','Biaya diasumsikan'],[{c:['Crypto (8 koin Binance, harian)',R.crypto.start+' – '+R.crypto.end,V(pct(R.crypto.cagr,2),cls(R.crypto.cagr)),pct(R.crypto.mdd),R.crypto.trades,pct(R.crypto.win_ratio),num(R.crypto.profit_factor),'fee 0,1%/sisi + spread 0,05%/sisi']},
 {c:['Forex (9 pair, sesi harian)',R.forex.start+' – '+R.forex.end,V(pct(R.forex.cagr,2),cls(R.forex.cagr)),pct(R.forex.mdd),R.forex.trades,pct(R.forex.win_ratio),num(R.forex.profit_factor),'spread 0,015%/sisi, tanpa leverage']}],{left:2});
$('combos').innerHTML=`Jumlah kombinasi pada pipeline ini: grid in-sample ${R.pipeline_runs.is_grid}, walk-forward ${R.pipeline_runs.walk_forward}, sensitivitas ${R.pipeline_runs.sensitivity}, entry acak ${R.pipeline_runs.random}. Sebelum pipeline ini, riset di repositori yang sama sudah mencatat sekitar <b>${num(R.research_runs_logged,0)}</b> baris hasil simulasi pada data yang sama (banyak keluarga strategi dan varian), sehingga pemilihan bentuk strategi tidak bebas dari data snooping.`;
// B. forward test.
$('fwd').innerHTML=`<p>Tanggal pembekuan strategi: <b>${R.frozen.date}</b>. Parameter beku: N=${R.frozen.params.channel}, θ=${R.frozen.params.er_min}, M=${R.frozen.params.sma_exit}, k=${R.frozen.params.fade_atr}, g=${pct(R.frozen.params.gap,0)}. Sidik SHA-256 kode: <code>${R.frozen.code_sha256}</code>.</p>
${R.forward?`<p><span class="badge b-ok">Forward test tersedia</span> ${R.forward.start} – ${R.forward.end}: CAGR ${pct(R.forward.cagr,2)}, MDD ${pct(R.forward.mdd)}, ${R.forward.trades} trade. Kode cocok dengan hash beku: ${R.forward.code_ok}.</p>`:''}<p><span class="badge ${R.forward?'b-ok':'b-no'}">${R.forward?'Hasil forward di atas':'Belum ada hasil forward test'}</span> Data di file berakhir ${meta.end}; data sesudah tanggal pembekuan belum tersedia di lingkungan pengerjaan (akses unduh data diblokir). Forward test minimal 4 minggu harus dijalankan sesudah ${R.frozen.date} dengan <code>python -m uts.forward_test --data &lt;csv baru&gt;</code>; skrip itu memakai parameter dan kode beku di atas tanpa perubahan, lalu hasilnya ditampilkan terpisah dari backtest.</p>`;
// C.
table('t-trunc',['Tanggal potong','Hari dibandingkan','Trade dibandingkan','Hasil'],R.truncation_test.map(t=>({c:[t.cut,num(t.days,0),num(t.trades,0),t.identical?'<span class="badge b-ok">identik</span>':'<span class="badge b-no">berbeda</span>']})));
const D=R.delay_1bar,DO=R.delay_1bar_oos;
$('delaynote')&&0;table('t-delay',['Skenario','CAGR penuh','MDD penuh','% bln rekor','PF','CAGR OOS'],[{c:['Normal',pct(M.cagr,2),pct(M.mdd),pct(M.record_month_pct),num(M.profit_factor),pct(R.out_of_sample.cagr,2)]},{c:['Tertunda 1 bar',V(pct(D.cagr,2),cls(D.cagr)),pct(D.mdd),pct(D.record_month_pct),num(D.profit_factor),V(pct(DO.cagr,2),cls(DO.cagr))]}]);
$('lacheck').innerHTML=['Sinyal dari harga penutupan dieksekusi paling cepat di Open bar berikutnya; level buy stop dan semua filter memakai data sampai bar i−1.',
 'Buy stop hanya terisi bila High melewati level; bila Open sudah di atas level, terisi di Open. Tidak ada pengisian di High/Low atau di level yang baru diketahui sesudah bar selesai.',
 'Saat slot terbatas, order hanya dipasang sebelum Open untuk saham peringkat teratas (sebanyak slot kosong); program tidak memilih di antara saham yang ternyata tersentuh pada hari itu.',
 'Indikator: rolling max/mean, ER Kaufman, ATR Wilder, log return — semuanya hanya memakai data lampau. Tidak ada zigzag, pivot yang melukis ulang, moving average terpusat, atau normalisasi seluruh periode. Tidak memakai data fundamental.',
 `Survivorship bias: ${DF.tickers} saham dan tidak satu pun berhenti sebelum 2025 (${DF.tickers_listed_after_2005} baru tercatat sesudah 2005). Ini daftar saham yang bertahan, bukan anggota Kompas100 historis per tanggal; saham yang delisting atau keluar indeks tidak ikut diuji. Akibatnya hasil backtest dan pembanding cenderung terlalu optimistis; besarnya tidak bisa diukur tanpa daftar anggota indeks historis.`,
 `Harga disesuaikan aksi korporasi oleh sumber data (${num(DF.noninteger_opens,0)} Open bukan bilangan bulat). Fraksi harga dan batas ARA/ARB dihitung pada harga yang disesuaikan, sehingga biaya spread di masa lalu hanya pendekatan.`].map(x=>'<li>'+x+'</li>').join('');
// D.
const G=R.gross,DB=R.double_cost,DBO=R.double_cost_oos;
const costRow=(n,m,o)=>({c:[n,V(pct(m.cagr,2),cls(m.cagr)),pct(m.win_ratio),num(m.profit_factor),pct(m.record_month_pct),pct(m.mdd),m.trades,o==null?'—':pct(o,2)]});
table('t-cost',['Skenario','CAGR','Win ratio','PF','% bln rekor','MDD','Trade','CAGR OOS'],[costRow('Sebelum biaya (tanpa fee & spread)',G,null),{...costRow('Sesudah biaya (resmi)',M,R.out_of_sample.cagr),hl:1},costRow('Biaya 2× (fee 0,30%/0,50%, spread 2 fraksi)',DB,DBO.cagr)]);
$('execlist').innerHTML=['Fee broker: beli 0,15%, jual 0,25% (termasuk PPh final 0,1%).','Spread: beli di harga offer = harga acuan dibulatkan ke atas ke fraksi + 1 fraksi; jual di bid = dibulatkan ke bawah − 1 fraksi.',
 'Fraksi harga BEI: &lt;Rp200: Rp1; Rp200–&lt;500: Rp2; Rp500–&lt;2.000: Rp5; Rp2.000–&lt;5.000: Rp10; ≥Rp5.000: Rp25 (berdasarkan Close hari sebelumnya).','Jumlah saham kelipatan 1 lot (100 lembar), tanpa pecahan.',
 'ARA: Rp50–200 35%, &gt;Rp200–5.000 25%, &gt;Rp5.000 20% dari Close sebelumnya; tidak membeli bila harga acuan sudah di batas ARA. ARB simetris kecuali periode asimetris yang diasumsikan: 10% (10–12 Mar 2020), 7% (13 Mar 2020–4 Jun 2023), 15% (5 Jun–3 Sep 2023 dan sejak 8 Apr 2025); tidak menjual bila harga di batas ARB (order menunggu hari berikutnya).',
 'Hari dengan Volume 0 (termasuk suspensi) tidak menghasilkan pengisian order.','Likuiditas: nilai satu order beli maksimal 5% rata-rata nilai transaksi harian (Close × Volume) 20 hari sebelumnya; penjualan tidak dibatasi dan ADV20 adalah rata-rata sehingga satu transaksi blok besar dapat menaikkannya.','Tanpa short selling, margin, atau leverage. Kas menganggur tidak diberi bunga.'].map(x=>'<li>'+x+'</li>').join('');
table('t-cap',['Variasi','CAGR','MDD','% bln rekor','Trade'],[['Modal Rp100 juta',R.capital_100m],['Modal Rp1 miliar (resmi)',M],['Modal Rp10 miliar',R.capital_10bn],['Tanpa batas likuiditas (diagnosa)',R.no_liquidity_cap],['Tanpa ARA/ARB (diagnosa)',R.no_price_limits]].map(([n,m])=>({hl:n.includes('resmi'),c:[n,pct(m.cagr,2),pct(m.mdd),pct(m.record_month_pct),m.trades]})));
// Red flags.
(function(){const top2=TR.map(t=>t[12]).sort((a,b)=>b-a).slice(0,2).reduce((a,b)=>a+b,0)/M.net_profit_closed;const isC=R.in_sample.cagr,ooC=R.out_of_sample.cagr;
 const F=[['CAGR jangka panjang > 100%/tahun',M.cagr>1,`CAGR ${pct(M.cagr,2)}`],['Win ratio > 80% dengan avg loss sangat kecil',M.win_ratio>.8,`Win ratio ${pct(M.win_ratio)}, avg loss ${pct(M.avg_loss_pct,2)}`],
  ['Profit factor > 3 pada periode panjang',M.profit_factor>3,`PF ${num(M.profit_factor)}`],['Kurva ekuitas hampir lurus tanpa drawdown berarti',M.mdd>-.1,`MDD ${pct(M.mdd)}`],
  ['Out-of-sample jauh lebih baik dari in-sample',ooC>isC*1.5&&ooC-isC>.05,`IS ${pct(isC,2)} vs OOS ${pct(ooC,2)}`],['Hasil runtuh saat eksekusi ditunda 1 bar',D.cagr<=0||D.cagr<M.cagr*.3,`Normal ${pct(M.cagr,2)} → tertunda ${pct(D.cagr,2)}`],
  ['Tidak ada satu pun tahun rugi selama 10 tahun',M.losing_years==0,`${M.losing_years} tahun rugi dari ${M.years_count}`],['Sebagian besar laba dari 1–2 trade',top2>.5,`2 trade terbaik = ${pct(top2,1)} laba bersih`]];
 table('t-flags',['Tanda bahaya','Status','Bukti'],F.map(([k,b,e])=>({c:[k,b?'<span class="badge b-warn">terpicu — lihat penjelasan di bagian Keterbatasan</span>':'<span class="badge b-ok">tidak terpicu</span>',e]})),{left:1})})();
// Trade log.
const LH=['#','Saham','Masuk','Jam','Harga masuk','Keluar','Jam','Harga keluar','Lot','Fee','Spread','Hasil Rp','Hasil %','Hari','Alasan keluar'];
function renderLog(f){const q=f.trim().toLowerCase();const rows=q?TR.filter(t=>(t[1]+' '+t[2]+' '+t[5]+' '+t[16]).toLowerCase().includes(q)):TR;
 let h='<thead><tr>'+LH.map((c,i)=>`<th class="${i<2?'l':''}">${c}</th>`).join('')+'</tr></thead><tbody>';
 for(const t of rows)h+=`<tr><td class="l">${t[0]}</td><td class="l">${t[1]}</td><td>${t[2]}</td><td>${t[3]}</td><td>${num(t[4],0)}</td><td>${t[5]}</td><td>${t[6]}</td><td>${num(t[7],0)}</td><td>${num(t[8],0)}</td><td>${num(t[9],0)}</td><td>${num(t[10],0)}</td><td class="${cls(t[12])}">${num(t[12],0)}</td><td class="${cls(t[13])}">${pct(t[13],2)}</td><td>${t[14]}</td><td class="l">${t[16]}</td></tr>`;
 $('t-log').innerHTML=h+'</tbody>';$('qcount').textContent=rows.length+' dari '+TR.length+' trade'}
renderLog('');$('q').addEventListener('input',e=>renderLog(e.target.value));
table('t-open',['Saham','Masuk','Jam','Harga masuk','Lot','Close terakhir','Nilai pasar','Unrealized Rp','Unrealized %','Sinyal keluar tertunda'],OP.map(o=>({c:[o[0],o[1],o[2],num(o[3],0),num(o[4],0),num(o[5],0),rp(o[6]),V(num(o[7],0),cls(o[7])),V(pct(o[8],2),cls(o[8])),o[9]||'—']})),{left:1});
// Limitations.
$('limits').innerHTML=[`Survivorship bias: universe hanya berisi saham yang bertahan sampai 2025; hasil nyata kemungkinan lebih rendah.`,
 `Pembanding memakai indeks equal-weight 100 saham yang sama, bukan IHSG/LQ45, karena data indeks tidak tersedia di lingkungan pengerjaan.`,
 `Forward test belum dijalankan; strategi baru dibekukan ${R.frozen.date}.`,
 `Data snooping: banyak varian strategi pernah diuji pada data yang sama sebelum pipeline ini (sekitar ${num(R.research_runs_logged,0)} baris hasil simulasi tercatat); pemisahan in-sample/out-of-sample di sini hanya membatasi pemilihan parameter, bukan bentuk strategi.`,
 `OOS vs IS: bila CAGR out-of-sample terlihat lebih tinggi dari in-sample, penyebab yang diketahui: (a) periode OOS (2018–2025) punya rezim tren yang berbeda, bukan bukti kualitas; (b) aturan momentum 120/20 dan bentuk strategi dipilih setelah melihat riset 2016–2025 sehingga OOS tidak sepenuhnya murni; (c) run terpisah memulai ulang modal dan memberi pengaruh kapasitas yang berbeda. Gunakan angka potongan kontinu dan walk-forward sebagai pembanding yang lebih jujur.`,
 `Kapasitas: batas 5% nilai transaksi membuat CAGR turun saat modal membesar (lihat tabel kapasitas).`,
 `Pengisian buy stop diasumsikan tepat di level + 1 fraksi; di hari breakout cepat, slippage bisa lebih besar. Antrean order, kedalaman order book, dan sesi pra-pembukaan tidak dimodelkan.`,
 `Jadwal ARB asimetris dan harga yang disesuaikan adalah pendekatan; perubahan fraksi harga historis tidak dimodelkan.`,
 `Strategi long-only, terkonsentrasi maksimal 10 saham; drawdown terbesar ${pct(M.mdd)} dan periode terlama tanpa rekor ${num(M.longest_months_without_record,1)} bulan.`].map(x=>'<li>'+x+'</li>').join('');
// Checklist.
const CK=[['File terbuka tanpa internet dan tanpa server',1,'semua CSS/JS/data tertanam; grafik SVG buatan sendiri'],['Nama file UTS_NIM_Nama.html',0,'ganti NIM dan Nama sebelum upload'],
 ['Enam metrik utama dan metrik pelengkap, sesudah biaya',1,''],['Log trade lengkap dan kurva ekuitas harian tertanam',1,TR.length+' trade, '+EQ.length+' hari'],['In-sample/out-of-sample, walk-forward, sensitivitas',1,''],
 ['Tanggal pembekuan dan hasil forward test terpisah',0,'tanggal pembekuan ada; forward test menunggu data sesudah '+R.frozen.date],['Uji keterlambatan 1 bar dan biaya 2×',1,''],['Asumsi fee, spread, lot, likuiditas',1,''],
 ['Survivorship bias dan keterbatasan',1,''],['Pernyataan keaslian dan penggunaan AI',0,'lengkapi pernyataan keaslian Anda sendiri'],['Kode sumber backtest terlampir',1,'folder uts/ (zip)']];
table('t-check',['Butir','Status','Catatan'],CK.map(([k,s,n])=>({c:[k,s?'<span class="badge b-ok">siap</span>':'<span class="badge b-warn">perlu tindakan</span>',n]})),{left:1});
})();
</script>
</body>
</html>
"""

if __name__=='__main__':main()
