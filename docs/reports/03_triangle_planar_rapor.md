# Faz 1 / Brief 03 — Planar Triangle Baseline Tamamlama Raporu

**Brief:** `docs/briefs/03_triangle_planar.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, 5/5 kabul testi geçti (tüm paket 27/27).
**Uygulayan:** Claude Code (brief uygulayıcısı)
**Dokunulan dosyalar:** `bench/algorithms/triangle_planar.py`, `bench/tests/test_triangle_planar.py`,
`bench/compare.py` (yeni, ayrı dosya). Bench core / kontrat değişmedi.
**Yardımcı:** `bench/analysis.py` (2-D DB alanı dökümü + n_scenes), `tests/conftest.py` (moderate_attitude).

---

## 1. Ne yapıldı

Üç yıldızın ara açılarını permütasyon-bağımsız anahtar `(a_min, a_mid, a_max)` olarak
kullanan klasik üçgen eşleştirmesi. Amaç: Liebe ile **aynı** katalog/sahne/QUEST/metrik
altında, O(n·f²) DB maliyetini ölçüp O(n) Liebe ile kontrast oluşturmak.

- **`build_database`** → FOV'da birlikte görülebilir (A-merkezli) tüm üçlüler;
  dedup; `a_min`'e göre sıralı. Köşe karşılıkları, sıralı-kenar çiftlerinin ortak
  köşesinden türetilir (vektörize).
- **`extract_features`** → gözlenen C(f,3) üçlü (vektörize).
- **`match`** → `a_min` penceresi + diğer iki açı filtresi → oylama → **dayanıklı
  (RANSAC-tarzı) 4. yıldız doğrulaması**.

## 2. Kabul testleri (brief §Kabul testleri) — 5/5 PASSED

| # | Test | Kriter | Sonuç |
|---|---|---|---|
| 1 | `test_triangle_noiseless` | gürültüsüz id_rate ≥ 0.99, false_id yok | ✅ id_rate **1.000** |
| 2 | `test_triangle_db_much_larger_than_liebe` | DB >> Liebe (O(n·f²) vs O(n)) | ✅ **69×** |
| 3 | `test_triangle_noise_grace` | düşük gürültüde yüksek, ~monoton | ✅ |
| 4 | `test_triangle_confirmation_helps` | doğrulama kapalı→false_id artar | ✅ off 0.97 → on 0.03 |
| 5 | `test_triangle_deterministic` | sabit seed → aynı | ✅ |

## 3. DB incelemesi

`results/triangle_planar_db.csv` — sütunlar `key0,key1,key2` (a_min,a_mid,a_max, **arcsec**),
`v_mm,v_mx,v_dx` (köşe HIP no).

- **1.024.337 kayıt**, bellek **≈ 49.6 MB** (`db_size_bytes`), CSV dökümü ~54 MB.
- Liebe DB: 0.72 MB → **oran ~69×**. Bu, survey Tablo 1'in **O(n·f²) vs O(n)**
  farkının doğrudan ampirik kanıtı. (A-merkezli co-visibility ile ~1.7M üçgen üretilip
  dedup'tan sonra ~1.02M; 2×-yarıçap köşegen co-visibility ~25M verirdi — inşası infeasible.)

## 4. Zamanlama (full-sky, best-of-3, ısınmalı)

| Aşama | medyan | mean | max |
|---|---|---|---|
| `build_database` | ~2.4–7 s (tek seferlik, makine yüküne bağlı) | | |
| `extract_features` | 3.0 ms | 6.4 | 39 |
| **`match` (DB arama)** | **148 ms** | 292 | **1615** |
| toplam | 151 ms | 298 | 1654 |

(gözlem/sahne medyan 22)

### Zamanlama grafiği — `results/triangle_planar_timing.png`
`match` toplamı domine ediyor ve gözlem sayısıyla **kübik (~O(f³))** büyüyor:
~60 ms (13 yıldız) → ~1600 ms (50 yıldız). `extract` (vektörize) neredeyse sıfır.
Liebe'nin ~ms-ölçekli, neredeyse-doğrusal davranışıyla **çarpıcı kontrast** — DB'nin
1M+ kayıt üzerinde lineer üçgen araması ve obs-üçlü sayısının C(f,3) büyümesi birleşiyor.

## 5. Çıktıların yorumu

- **Doğruluk:** Üçgen, düşük-orta gürültüde Liebe'den **daha doğru ve robust**: 4. yıldız
  (attitude) doğrulaması spike kaynaklı yanlış eşleşmeleri eler. Mekanizmanın etkisi net:
  spike senaryosunda (σ=8″+5 spike) `require_confirm` kapalı false_id=0.97 → açık **0.03**;
  yanlış eşleşme 1.5 → 0.0. Doğrulama olmadan spike→yıldız yanlış eşleşmeleri runner'ın
  QUEST'ini bozup yanlış attitude üretiyor.
- **Grace eğrisi** (`results/triangle_planar_grace.{csv,png}`): id_rate 1.0/1.0/0.967/0.761
  @ σ=2/5/10/20″. σ=20″'te false_id_rate 0.6 — 1-piksel mertebesi gürültüde açı anahtarı
  toleransla taşıyor, beklenen çöküş.
- **Maliyet/fayda:** Üçgen, bu robustluğu **çok pahalıya** alıyor — ~69× DB belleği ve
  ~38× daha yavaş arama. "Neden modern yöntemler kazandı"nın sayısal cevabı: aynı
  doğruluğu/robustluğu O(n) bellek ve sabit-zaman aramayla (k-vector, Faz 2) elde etmek.
- **Sahne görseli:** `results/triangle_planar_scene.png` (temsilî sahne; yıldız/spike/FOV).

## 6. Head-to-head: Liebe vs Triangle (`results/phase1_compare.csv`)

Aynı 80 full-sky sahnesi, σ=5″ + 3 spike:

| Metrik | Liebe | Triangle | Not |
|---|---|---|---|
| DB boyutu | 0.72 MB | **49.6 MB** | 69× — O(n·f²) vs O(n) |
| build | ~2.3 s | ~7.1 s | tek seferlik |
| id_rate (ort) | 0.891 | **1.000** | üçgen daha doğru |
| false_id oranı | 0.0375 | **0.000** | doğrulama spike eler |
| match medyan | **4.0 ms** | 152 ms | Liebe ~38× hızlı |
| extract medyan | 10.4 ms | 3.1 ms | (uygulama farkı; arama maliyeti baskın) |

**Okuma:** Triangle doğruluk/robustlukta kazanıyor ama bellek ve arama hızında ağır
kaybediyor. Survey'in tezi tam da bu: modern yöntemler (k-vector, Pyramid) üçgenin
doğruluğunu O(n) bellek + hızlı aramayla yakalar. Bu tablo Faz 2 için referans çizgisi.

## 7. PM'e notlar (sapmalar)

1. **Co-visibility yarıçapı:** brief köşegen/FOV-çapı öneriyor; bench'in sahne modeli
   **dairesel FOV** (yarıçap = FOV_H/2) olduğundan A-merkezli co-visibility (yarıçap =
   fov_radius) kullanıldı — sahnede gerçekten birlikte görünen üçgenleri kapsar, DB'yi
   infeasible 25M yerine ~1M'de tutar.
2. **Doğrulama:** brief "aday attitude'la 4. yıldızı öngör" diyor; tek-shot tüm-eşleşmeli
   QUEST spike'lara kırılgan çıktı (id_rate'i 0.03'e düşürüyordu). Bunun yerine **dayanıklı
   RANSAC-tarzı** doğrulama (yüksek-oylu eşleşme çiftlerinden attitude tohumla, en büyük
   tutarlı inlier kümesini koru) uygulandı — aynı 4-yıldız/attitude tutarlılık fikri,
   aykırı-değer dayanıklı hâli.

## 8. Çalıştırma

```bash
python -m pytest bench/tests/test_triangle_planar.py -v
python -m bench.compare        # Liebe vs Triangle -> results/phase1_compare.csv
python -m bench.analysis       # (örnek: Liebe tam analiz)
```

## 9. Çıkış koşulu

Brief 03 kabul kriterleri **sağlandı**. Faz 1 (Liebe + Triangle) tamam; ilk head-to-head
karşılaştırma üretildi. Faz 2 (Quine, SLA k-vector, Pyramid) için referans hazır.
