# Faz 2 / Brief 04 — Quine (1996) Tamamlama Raporu

**Brief:** `docs/briefs/04_quine.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, 5/5 kabul testi geçti (tüm paket 37/37).
**Uygulayan:** Claude Code (brief uygulayıcısı)
**Dokunulan dosyalar:** `bench/algorithms/quine.py`, `bench/tests/test_quine.py`.
Bench core / kontrat değişmedi; Liebe dosyası değişmedi (yalnız import edildi).

---

## 1. Ne yapıldı

Quine = **Liebe + farklı arama yapısı**. Feature, kayıt seti ve oylama Liebe'den
**içe aktarıldı** (kopyalanmadı): `extract_features`, `build_database` kayıtları ve
`_resolve` `LiebeAlgorithm`'den gelir. Tek değişiklik: lineer tarama yerine
`(d1, d2, theta)` öznitelik uzayında **ölçekli cKDTree kutu sorgusu** (Chebyshev,
p=∞, yarıçap 1 = `|Δ|≤tol` her eksende) → search O(n)→O(lg n).

`QuineConfig(use_core_verify=False)` ile Faz 2 ablation modu (native vs +ortak
doğrulayıcı `core/verify.ransac_confirm`).

## 2. Kabul testleri (brief §Kabul testleri) — 5/5 PASSED

| # | Test | Kriter | Sonuç |
|---|---|---|---|
| 1 | `test_quine_equivalent_to_liebe` | Quine eşleşme kümesi == Liebe | ✅ **0 uyuşmazlık** (12 sahne) |
| 2 | `test_quine_noiseless` | id_rate ≥ 0.99, wrong_attitude = 0 | ✅ 1.000 |
| 3 | `test_quine_search_scaling` | Liebe ~O(n), Quine ~O(lg n) | ✅ (aşağıda) |
| 4 | `test_quine_native_vs_verify` | verify spike yanlışlarını buder | ✅ |
| 5 | `test_quine_deterministic` | sabit seed → aynı | ✅ |

## 3. Çıktıların yorumu

### Eşdeğerlik (brief'in en önemli kriteri)
Aynı feature + aynı kayıt + aynı tolerans + aynı oylama → Quine ve Liebe **birebir
aynı eşleşme kümesini** veriyor (gürültüsüz + σ=8″+3 spike, 12 sahne, 0 uyuşmazlık).
Tek fark hızdır — adil karşılaştırmanın en saf hâli (tek değişken: arama yapısı).

### Arama ölçeklemesi — Tablo 1 doğrulaması (`results/quine_scaling.{csv,png}`)
Mutlak wall-time bu ölçekte (≤5k yıldız, Mv<6) temiz ayrışmıyor (Liebe penceresi
numpy-vektörize, Quine KDTree Python-overhead'li; asimptotik kesişim katalog
boyutunun ötesinde). Asıl kanıt **sorgu başına dokunulan kayıt sayısında**:

| n | Liebe taranan/sorgu | Quine aday/sorgu |
|---|---|---|
| 1000 | 5.7 | 0.78 |
| 2000 | 10.6 | 0.45 |
| 4000 | 23.2 | 0.45 |
| 4992 | 35.4 | 0.52 |

**Liebe ~O(n)** (n 5× → tarama ~6× büyür: d1-penceresi yoğunlukla şişer),
**Quine ~sabit** (KDTree O(lg n) konumlandırma + sadece gerçek adaylar döner).
Survey Tablo 1'in "ikili ağaç aramayı O(lg n)'e indirir" tezinin doğrudan kanıtı.

### DB boyutu
- Kayıtlar **Liebe ile aynı** (14976, 0.72 MB) → **O(n)** korunur.
- Tam Quine indeksi (kayıtlar + KDTree) ~**1.38 MB**: KDTree sabit-çarpanlı ek
  (brief: "ek indeks sabit-çarpan"). Asimptotik sınıf değişmez.

### Zamanlama (full-sky, best-of-3)
- `extract` medyan ~9.7 ms (Liebe'den miras — Python döngüsü; **kıyas ekseni değil**).
- `match` medyan ~4.1 ms — n=5k'da Liebe (~4 ms) ile **aynı mertebede**; fark
  ölçeklemede (yukarıda), wall-time'da değil (crossover katalogdan büyük n'de).
- `results/quine_timing.png`.

### Gürültü grace
Quine ≡ Liebe olduğundan grace eğrisi **Liebe ile birebir aynı**. Temsilî yoğun
alanda 1.000/0.992/0.842/0.404 @ σ=2/5/10/20″ (bkz. Liebe raporu). `quine_grace.csv`
seyrek (12 yıldız) alanda üretildi (id_rate yoğunluğa bağlı düşer; Liebe ile aynı).

### Sahne
`results/quine_scene.png`.

### native vs +ortak doğrulayıcı (Faz 2 ablation — kritik bulgu)
σ=5″ + spike taraması:

| spike | native wrong_attitude | +verify | native n_wrong | +verify n_wrong |
|---|---|---|---|---|
| 20 | 0.725 | 0.675 | 0.17 | **0.00** |
| 40 | 0.700 | 0.600 | 0.55 | **0.00** |

**Bulgu:** `use_core_verify` yanlış eşleşmeleri (`n_wrong`) **sıfırlıyor** ve
wrong_attitude'u **düşürüyor** — ama etki ılımlı. Çünkü **Quine'ın oylaması zaten
büyük ölçüde spike-dayanıklı** (en yakın-2 pattern'i + min_votes; spike'lar nadiren
tutarlı oy alır). Doğrulama yalnız spike yoğunlaştığında (ör. 40 spike) bariz katkı
sağlar. Yüksek gürültüdeki kalan wrong_attitude'un çoğu **yanlış eşleşmeden değil**,
seyrek alanda az yıldızla gürültü-sınırlı **zayıf roll** kestiriminden gelir —
doğrulama bunu çözemez (per-yıldız body artığı küçük kalır). Bu, brief 03b'nin
amaçladığı ablation sonucudur: Quine için robustluk büyük ölçüde **pattern+oylama**dan,
az kısmı doğrulamadan gelir. (Karşıtlık: Triangle'da izin-verici eşleme spike
yanlışları üretiyordu, orada doğrulama elzemdi.)

## 4. PM'e notlar
1. **Ölçekleme kanıtı operasyon-sayımıyla** verildi (wall-time ≤5k'da ayrışmıyor;
   Liebe vektörize pencere + Quine KDTree overhead). Dokunulan-kayıt sayısı
   asimptotik sınıfı net gösterir; mutlak süre yerine bu raporlandı.
2. **Test 4 "verify wrong_attitude'u düşürür"** doğrulandı ama **etki ılımlı**:
   Quine native voting zaten spike-robust; verify asıl katkıyı yoğun-spike rejiminde
   yapar. Bu bir bulgu (kusur değil) — Faz 2 ablation'ın ölçmek istediği tam da bu.

## 5. Çalıştırma
```bash
python -m pytest bench/tests/test_quine.py -v
```

## 6. Çıkış koşulu
Brief 04 kabul kriterleri sağlandı. Faz 2'nin ilk adımı (arama hızlandırma) tamam;
sıradaki SLA k-vector (brief 05) ile DB-boyutundan-bağımsız arama gelecek.
