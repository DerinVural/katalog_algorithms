# Brief 07b (FINAL, birleşik) — ARAŞTIRMA: Non-Dim Ailesi × Pyramid

**Bu doküman v1/v2/v3'ün YERİNE geçer; tek kaynak budur.** Önceki sürümlere bakmak gerekmez.
**Hedef dosyalar:** `bench/algorithms/nondim_pyramid.py` (Kol B), `bench/algorithms/twostage_ndsia.py` (Kol C), `bench/algorithms/ndsia.py` (Kol D), `bench/experiments/exp_07b_hybrid.py`, testler.
**Bağımlılık:** 06/06a/06b (Pyramid + eksen-ayrık kapı) ve 07 (Samaan, `focal_error_ppm` dahil) onaylı. Yapı taşları: `SamaanDB` + iç-açı yardımcıları, `pyramid_triad_order`, `kvector_range`, `propagate_full_frame`, `covisible_triples`.
**Tür:** Araştırma deneyi — survey reprodüksiyonu değil. **Negatif sonuç geçerli sonuçtur.**
**Referanslar:** Leake-Arnas-Mortari, *Non-Dimensional Star-Identification*, Sensors 2020 (repoda, "NDSIA makalesi"); Samaan-Mortari-Junkins 2006; Mortari-Samaan-Bruccoleri 2004 (Pyramid); Arnas-Leake-Mortari n-D k-vector AMC 2020 (repoda); Arnas-Fialho-Mortari 2017 (kernel generators).

---

## 1. Literatür konumu ve araştırma sorusu
NDSIA'nın kendisi bir **füzyondur** (Pyramid iskeleti + non-dim öznitelik); makaledeki mod-anahtarlama (Pyramid → TASTE → NDSIA → yeniden kalibrasyon → Pyramid) bunun etrafındaki operasyonel kavramdır. "Füzyon fikri bizim" İDDİA EDİLMEZ. Özgün eksenimiz **öznitelik takası**:
- **Kol B (bizim füzyon):** piksel-düzlemi planar iç açıları — 2 bağımsız öznitelik; f-ölçeklemesine VE OA-ötelemesine **TAM** değişmez (07 ölçümü: 0.0000″ @ 3000 ppm; OA = piksellere saf öteleme, NDSIA makalesi denk. 3).
- **Kol D (sadık NDSIA):** küresel dihedral açılar — **3** bağımsız öznitelik (toplam ∈ (180°,540°)); body-vektör yolundan **birinci-derece** duyarsız (07 ölçümü: 0.7″ @ 3000 ppm), OA ofsetine belirgin duyarlı (makale Test 4–5).
**Soru:** bizim rejimde (14.7° FOV, ~5k yıldız, 1.02M üçlü, ~2351 aday/sorgu) hangisi kazanır — az-ama-tam mı, çok-ama-yaklaşık mı? Makalenin "geniş FOV'da 2-öznitelikli katalog ayırt ediciliğini yitirir" argümanı bizim 07 aday-patlaması bulgumuzdur; deney bunu kendi sensörümüzde sınar.

## 2. Hipotezler (önceden taahhüt)
- **H1:** Kol B, ±3000 ppm boyunca düz (id≈1.0, wa=0).
- **H2:** Kol B işkencede Pyramid-sınıfı (sahte=0, wa=0); saf Samaan spike altında bozulur. Samaan'ın spike davranışı ölçülmedi — **Adım 0 ölçer**; dayanıklı çıkarsa hipotez revize edilir (PM'e dön).
- **H3 (manşet):** ppm × spike birleşik streste ebeveynler düşerken füzyon ayakta kalır.
- **H4:** Aday patlaması × permütasyon = match süresi cezası; ölçülür, saklanmaz.
- **H5 (betimsel):** Kol C kalibrasyon-yalnız eksende ≈ Kol B ve çözüm-sonrası hızlı; birleşik streste bootstrap zehirlenmesinden çöker (yanlış kimlik → kötü f* → Aşama 2 çöker). Yargı kazanan ilanı değil, "hangi mimari hangi rejimde" kılavuzu.
- **H6 (ana soru):** Kalibrasyon eksenlerinde B vs D profili — makale argümanı doğruysa D'nin *tamamlama* oranı yoğun rejimde B'den yüksek; bozulma büyüdükçe B'nin tam değişmezliği avantaja dönmeli.
- **H7 (teoriden yanlışlanabilir öngörü):** OA ekseninde B **düz** (öteleme-değişmezliği), D düşer (makale Test 4–5 imzası), Pyramid neredeyse etkilenmez. Üçü tek figürde.

## 3. İş 0 — Sahne eki: OA ofset bozulması (`scene.py`, küçük; `focal_error_ppm` zaten var)
`NoiseConfig.oa_offset_error_frac: float = 0.0` (yarı-imager genişliği oranı; makale Tablo 1 birimi). Sahne gerçek asal noktayı kaydırıp projekte eder (denk. 3 modeli), gözlemci nominali varsayar. Kabul: oa=0 → bit-bit regresyon; oracle her bozulmada id=1.0.

## 4. Adım 0 — Taban çizgileri (implementasyondan ÖNCE, atlanamaz)
Mevcut **Pyramid ve Samaan**, deney ızgarasında (bölüm 8) koşulur → `results/exp07b_baseline.{csv,png}` (id_rate + wrong_attitude ısı haritaları). Beklenti: Pyramid ppm/OA'da değil spike'ta sağlam ama kalibrasyonda çöker; Samaan spike'ta bozulur. Beklenti tutmazsa hipotez revizyonu için PM'e dönülür.

## 5. Kol B — Füzyon (`nondim_pyramid.py`)
- **DB:** `SamaanAlgorithm.build_database` AYNEN (ek maliyet 0; raporda doğrula).
- **extract:** Samaan'ın piksel-düzlemi planar iç açıları (import).
- **match (Pyramid iskeleti):**
  1. `pyramid_triad_order(f)` (import; en-parlak kısıtı yok).
  2. Üçlü başına non-dim sorgu: `kvector_range(θ_min±tol)` + θ_max filtresi + köşe ataması; `max_candidates_per_triple` tavanı Samaan'dan; **tam-1 tutarlı atama** kuralı Pyramid'den (0 veya ≥2 → atla; Samaan'ın oy havuzu YOK — merkezi tasarım kararı, raporda gerekçelendir).
  3. **Non-dim piramit onayı:** 4. gözlem r ile C(4,3)=4 üçgenin DÖRDÜ tutarlı; `n_confirm_stars=2` → en az 2 farklı r.
  4. Çekirdek artık kapısı `consensus_gate_arcsec=300` (Samaan gerekçesi: ±3000 ppm bozulması ≤~80″ ≪ 300″ ≪ derece-mertebesi sahtekâr; 06a'nın 20″'si ppm altında gerçek çözümleri öldürür — bilinçli fark).
  5. `min_extra_stars≥1` + `propagate_full_frame`.
- `NonDimPyramidConfig` — tüm sabitler parametrik; ebeveyn default'ları değiştirilmez.

## 6. Kol C — LAM-stili iki-aşama (`twostage_ndsia.py`)
1. **Aşama 1:** `SamaanAlgorithm.match` (import) → kimlikler; `[]` ise `[]` döndür.
2. **`_estimate_focal` (modül-içi, birim-testli):** eşleşmiş çiftlerde gözlenen piksel geometrisinden `θ_obs(f)`, katalogtan `θ_cat`; tek parametreli EKK: `f* = argmin Σ(θ_obs(f)−θ_cat)²` (kaba tarama + parabolik incelik / minimize_scalar). Teşhis: `last_focal_estimate_ppm`.
3. **Aşama 2:** body vektörler `f*` ile pikselden YENİDEN türetilir; `PyramidAlgorithm.match` bu vektörlerle (Pyramid kodu değişmez).
> Aşama 1 kimlik hataları f*'ı zehirler → Aşama 2 çöker; gizlenmez, H5 bunu ölçer. (Not: OA kestirimi bu turda YOK — yalnız f; OA hücrelerinde C'nin sınırlılığı raporda açıkça yazılır.)

## 7. Kol D — Sadık NDSIA (`ndsia.py`)
Makaleden birebir (sapmalar dokümante):
1. **DB:** co-visible üçlüler (paylaşılan) → ara açılar (denk. 4) → **dihedral açılar** (denk. 5; en küçük ara açıya göre dal; kalanlar sinüs kuralı denk. 6 — makale tanjantın fark yaratmadığını raporluyor; π/2 belirsizlik notu). Artan sıralı (A,B,C) + köşe-eşli hip'ler.
2. **Arama:** sadık yol 3-D NDKV; **izinli sapma:** ilk açıda 1-D `kvector_range` + kalan ikide filtre (bizim ölçekte yeterli; NDKV gerekirse-yükseltme, raporda not). ε = 3σ_centroid (dihedral uzaya yansıtma türetimi dokümante) + **L2 kontrolü** (denk. 1): tam-1 eşleşme VE √(ΔA²+ΔB²+ΔC²) < ε.
3. **Kernel:** `pyramid_triad_order` (makalenin pattern-shifting ailesi; denklik notu).
4. **Onay:** r: {r,i,j},{r,i,k},{r,j,k} üçü unique; r₂: 6 üçgen ({i,j,r₂},{i,k,r₂},{j,k,r₂},{i,r,r₂},{j,r,r₂},{k,r,r₂}) hepsi unique. Kalan yıldızlar r-protokolü; **final kontrol:** tüm tanınan çiftlerin ara açıları < FOV, ihlalde `[]`. Yayılım YOK (makale protokolü aynen).

## 8. Deney matrisi (`exp_07b_hybrid.py`)
σ=5″, ≥40 deneme/hücre, 5 çizgi: Pyramid, Samaan, B, C, D. Hücre patlamasını önlemek için üç düzlem:
- **Düzlem 1 (ppm×spike, OA=0):** ppm ∈ {0,1500,3000} × spike ∈ {0,10,30,63} → H1–H5 + H6'nın f-ayağı.
- **Düzlem 2 (OA×spike, ppm=0):** OA ∈ {0, %0.5, %2} × spike ∈ {0,30} → **H7 figürü**.
- **Köşe hücresi:** (3000 ppm, %2 OA, 63 spike) — birleşik stresin ucu.
Ek bloklar: **işkence** (tam-5-gerçek, σ∈{0,5}, ≥50 deneme, kimlik-düzeyi sahte sayımı + saf-roll ayrımı + tripwire — 06a/06b standardı); **maliyet tablosu** (match ms, denenen üçlü medyanı, C için Aşama1/kestirim/Aşama2 ayrışımı); **f* doğruluk mini-tablosu** (kestirim hatası vs enjekte ppm; spike'sız hücrelerde |hata| < ~200 ppm).
Çıktılar: `results/exp07b_baseline.*`, `exp07b_grid.*` (manşet, 5 çizgi), `exp07b_torture.csv`, `exp07b_cost.csv`.

## 9. Kabul testleri
1. İş 0 regresyon (oa=0 bit-bit; oracle 1.0 her bozulmada).
2. `_estimate_focal`: tam-doğru kimliklerle enjekte ppm'i <50 ppm hatayla geri kazanır; %20 yanlış kimlikte zehirlenme eğrisi raporlanır.
3. NDSIA dihedral hesabı brute-force küresel trigonometriyle birebir; nominal koşulda **n+id=%100 imzası** (yanlış tanıma 0 — makalenin "never completes unsuccessfully" özelliği bizim kurguda da tutmalı).
4. Kol B: gürültüsüz id ≥0.99, wa=0; T1-tarzı determinizm.
5. H7 figürü üretilir; öngörü tutuyor/tutmuyor açık yazılır.
6. Başarı kriterleri: **Başarı** = H1 ∧ H2 ∧ (Düzlem-1'in ≥%80 hücresinde B ≥ max(ebeveyn), wa=0 korunarak). **Kısmi** = H1∧H2 tutar, köşede B de düşer → "stres çarpımı" analizi. **Başarısızlık** = H1 veya H2 çürür → mekanizma teşhisi + negatif-sonuç raporu. H5/H6/H7 betimsel, Faz 6'ya kılavuz paragrafı.

## 10. Yapma
- Ebeveyn dosyalarını (samaan/pyramid/sla) değiştirme — yalnız import.
- Adım 0'ı atlama; ızgara hücre/deneme sayısını sonuca göre kırpma.
- NDKV'yi bu turda implement etme; Kol B'yi dihedral'e geçirme (B'nin değeri tam değişmezliğinde).
- Makale Tablo 3'ü reprodüksiyon hedefi yapma — sensör/katalog farklı; yalnız *imzalar* karşılaştırılır (OA asimetrisi, n+id=100).
- Kapı/tolerans/ε sabitlerini "test geçsin" diye ayarlama; değişiklik önerisi PM'e.
- "LAM reprodüksiyonu" yalnız Kol D için ve sapma listesiyle iddia edilir; Kol B/C tasarımı bizimdir, öyle yazılır.
