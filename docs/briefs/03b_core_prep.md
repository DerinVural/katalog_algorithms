# Brief 03b — Faz 2 Öncesi Core Hazırlığı

**Hedef dosyalar:** `bench/core/metrics.py`, `bench/core/verify.py` (yeni), `bench/compare.py`, `bench/runner.py`, ilgili testler.
**Bağımlılık:** Faz 1 (onaylandı).
**Neden:** Faz 2'ye (Quine, SLA, Pyramid) geçmeden iki core eksiği kapatılmalı; yoksa Pyramid'in non-star reddi gibi katkıları temiz ölçemeyiz. **Hiçbir algoritma dosyasına dokunulmaz**, yalnız core + kıyas araçları.

> Bu PM incelemesinden çıktı: (1) `false_id` metriği "çözümsüzlük" ile "yanlış attitude"u tek bayrakta topluyor; (2) doğrulama her algoritmaya gömülü olduğu için kıyas için ortak, opsiyonel bir doğrulayıcıya ihtiyaç var.

---

## İş 1 — `false_id` metriğini ikiye ayır (core/metrics.py)

Şu an: `false_id_flag = (attitude sonsuz) OR (hata > gate)`. `quest` <2 eşleşmede `None` → hata `inf` → çözümsüzlük de `false_id` sayılıyor. Yıldız izleyici için **çözümsüzlük güvenli**, **yanlış attitude tehlikeli** — ayrılmalı.

### Yapılacak
`TrialResult`'a iki alan ekle, `false_id_flag`'i yeniden tanımla:
```python
solved          = (q_est is not None) and bool(np.all(np.isfinite(q_est)))
no_solution     = not solved
wrong_attitude  = solved and (total_err > gate)      # TEHLİKELİ
false_id_flag   = wrong_attitude                     # artık YALNIZ tehlikeli durum
```
- `evaluate` `solved`'i `q_est`'ten belirlesin (inf'e güvenme).
- `TrialResult` alanları: mevcutlara ek `no_solution: bool`, `wrong_attitude: bool`. `false_id_flag` korunur ama anlamı = `wrong_attitude`.
- `attitude_error` davranışı aynı (None → inf); ama `no_solution`/`wrong_attitude` ayrımı `q_est is None` ile yapılır.

### compare.py + runner.py
`_summarize` ve runner kayıtlarına `no_solution_rate` ve `wrong_attitude_rate` ekle. `false_id_rate` artık yalnız tehlikeli oranı gösterir. `run_full_sky` "covered" tanımı zaten `attitude_solved and not false_id_flag and id_rate>=min` — yeni anlamla tutarlı kalır (çözümsüzlük → solved False → kapsanmadı).

---

## İş 2 — Paylaşılan opsiyonel doğrulayıcı (core/verify.py, yeni)

Triangle'ın RANSAC 4. yıldız doğrulamasını **jenerik, truth'suz** bir core yardımcısına çıkar. Amaç: Faz 2'de her algoritmayı "native" (kendi doğrulamasıyla) **ve** "+ortak doğrulayıcı" ile koşup, robustluğun ne kadarı pattern ne kadarı doğrulama ayırt edilebilsin.

```python
# bench/core/verify.py
def ransac_confirm(
    matches: list[CandidateMatch],
    observed: Sequence[BodyVector],
    catalog: Catalog,
    gate_arcsec: float = 60.0,
    max_seeds: int = 8,
) -> list[CandidateMatch]:
    """En yüksek-güvenli eşleşme çiftlerinden attitude tohumla, her tohum için
    inlier (artık açısı <= gate) kümesini say, en büyük tutarlı kümeyi tut,
    inlier'lardan yeniden kestirip rafine et. <3 tutarlı eşleşme -> [] (çözümsüz
    > yanlış). Truth KULLANMAZ; yalnız obs body vektörleri + katalog inertial."""
```
Mantık triangle_planar._confirm ile birebir; tek fark `catalog.by_id(hip).u_inertial` üzerinden çalışır ve herhangi bir algoritmanın `CandidateMatch` listesine uygulanabilir. `triangle_planar.py`'yi **değiştirme** (kendi native confirm'i kalsın); bu sadece ortak, paylaşılabilir kopya.

> Kritik bulgu (PM): doğrulamayı bir algoritmanın *çıktısına* sonradan yapıştırmak recall açığını kapatmaz — doğrulama aday-üretimine gömülü olduğunda etkilidir. Bu yüzden `ransac_confirm` "her şeyi düzeltir" diye sunulmaz; Faz 2 ablation'ında kontrollü bir eksen olarak kullanılır.

---

## İş 3 — Faz 1 kıyasını yeniden üret + dipnot

- `python -m bench.compare` yeni metriklerle yeniden koşulsun; `results/phase1_compare.csv` artık `no_solution_rate` ve `wrong_attitude_rate` ayrı sütunlarla.
- Rapora dipnot: "69× DB oranı muhafazakârdır — Liebe `neighbors_k=3` ile 3× şişkin; `k=2`'de oran ~200×." (O(n) vs O(n·f²) karakterizasyonu değişmez.)

## Kabul testleri
1. **metric_no_solution:** `q_est=None` vakası → `no_solution=True`, `wrong_attitude=False`, `false_id_flag=False`.
2. **metric_wrong_attitude:** doğru eşleşme + kasten 90° sapık `q_est` → `no_solution=False`, `wrong_attitude=True`, `false_id_flag=True`.
3. **metric_good:** gürültüsüz oracle → üçü de `False`.
4. **verify_prunes_outlier:** tutarlı eşleşmelere 1 aykırı eklenince `ransac_confirm` onu eler; <3 tutarlı kalırsa `[]`.
5. **verify_no_truth:** `ransac_confirm` imzasında/gövdesinde truth erişimi yok (grep ile doğrula).
6. **regresyon:** mevcut 27 testin tümü hâlâ geçer (false_id anlamına dayanan varsa güncelle).

## Yapma
- Hiçbir algoritma dosyasını (liebe.py, triangle_planar.py, oracle.py) değiştirme.
- `StarIDAlgorithm` kontratını değiştirme. `ransac_confirm` core yardımcısıdır, kontrat parçası değil.
