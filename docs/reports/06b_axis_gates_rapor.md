# Brief 06b — Eksen-Ayrık Hata Kapısı Tamamlama Raporu

**Brief:** `docs/briefs/06b_axis_gates.md`
**Tarih:** 2026-06-11
**Durum:** ✅ Tamamlandı; 4/4 kabul kriteri geçti, tüm paket regresyonsuz.
**Dokunulan dosyalar:** `bench/core/metrics.py`, `bench/compare.py` (cross/roll sütunları),
`bench/audit_roll.py` (yeni, tek seferlik denetim), `bench/tests/test_metrics.py`,
`bench/tests/test_pyramid.py` (T2 literal assert geri). **Hiçbir algoritma dosyası değişmedi.**
Kapı default'ları (60″/600″) Liebe-dayanaklı; "testler geçsin" diye ayarlanmadı.

---

## İş 1 — `wrong_attitude` eksen-ayrık tanım

```python
FALSE_ID_CROSS_ARCSEC = 60.0    # cross-boresight (eski anlamın devamı)
FALSE_ID_ROLL_ARCSEC  = 600.0   # roll = 10× (Liebe 2002 §V, denk. 12/16; örneği 2.3″/23″)

wrong_attitude = solved and (cross_err > gate_cross or roll_err > gate_roll)
```

- İki kapı da `evaluate` parametresi (`false_id_cross_arcsec`, `false_id_roll_arcsec`).
- `attitude_error_arcsec` (toplam) raporlamada aynen duruyor; karar eksen-ayrık.
- `no_solution` değişmedi; eski tek-kapıya geri-uyum YOK (temiz kırılım).
- Docstring'de Liebe §V atfı + 06a karşı-bulgu gerekçesi.

Kabul testleri (`test_metrics.py`):
| vaka | eski kapı | yeni kapı |
|---|---|---|
| saf-roll (cross=5″, roll=90″) | True (bayrak) | **False** ✅ — 06a artefaktı aklandı |
| cross-ihlal (70″, 10″) | True | **True** ✅ |
| aşırı-roll (5″, 700″) | True | **True** ✅ |
| no_solution davranışı | — | regresyonsuz ✅ |

## İş 2 — Geçmiş sayıların denetimi (`bench/audit_roll.py` → `results/roll_audit.csv`)

phase1_compare (100 deneme, seed=0) ve phase2_spike_sweep kurgusu (seed=11) aynı
seed'lerle yeniden üretildi; eski-kapı bayrakları yeniden sınıflandırıldı:

| bağlam | algoritma | eski-bayrak | hâlâ-tehlikeli | saf-roll-aklanan |
|---|---|---|---|---|
| Faz 1 (σ=5″+3 spike, 100) | liebe | 3/100 | **2** | 1 |
| Faz 1 | triangle_planar | 0/100 | 0 | 0 |
| Faz 2 (σ=5″, 0/5/20 spike, 24) | liebe | 2/24 | **2** | 0 |
| Faz 2 | quine | 2/24 | **2** | 0 |
| Faz 2 | pyramid / sla / triangle | 0/24 | 0 | 0 |

**Net cümle (brief gereği):** Faz 1–2'nin yayımlanmış sonuçları **dayanıklı çıktı**.
Liebe/Quine'ın "tehlikeli" bayraklarının neredeyse tamamı gerçekten tehlikeli (spike
kaynaklı yanlış kimlik → cross-ihlal); yalnız Faz 1'de Liebe'nin 3 bayrağından 1'i
saf-roll olarak aklandı. Triangle/SLA/Pyramid'in "sahte=0 / wrong_attitude=0" iddiaları
yeni kapıda da aynen geçerli. Hiçbir niteliksel sıralama veya Faz-2 sonucu değişmedi;
beklentiyle uyumlu (Liebe kısmî aklanma, robust algoritmalar dayanıklı).

## İş 3 — T2/T3 yeniden koşum

- **T2 (Pyramid işkence):** yeni kapıyla σ=5″ bloğunda **literal `wrong_attitude = 0`
  geri kondu ve GEÇİYOR** (06a'daki bayraklar cross 1–8″, roll 60–96″ < 600″ idi —
  fiziksel olarak erişilebilir hâle geldi). Kimlik-düzeyi sahte=0 ve %20 tripwire çift
  güvence olarak kaldı. Üç blok: 5R/σ0 → wa **0/50**; 5R/σ5 → wa **0/50** ✅;
  3R/σ5 → wa 0/50, no_solution 50/50 (baskın güvenli).
- **T3 spike taraması** yeni kapıyla yeniden üretildi (`phase2_spike_sweep.{csv,png}`):
  imzalar değişmedi — Liebe/Quine spike'ta tehlikeli (gerçek kimlik hatası), SLA güvenli-
  kırılgan, Triangle/Pyramid wa=0 + id_rate=1.0.

## Çıktıların yorumu

- **Metrik artık fiziği cezalandırmıyor:** dar-FOV tek-kafa yıldız izleyicide roll'un
  cross'tan ~10× kötü olması donanım/geometri gerçeği (Liebe §V). Eski tek kapı bu
  gerçeği algoritma hatası sayıyordu; yeni kapı kimlik hatalarını (cross-ihlal) aynı
  sertlikle yakalarken doğal roll dağılımını tehlikeli saymıyor.
- **"yeni_yakalanan" sınıfı boş** (denetimde 0 vaka): yeni kapı eskisinin alt kümesi
  (cross>60 ⟹ toplam>60; roll>600 ⟹ toplam>600). Yani 06b hiçbir gerçek tehlikeyi
  gevşetmedi, yalnız yanlış-pozitifleri kaldırdı.
- Pyramid'in 06a'da "PM kararı bekliyor" işaretli tek açık maddesi bu brief'le **kapandı**;
  T2 artık brief 06a'nın literal kriterini de sağlıyor.

## Çalıştırma
```bash
python -m pytest bench/tests -q          # tam paket (~13 dk; T2 3×50 blok)
python -m bench.audit_roll               # denetimi yeniden üretmek için
```

## Çıkış durumu
06b kabul kriterleri sağlandı; Faz 2 metrik temeli (eksen-ayrık kapı) yerleşti. Açık
PM maddesi kalmadı.
