# Apakah breakout mengatur WR dan ER mengatur holding?

9 Oktober2026:18 backtest selesai, silang HHVexit5/20/40 x tanpaERexit/ERsaham20>=.3/.5 x fee/spread. Entryinversemarket-only tetap:Close<SMA30ORfade2,marketER20<.3,nextOpen. ERyangdiubah adalah syarat ERSAHAMuntukEXIT, bukanERpasarentry, bukanpanjangperiodeER. Tidakmengubahmain/AFL atau memilihparameterbaru.

Full4Jan2000–15Agustus2025,Rp1miliar/10slot/compounding,fee buy.15%sell.25%. WRreturnnet>0;holdbar pertransaksi. Batas20baseline+.3 diregresikehasilasli;prefix/eligibility/akuntansidiperiksa. Gridfullsensitivity pada riwayat yangpernahdilihat,bukanvalidasiindependen.

| HHV | ERexit | WRfee | Holdbarfee | Avglossfee |
|---|---|---:|---:|---:|
|5|tanpa|62.12%|16.00|8.47%|
|5|.3|62.85%|57.79|17.14%|
|5|.5|66.34%|140.40|22.43%|
|20|tanpa|66.69%|44.23|15.58%|
|20|.3|66.13%|74.63|19.99%|
|20|.5|66.58%|147.35|23.52%|
|40|tanpa|66.71%|77.48|20.31%|
|40|.3|65.90%|92.18|21.13%|
|40|.5|68.17%|153.59|23.66%|

Observasi: ERmemperpanjanghold pada setiapHHV di gridini; pengaruhWRtidakmonoton. HHV20 WR66.69->66.13->66.58,hampirtetap sementarahold44->75->147. TetapiHHVjuga memengaruhiholding:tanpaER16->44->77bar;WR62.12->66.69->66.71. DenganER.3,HHV20->40justruWR66.13->65.90meskiholdnaik. Jadi bukanpemisahanfungsiWRvsdurasi. Keduanyaadalahpembatassinyalexit yangmengubahwaktujual, distribusihasil,cash/slotdanrealizedtrades.

Interaksi: menambahER.5 keHHV5 menaikkanhold124.40bar, sedangkankeHHV40 menaikkan76.12bar. MemperpanjangHHV5->40tanpaER menambah61.48bar, tetapiER.5hanya13.19bar. SaatERketat, syaratERmenjadi hambatanbesar sehingga perubahanHHVrelatiflebihkecil. IniinterpretasisinyalANDdanhasilgrid, bukanjaminanparametermonotonlintaspasar.

SpreadstressmodernIDX1tickeachside100shares:WRHHV5tanpa/.3/.5=50.97/58.97/63.41%;HHV20=61.02/62.10/63.52%;HHV40=63.80/63.93/65.52%. PolaWRberbeda setelahfriksi;jangananggapknobuniversal. HoldingfullspreadHHV5tanpasedikitberbedakarenaakhirnya roundlot/cashmengubahtrade;konfiglainsebagianbesarsamadenganfee. Semua9konfigsideannualequivalentnegatif dalamkeduaskenario;meskiCAGRfullfee/spreadbeberapapositif,belumstrategisidewaysberhasil. Sideannualequivalent adalahatribusiannualitaspadatanggalchoppy,bukanCAGRportofoliomandiri.

Kesimpulan:dugaan sebagianbenar bahwaERexit kuatmemengaruhiholding; tidakbenar jika breakout dianggapkhususWRdanERkhusushold. EfekparameterharusdinilaibersamaWR,avgwin,loss,holding,biaya. Memperpanjangholdingjuga menaikkanavg loss di seluruhgridfee, sehingga bukanperbaikanrisikogratis. Kode grid_choppy_exit_levers.py, PLAN/REPORT/comparison danledger/equity semuaada. Tidakdiadopsi.
