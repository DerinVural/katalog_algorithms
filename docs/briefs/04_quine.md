# Brief 04 — Quine (1996) (Faz 2)

**Hedef dosya:** `bench/algorithms/quine.py` (+ `bench/tests/test_quine.py`)
**Bağımlılık:** Faz 1 (Liebe) + Brief 03b (metrik ayrımı + core/verify) tamam.
**Referans:** Spratling & Mortari §3.1 (Quine 1996).
**Survey Tablo 1 hedefi:** Feature O(f·lg b), DB **O(n)** (Liebe ile aynı), search **O(lg n)** (ikili ağaç).

> Quine'ın tek yeniliği **arama**: Liebe'nin pattern'ini ve O(n) kayıt setini aynen tutar, ama lineer tarama yerine ikili-arama-ağacı kullanıp aramayı O(lg n)'e indirir. Yani Faz 2'nin ilk adımı ve "DB araması nasıl hızlanır"ın ilk cevabı.

---

## Amaç
Liebe ile **tek farkı arama yapısı** olan bir eklenti. Aynı feature, aynı kayıtlar → sonuç birebir aynı olmalı; yalnız `match` ölçeklemesi O(n)'den O(lg n)'e insin. Bu, adil karşılaştırmanın en saf hâli: tek değişken arama.

## Tasarım — Liebe'yi yeniden kullan
Feature ve kayıt üretimini **kopyalama**, `liebe.py`'den içe aktar:
- `extract_features`: `LiebeAlgorithm.extract_features`'ı aynen kullan (merkez + en yakın 2 → `(d1,d2,theta)`).
- Kayıt seti: `LiebeAlgorithm.build_database` ile aynı kayıtlar (`neighbors_k` dahil aynı config alanı).

### `build_database(catalog)` → O(n), index: ikili ağaç / k-d tree
Liebe'nin kayıtlarını al, `(d1, d2, theta)` öznitelik uzayında **dengeli bir arama yapısında** indeksle:
- `scipy.spatial.cKDTree`'yi 3-B ölçekli öznitelik vektörü üzerinde kur. Açıları toleransla uyumlu ölçekle (örn. `theta`'yı `tol_d/tol_theta` oranıyla ölçekle ki kutu sorgusu üç eksende de doğru olsun).
- DB boyutu Liebe ile **aynı O(n)** (kayıt sayısı aynı; ek indeks sabit-çarpan).

### `match(features, db)` → O(lg n)
Her gözlem pattern'i için öznitelik uzayında **aralık (kutu) sorgusu** (`query_ball_point`, yarıçap = toleransın ölçekli karşılığı) → aday kayıtlar → Liebe ile aynı oylama + global birebir (`_resolve`'u Liebe'den içe aktar veya birebir aynı mantık). d1≈d2 belirsizliği Liebe'deki gibi ele alınır (her iki sıralama sorgulanır).

> Katalog erişim kuralı brief 02/03 ile aynı; truth'a erişme.

## Doğrulama politikası (Faz 2 — ZORUNLU, her algoritmada)
Quine'ın native'inde **ekstra doğrulama yoktur** (Liebe gibi, sadece oylama). Yine de Faz 2 kıyasının apples-to-apples olması için her algoritma **iki modda** raporlanır:
- **native:** algoritmanın kendi (yayınlandığı) doğrulamasıyla — Quine için: doğrulama yok.
- **+ortak doğrulayıcı:** `core/verify.ransac_confirm` çıktıya uygulanmış hâliyle.
`QuineConfig(use_core_verify: bool = False)` ile aç/kapa. Bu sayede Faz 2 sonunda (Pyramid gelince) robustluğun ne kadarı pattern, ne kadarı doğrulama net ayrılır.

## Kabul testleri (`test_quine.py`)
1. **eşdeğerlik (en önemli):** sabit gürültüsüz/gürültülü sahnede Quine'ın eşleşme kümesi Liebe'ninkiyle **aynı** (sıra bağımsız). Aynı feature+kayıt+tolerans → aynı sonuç; tek fark hız.
2. **gürültüsüz id_rate ≥ 0.99**, false_id (yeni anlam: yalnız yanlış attitude) = 0.
3. **ölçekleme (Tablo 1 doğrulaması):** katalog n ∈ {1k, 2k, 4k, ~5k} alt-örneklemleriyle `match` medyan süresi ölç; Quine ~**O(lg n)**, Liebe (lineer pencere) ~**O(n)** trendi. Çıktı `results/quine_scaling.{csv,png}`. (Liebe'nin mevcut `searchsorted` penceresi de kısmen logaritmik; yine de pencere-içi tarama n ile büyürken Quine'ın kutu-sorgusu büyümez — kontrast bu eksende gösterilsin.)
4. **native vs +verify:** spike senaryosunda (σ=8″+5 spike) iki mod raporlanır; `use_core_verify=True` `wrong_attitude_rate`'i düşürür.
5. **determinizm:** sabit seed → aynı.

## Zamanlama adil-kıyas notu
`extract` süresi implementasyon-bağımlı (Liebe Python döngüsü). **Kıyaslanabilir eksen `match` süresi.** Quine `extract`'i Liebe'den miras aldığı için extract süreleri eşittir; gerçek fark `match`'te görünür — istenen sonuç.

## Yapma
- Feature/kayıt mantığını kopyalama; Liebe'den içe aktar (tek değişken = arama).
- k-vector kullanma (o SLA = Brief 05).
- core veya kontratı değiştirme.
