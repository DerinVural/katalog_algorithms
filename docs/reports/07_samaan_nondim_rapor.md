# Faz 3 Açılışı / Brief 07 — Samaan Non-Dimensional Star-ID Tamamlama Raporu

**Brief:** `docs/briefs/07_samaan_nondim.md`
**Tarih:** 2026-06-12
**Durum:** ✅ Tamamlandı, 5/5 kabul testi geçti (tüm paket 57/57).
**Dokunulan dosyalar:** `bench/core/scene.py` (İş 0), `bench/algorithms/samaan_nondim.py` (+test),
`bench/algorithms/triangle_planar.py` (yalnız `covisible_triples` ortaklaştırma — refactor,
davranış birebir: 1.024.337 kayıt aynı), `bench/algorithms/sla_kvector.py` (yalnız
`propagate_full_frame` ortaklaştırma). Kapı/tolerans sabitleri "test geçsin" diye oynanmadı.

---

## 1. İş 0 — Kalibrasyon bozulması enjeksiyonu (`scene.py`)

`NoiseConfig.focal_error_ppm`: sahne yıldızı **gerçek** odakla `f·(1+ppm·1e-6)` projekte
eder (f'te lineer → nominal pikselin radyal ölçeklenmesi), gözlemci **nominal** f ile geri
döndürür. Kabul: `ppm=0` bit-bit regresyonsuz (çarpan yolu guard'lı); oracle ±3000 ppm'de
id_rate=1.000 (sahne doğruluğu kontrolü). ✅

## 2. Algoritma

- **Feature:** üçgen iç açıları; θ_min+θ_mid+θ_max ≈ π → yalnız **2 bağımsız** öznitelik
  `(θ_min, θ_max)`. Boyutlu üçgenin 3 bağımsız özniteliğinden biri ölçek değişmezliğine
  harcandı — non-dim'in bilgi bedeli.
- **DB:** paylaşılan `covisible_triples` (Triangle ile birebir aynı 1.024.337 üçlü) +
  inertial vektörlerden küresel iç açılar (Liebe teğet-düzlem mekanizmasının vektörize
  eşdeğeri) + `θ_min` üzerinde k-vector (SLA'dan import). **49.8 MB** — Triangle sınıfı,
  bilinçli: kazanç bellek değil robustluk.
- **extract:** gözlem iç açıları **piksel koordinatlarından** (`centroid_px`) düz
  trigonometriyle — body vektörlerden DEĞİL (değişmezlik tam burada yaşar).
- **match:** k-vector aralığı + θ_max filtresi → ağırlıklı oylama → karşılıklı-tutarlılık
  turları → **≥5-yıldız geometrik konsensüs** → tam-kare yayılım → `min_match_stars=5`.

## 3. Kabul testleri — 5/5 PASSED

| # | Test | Sonuç |
|---|---|---|
| T1 | **T-calib** (tanımlayıcı) | ✅ Samaan tüm ppm'lerde 1.000; Liebe/SLA bozuldu |
| T2 | gürültüsüz ≥0.99, wa=0 | ✅ 1.000 / 0 |
| T3 | grace σ∈{2,5,10}″ | ✅ 1.000/1.000/1.000 |
| T4 | min_match 5→3 ablation | ✅ wa(5)=0 ≤ wa(3); ≥5 ile nadir |
| T5 | determinizm + DB tablosu | ✅ 1.024.337 kayıt (=Triangle), 49.8 MB |

## 4. T-calib — Faz 3 açılış figürü (`results/calib_sweep.{csv,png}`)

σ=5″, focal_error_ppm ∈ ±3000 (Liebe Fig. 23 aralığı), id_rate:

| ppm | Samaan | Liebe | SLA |
|---|---|---|---|
| 0 | **1.000** | 0.667 | 1.000 |
| ±1000 | **1.000** | 0.54 / 0.48 | **0.000** |
| ±2000 | **1.000** | 0.33 / 0.25 | 0.000 |
| ±3000 | **1.000** | 0.20 / 0.13 | 0.000 |

**Okuma:** Üç imza net. (1) **Samaan dümdüz 1.000** — düzlem iç açıları radyal ölçeklemeden
hiç etkilenmez; iddia kanıtlandı. (2) **SLA uçurum**: ±1000 ppm'de bile çöker (en parlak 4
yıldız geniş ayrımlı → çift-açı hatası ~50″+ ≫ 15″ tolerans) ama **güvenli** (no_solution=1.0,
wa=0). (3) **Liebe çan eğrisi**: en yakın-2 komşu ayrımları küçük (~1-2°) → hata toleransa
ancak yaklaşır, kademeli bozulur. Ara-açı tabanlı her algoritmanın kalibrasyona birinci
dereceden duyarlılığı; Samaan'ın varlık sebebi.

## 5. Teşhis ve gerekli sapmalar (PM'e — önemli)

Brief'in literal match tarifi (oy → birebir → ≥5) ilk uygulamada **id_rate 0.08, wa 8/8**
verdi. Teşhis zinciri (gürültüsüz, kanıtlı):
1. **Açılar doğru:** gözlem-planar vs katalog-küresel fark ≤0.08° ≪ 0.5° tol (küresel
   fazlalık/gnomonik bozulma ihmal edilebilir; feature tasarımı sağlam).
2. **Aday patlaması:** 2 zayıf öznitelik, 1M kayıtlık DB'de ayırt edici değil — tek sorgu
   θ_max filtresinden sonra bile ~2351 aday döndürüyordu; oy gürültüsü sinyali boğuyordu.
   → bilgisiz-üçlü atlama (`max_candidates_per_triple=200`) + 1/n_aday ağırlığı (0.08→0.42).
3. **Küme kopyaları:** yıldız kümelerinde yerel geometri benzerleri, tekil-yıldız çoğunluğunu
   tutarlı-yanlış kazananlara taşıyordu (gürültüsüzde bile truth c≈9 vs sahtekâr c≈11).
   → Samaan'ın **≥5 yıldız ilkesinin geometrik uygulaması**: oy-kısa-listesi havuzundan en
   büyük attitude-tutarlı alt küme (RANSAC, `consensus_gate=300″` — kalibrasyon-toleranslı:
   ±3000 ppm bozulması ≤~80″ ≪ 300″ ≪ sahtekâr hatası derece-mertebesi). wa 8→0.
4. **Tam-kare yayılım** (SLA/Pyramid emsali; `propagate_full_frame` ortaklaştırıldı, geniş
   kapıyla): id_rate 0.51→1.000. Brief'te açıkça yoktu; bench id_rate'i tüm yıldızları
   saydığından gerekli tamamlama.

Bu üç ek mekanizma (ağırlık+tavan, geometrik konsensüs, yayılım) brief'in oylama+≥5
iskeletini korur; "≥5 tutarlı yıldız" şartı artık geometrik olarak denetleniyor — Samaan'ın
özgün bulgusunun güçlü hâli. Kapı 300″ kalibrasyon fiziğinden türetildi, test-uydurma değil.

## 6. Diğer analizler (standart set)

- **DB dökümü:** `results/samaan_nondim_db.csv` (θ derece + köşe HIP'leri, iç-açı-sıralı).
- **Zamanlama** (`samaan_nondim_timing.png`): build ~4.4 s (tek seferlik); extract medyan
  1.5 ms (vektörize); **match medyan 188 ms** (yoğun sahnede 4 s'ye kadar) — Triangle-sınıfı
  maliyet: C(f,3) sorgu × kalabalık aday listeleri. Beklenen; kazanç hız değil kalibrasyon
  robustluğu. (Mutlak süreler makine yüküne duyarlı; göreli sınıf anlamlı.)
- **Grace:** 1.000/1.000/1.000 @ σ=2/5/10″ (`samaan_nondim_grace.csv`) — geniş konsensüs
  kapısı + yayılım gürültüye de dayanıklı kılıyor.
- **Sahne:** `samaan_nondim_scene.png`.
- **Refactor güvencesi:** Triangle 1.024.337 kayıt birebir; SLA/Triangle/Pyramid testleri
  değişiklik sonrası geçiyor (suite 57/57).

## 7. Çalıştırma
```bash
python -m pytest bench/tests/test_samaan.py -v
```

## 8. Çıkış durumu
Brief 07 kabul kriterleri sağlandı; Faz 3 kalibrasyon ekseni açıldı. 07b (non-dim × Pyramid
melezi) PM onayına hazır.
