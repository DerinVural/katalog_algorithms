# Brief 07 — Samaan Non-Dimensional Star-ID (2003/2006) (Faz 3 açılışı)

**Hedef dosya:** `bench/algorithms/samaan_nondim.py` (+ `bench/tests/test_samaan.py`)
**Bağımlılık:** Faz 2 kapandı; `kvector_range`/`build_kvector` (SLA'dan import), Liebe'nin teğet-düzlem iç-açı yardımcısı (varsa import, yoksa yerel eşdeğer).
**Referans:** Spratling & Mortari §4; Samaan, Mortari & Junkins, *Nondimensional star identification for uncalibrated star cameras*, J. Astronaut. Sci. 2006.
**Faz 3 sırası:** 07 Samaan → 08 Padgett Grid → 09 Rousseau; 07b (araştırma: non-dim iç açıları × Pyramid makinesi) ancak 07 onaylanınca açılır.

> Yeni eksen: **kalibrasyon robustluğu**. Şimdiye kadarki tüm algoritmalar ara açı kullandı — ara açı, odak uzaklığı hatasıyla doğrudan ölçeklenir (Liebe tutorial Fig. 23: boresight doğruluğu odak uzaklığına *mikron* hassasiyetinde bağlı). Samaan'ın fikri: üçgenin **iç açıları** görüntü düzleminde odak-uzaklığı ölçeklemesine birinci dereceden değişmezdir (radyal ölçekleme düzlem açılarını hiç değiştirmez). Sıcaklık çevrimiyle kayan kalibrasyon → SLA/Liebe bozulur, Samaan ayakta kalır — kanıtlanacak iddia bu.

---

## İş 0 — Küçük core eki (yalnız `scene.py`): kalibrasyon bozulması enjeksiyonu
`NoiseConfig`'e `focal_error_ppm: float = 0.0` ekle. Sahne, yıldızı piksel düzlemine **gerçek** odak uzaklığı `f·(1+ppm·1e-6)` ile projekte eder; gözlemci (pinhole geri-dönüşü) **nominal** `f` kullanır — gerçek dünyadaki kalibrasyon hatasının birebir modeli. Centroid gürültüsü mevcut piksel-yolu üzerinde aynen. Kabul: `focal_error_ppm=0` ile mevcut tüm testler bit-bit regresyonsuz; oracle, ±3000 ppm'de bile id_rate=1.0 (oracle truth'tan eşleştiği için bozulmadan etkilenmez — sahne doğruluğunun kontrolü).

## Algoritma

### Feature: üçgen iç açıları
Üçgen (A,B,C), her köşede bir iç açı; **θ_min + θ_mid + θ_max ≈ π** (küresel fazlalık küçük FOV'da ihmal) → yalnız **2 bağımsız** öznitelik: `(θ_min, θ_max)`. (Boyutlu üçgenin 3 bağımsız özniteliğinden biri, ölçek değişmezliğine harcandı — non-dim'in bilgi bedeli; raporda bu cümle geçsin.)

### `build_database(catalog)` — O(n·f²) üçlü kataloğu + k-vector
Triangle planar'ın co-visible üçlü enumerasyonunu yeniden kullan (import/ortaklaştır). Her üçlü için inertial vektörlerden **küresel iç açılar**: köşe B'de, A ve C'nin B'nin teğet düzlemine izdüşümleri arasındaki açı (Liebe'nin `theta` hesabıyla aynı mekanizma — import et). Kayıt: `(θ_min, θ_max, hip_min, hip_mid, hip_max)` — hip'ler iç açısına göre eşlenmiş sırada (köşe ataması aramada bedavaya gelsin). `θ_min`'e göre sırala + **k-vector** kur (SLA'dan import). DB büyük (Triangle sınıfı) — bilinçli; kazanç bellek değil, robustluk.

### `extract_features(observed)` — DÜZLEMSEL, `centroid_px`'ten
Gözlem üçlülerinin iç açıları **piksel koordinatlarından** (BodyVector.centroid_px) düz trigonometriyle hesaplanır — body vektörlerden DEĞİL. Değişmezlik tam burada yaşar: body vektörler (yanlış) nominal pinhole'dan geçer ve bozulmayı içeri taşır; düzlem iç açıları radyal ölçeklemeden hiç etkilenmez. f<3 → boş.

### `match(features, db)`
Her gözlem üçlüsü: `kvector_range(θ_min ± tol_θ)` → adaylarda `|θ_max−θ_max'| < tol_θ` filtresi → sıra-eşlenmiş köşe ataması → oy. **Samaan'ın bulgusu: en az 5 yıldız tutarlı eşleşmeden çözüm üretme** (`min_match_stars=5`, config) — iki bağımsız öznitelikli üçgen tek başına ayırt edici değildir, erken çözüm sahte üretir. Oylar → global birebir (`_resolve` deseni) → <5 → `[]`. `use_core_verify` ablation anahtarı (Faz 2 politikası devam).

Tolerans: `tol_theta_deg=0.5` başlangıç (iç açı, ara açıdan farklı birim ölçeğinde; gürültüsüz ≥0.99 verecek şekilde kalibre et, config'te).

## Kabul testleri
1. **T-calib (tanımlayıcı test):** `focal_error_ppm ∈ {0, ±1000, ±2000, ±3000}` (Liebe Fig. 23 aralığı), σ=5″: Samaan id_rate düz kalmalı; **aynı taramada Liebe ve SLA** kıyas eğrisi (bozulmaları görünsün). Çıktı `results/calib_sweep.{csv,png}` — Faz 3'ün açılış figürü.
2. Gürültüsüz: id_rate ≥ 0.99, wrong_attitude=0 (eksen-ayrık kapı).
3. Gürültü grace: σ ∈ {2,5,10}″ eğrisi.
4. **min_match_stars ablation:** 5→3 düşürülünce wrong_attitude artmalı (Samaan'ın ≥5 bulgusunun ampirik kanıtı).
5. Determinizm; DB boyutu tablosu (Triangle ile aynı mertebe beklenir, raporla).

## Yapma
- Gözlem iç açılarını body vektörlerden hesaplama (değişmezliği öldürür — en olası hata bu).
- k-vector/üçlü-enumerasyon kodunu kopyalama; import/ortaklaştır.
- Pyramid melezini burada deneme (07b'nin işi).
- Kapı/tolerans sabitlerini "test geçsin" diye oynama.
