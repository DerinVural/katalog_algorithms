# Brief 03b — Faz 2 Öncesi Core Hazırlığı Tamamlama Raporu

**Brief:** `docs/briefs/03b_core_prep.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, 6/6 kabul kriteri geçti (tüm paket 32/32).
**Uygulayan:** Claude Code (brief uygulayıcısı)
**Dokunulan dosyalar:** `bench/core/metrics.py`, `bench/core/verify.py` (yeni),
`bench/compare.py`. **Hiçbir algoritma dosyasına dokunulmadı**; `StarIDAlgorithm`
kontratı değişmedi.

> Not: 7-başlık analiz seti (DB/timing/grace/sahne) **algoritma** brief'leri içindir;
> 03b bir core-altyapı brief'i (yeni algoritma yok), bu yüzden ilgili kısım
> compare'in yeniden üretimi + metrik yorumu olarak verildi.

---

## İş 1 — `false_id` ikiye ayrıldı (core/metrics.py)

`TrialResult`'a `no_solution` (GÜVENLİ) ve `wrong_attitude` (TEHLİKELİ) eklendi;
`false_id_flag` artık **yalnız** `wrong_attitude`'u gösterir. `solved`, `q_est`'ten
belirlenir (inf'e güvenilmez):

```python
solved         = (q_est is not None) and bool(np.all(np.isfinite(q_est)))
no_solution    = not solved
wrong_attitude = solved and (total_err > gate)
false_id_flag  = wrong_attitude
```

`compare.py` özetine `wrong_attitude_rate` ve `no_solution_rate` eklendi;
`phase1_compare.csv` artık bu iki sütunu ayrı taşır.

## İş 2 — Paylaşılan doğrulayıcı (core/verify.py, yeni)

`ransac_confirm(matches, observed, catalog, gate_arcsec=60, max_seeds=8)`:
triangle'ın native RANSAC 4. yıldız doğrulamasının **jenerik, truth'suz** kopyası.
En yüksek-güvenli eşleşme çiftlerinden attitude tohumlar, en büyük inlier kümesini
tutar, rafine eder; <3 tutarlı eşleşme kalırsa `[]` (çözümsüz > yanlış). Katalog
inertial'ına `catalog.by_id(hip)` ile erişir; `triangle_planar.py` **değişmedi**
(kendi native confirm'i kalır). Faz 2'de "native vs +ortak doğrulayıcı" ablation
ekseni olacak.

## Kabul testleri (brief 03b) — 6/6 PASSED

| # | Test | Sonuç |
|---|---|---|
| 1 | `test_metric_no_solution` | q_est=None → no_solution=T, wrong=F, false_id=F ✅ |
| 2 | `test_metric_wrong_attitude` | 90° sapık → no_solution=F, wrong=T, false_id=T ✅ |
| 3 | `test_metric_good` | doğru attitude → üçü de F ✅ |
| 4 | `test_verify_prunes_outlier` | aykırı elenir; <3 tutarlı → [] ✅ |
| 5 | `test_verify_no_truth_access` | verify.py'de truth erişimi yok (grep) ✅ |
| 6 | regresyon | mevcut 27 test + 5 yeni = **32/32** ✅ |

## İş 3 — Faz 1 kıyası yeniden üretildi (yeni metrikler)

`results/phase1_compare.csv` yeni sütunlarla (80 full-sky sahne, σ=5″ + 3 spike):

| Metrik | Liebe | Triangle |
|---|---|---|
| DB boyutu | 0.72 MB | 49.58 MB (**69×**) |
| id_rate ort | 0.886 | 1.000 |
| **wrong_attitude** (tehlikeli) | **0.030** | **0.000** |
| **no_solution** (güvenli) | **0.000** | **0.000** |
| match medyan | 4.1 ms | 174.6 ms |

### Çıktıların yorumu (ayrımın neden önemli olduğu)
- Eski tek bayrak Liebe için %3.7 "false_id" diyordu; **ayrım gösteriyor ki bu %3'ün
  tamamı `wrong_attitude` (TEHLİKELİ), `no_solution` %0.** Yani Liebe σ=5″+3spike'ta
  başarısız olduğunda "çözüm yok" demiyor, **yanlış attitude üretiyor** — yıldız
  izleyici için en kötü durum. Bu, spike reddi olmamasının doğrudan sonucu.
- Triangle hem wrong_attitude hem no_solution = %0: RANSAC 4. yıldız doğrulaması spike
  yanlışlarını eleyip yalnız tutarlı çözümleri bırakıyor.
- Bu ayrım Faz 2 için **kritik ölçüm ekseni**: Pyramid'in non-star reddi gibi katkılar
  artık `wrong_attitude`'u (tehlikeli) `no_solution`'dan (güvenli) ayrı izlenerek temiz
  ölçülebilir — brief 03b'nin asıl gerekçesi.
- **Dipnot (rapor 03'e eklendi):** 69× oranı muhafazakâr; Liebe `k=3` ile 3× şişkin,
  `k=2`'de oran ~200×. O(n) vs O(n·f²) karakterizasyonu değişmez.

## PM'e not — kritik bulgunun korunması
Brief'in vurguladığı gibi `ransac_confirm` "her şeyi düzeltir" diye sunulmuyor:
doğrulamayı bir algoritmanın *çıktısına* sonradan yapıştırmak recall açığını kapatmaz
(doğrulama aday-üretimine gömülü olduğunda etkilidir). Bu yüzden core'a **opsiyonel,
kontrol edilebilir bir eksen** olarak eklendi; Faz 2 ablation'ında native pattern
gücü ile doğrulama katkısı ayrı ayrı ölçülecek.

## Çıkış koşulu
Brief 03b kabul kriterleri sağlandı. Core, Faz 2 (Quine, SLA k-vector, Pyramid) için
hazır.
