# Brief 06 — Pyramid (Mortari 2004) (Faz 2 finali)

**Hedef dosya:** `bench/algorithms/pyramid.py` (+ `bench/tests/test_pyramid.py`)
**Bağımlılık:** Brief 05 (SLA) onaylandı — `build_kvector` / `kvector_range` oradan **import edilir**.
**Referans:** Spratling & Mortari §3.3; Mortari, Samaan & Bruccoleri, *The Pyramid star identification technique*, Navigation 2004.
**Survey konumu:** Arama problemi SLA ile çözüldü; Pyramid'in tüm katkısı **non-star (spike) reddi** — "robustness to non-star spikes was essential towards reducing the number of iterations". Survey'in referans verdiği işkence testi: **5 gerçek yıldız + 63 spike** içeren görüntüde doğru kimliklendirme.

> Hikâye burada tersine döner: önceki brief'lerde soru "doğru eşleşmeyi ne kadar hızlı bulursun"du; Pyramid'de soru "sahte yıldızlarla dolu bir görüntüde **yanlış eşleşmeyi nasıl reddedersin**". KAT-02 için uçuş-sınıfı güvenilirliğin referans noktası.

---

## Amaç
k-vector tabanlı üçgen eşleme + **4. yıldızla piramit doğrulaması** + spike'lardan hızla uzaklaşan **akıllı üçlü tarama permütasyonu**. Native doğrulama bu algoritmanın *tanımıdır* — Triangle'daki gibi sonradan eklenmiş değil, aday-üretiminin içine örülüdür.

## Tasarım

### `build_database(catalog)` — SLA ile AYNI
Çift kataloğu + k-vector. `sla_kvector.SLAAlgorithm.build_database`'i **aynen çağır** (veya `SLADB`'yi yeniden kullan); kopya kod yok. DB boyutu SLA ile birebir aynı — raporda "ek DB maliyeti: 0" notu düşülsün.

### `extract_features(observed)` — O(f²) çift açıları
Tüm gözlem çiftlerinin ara açıları (Pyramid herhangi üçlüyü deneyebilmeli; en-parlak-4 kısıtı YOK — SLA'dan fark). f tipik 15–20, C(f,2) küçük; vektörize hesapla.

### `match(features, db)` — Pyramid döngüsü
1. **Akıllı üçlü permütasyonu (Mortari'nin "smart technique"i):** üçlüler `(i, j, k)` öyle sıralanır ki ardışık denemeler aynı yıldızda ısrar etmez — kalıcı bir spike'ın denemeleri arka arkaya zehirlemesi engellenir. Mortari 2004'ün indeks deseni: `dj=1..f-2, dk=dj+1..f-1, i=1..f-dk` üzerinden `(i, j=i+dj, k=i+dk)` üret — küçük kaydırmalı kombinasyonlar önce, herhangi tek yıldıza bağımlılık hızla değişir. Bu sırayı ayrı, **birim-test edilebilir** bir `pyramid_triad_order(f)` fonksiyonu yap (T1).
2. **Üçlü eşleme:** üçlünün 3 çift açısı için 3 `kvector_range` sorgusu → 3 aday çift listesi → ortak-yıldız mantığıyla tutarlı `(hipI, hipJ, hipK)` atamaları. **Tam 1 tutarlı atama** yoksa (0 veya ≥2 belirsiz) üçlüyü reddet, sıradakine geç. (Belirsizlikte ısrar etmemek Pyramid'in hız sırrıdır.)
3. **Piramit doğrulaması:** tutarlı üçlü bulununca, kalan gözlemlerden bir **4. yıldız r** seç; `(i,r), (j,r), (k,r)` üç açısı da k-vector'de aynı `hipR` ile tutarlıysa **piramit onaylandı** → kimliklendirme kabul. Hiçbir r onaylamazsa üçlü reddedilir (büyük olasılıkla içinde spike var), permütasyon devam eder.
4. **Tüm üçlüler tükenirse** → `[]` (çözümsüz; yanlıştan iyidir).
5. **Yayılım:** onaylı 4'lüden attitude (QUEST) → SLA'daki tam-kare direct-match yayılımının aynısı (`_propagate`'i import et / paylaş). SLA sapma şerhi burada da geçerli; raporda aynı dipnot.
6. `PyramidConfig(use_core_verify: bool=False)` — Faz 2 ablation politikası: **native** = piramit onayı (algoritmanın kendisi); **ablation** = piramit onayı KAPALI (`confirm_pyramid=False` anahtarı: ilk tutarlı üçlü, 4. yıldız onayı olmadan kabul) + ayrıca `+core_verify` modu. Üç mod da raporlanır — Triangle'daki `require_confirm` ablation'unun birebir karşılığı; Pyramid'in katkısını izole eden deney budur.

> Tolerans `tol_angle_arcsec=15.0` (zincirle aynı). Katalog erişim kuralı aynı; truth yok.

## Kabul testleri (`test_pyramid.py`)
1. **T1 — permütasyon birim testi:** `pyramid_triad_order(f)` (a) tüm C(f,3) üçlüyü tam bir kez üretir; (b) ardışık ilk ~f denemede hiçbir yıldız indeksi tüm üçlülerde ortak değildir (tek spike'a ısrar yok); (c) deterministiktir.
2. **T2 — işkence testi (survey referansı):** zengin sahne, gerçek yıldızlar 5'e indirilir (`p_missing` ile) + **63 spike** eklenir. ≥50 denemede: `wrong_attitude = 0` ZORUNLU; id_rate (5 gerçek üzerinden) yüksek; çözümsüzlük kabul edilebilir ama nadir olmalı. Çıktı `results/pyramid_torture.csv`.
3. **T3 — spike taraması (Faz 2 finali kıyası):** n_spikes ∈ {0, 3, 5, 10, 20} × σ=5″'te Pyramid vs SLA vs Liebe vs Quine vs Triangle — id_rate, no_solution_rate, wrong_attitude_rate. Tek grafik + CSV (`results/phase2_spike_sweep.{csv,png}`). Beklenti: spike arttıkça Pyramid'in wrong_attitude'u 0'da kalır, diğerlerinde no_solution/wrong artışı görünür.
4. **T4 — ablation üçlüsü:** σ=8″+10 spike'ta {native piramit, piramit-kapalı, piramit+core_verify} üç modu; piramit-kapalı modda wrong_attitude belirgin artmalı → Pyramid'in katkısının kanıtı.
5. **T5 — gürültüsüz taban:** id_rate ≥ 0.99, wrong_attitude = 0.
6. **T6 — determinizm.**

## Raporda istenen (PM review için)
- T3 grafiği Faz 2'nin kapanış figürüdür: dört algoritmanın spike altında davranış imzaları.
- Üçlü deneme sayısı istatistiği (spike sayısına göre medyan kaç üçlü denendi) — "permütasyon zehirden hızla uzaklaşır" iddiasının ölçümü.
- DB paylaşımı doğrulaması: Pyramid DB'si == SLA DB'si (ek maliyet 0).

## Yapma
- k-vector / çift kataloğu kodunu kopyalama — `sla_kvector`'dan import.
- Yıldız parlaklığını kullanma (Pyramid kullanmaz; magnitude ekseni Scholl/Faz planı kararına bağlı).
- core veya kontratı değiştirme.
- T2'de toleransı gevşetme/sıkılaştırma — zincirle aynı 15″; işkence testi *bu* toleransta geçmeli.
