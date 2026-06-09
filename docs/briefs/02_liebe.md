# Brief 02 — Liebe (1992) (Faz 1)

**Hedef dosya:** `bench/algorithms/liebe.py` (+ `bench/tests/test_liebe.py`)
**Bağımlılık:** Faz 0 bench core (onaylandı).
**Referans:** Spratling & Mortari §3 (Liebe 1992) + Liebe, *Pattern recognition of star constellations*, IEEE AES Mag. 1992.
**Survey Tablo 1 hedefi:** Feature O(f·lg b), DB boyutu **O(n)**, search **O(n)** (lineer).

> Format brief 01'in aynısı. Yalnız `StarIDAlgorithm` kontratını dolduran tek dosya yaz; bench core'a dokunma. Kontrat eksik gelirse PM'e bildir (kontratı kendi başına değiştirme).

---

## Amaç
Liebe'nin "merkez yıldız + 2 en yakın komşu" pattern'ini uygula. Bu, lost-in-space'i ilk *tractable* yapan yöntem ve KAT-02'nin en sade çekirdeği.

## Algoritma tanımı

### Pattern (feature)
Her yıldız için, ona **en yakın 2 yıldız** alınır. Feature üçlüsü:
- `d1` = merkez yıldıza en yakın yıldızın açısal uzaklığı (rad),
- `d2` = ikinci en yakın yıldızın açısal uzaklığı (rad),  `d1 ≤ d2`,
- `theta` = bu iki komşunun merkez yıldızdaki **iç açısı** (rad), `acos(û1·û2)`.

(Survey Fig. 4: "2 inter-star angle + 1 interior angle".) Açısal uzaklık = `acos(clip(u_a·u_b, -1, 1))`.

### `build_database(catalog)`  → DB boyutu O(n)
Her katalog yıldızı için:
1. KD-tree ile en yakın komşularını bul (`catalog.kdtree` / `query_radius`); FOV yarıçapı içindeki adaylardan **en yakın 2'sini** seç.
2. `(d1, d2, theta, hip_center, hip_n1, hip_n2)` kaydet.
3. ≥2 komşusu olmayan yıldızı atla.
Sonuç: yıldız başına bir kayıt → **O(n)** kayıt. Aramayı hızlandırmak için `d1`'e göre sıralı bir numpy dizi tut (lineer/iki-uçlu daraltma için; binary-tree'ye geçiş **Quine = brief 04**, burada yapma).

> **Katalog erişim kuralı:** yalnız `catalog.vectors`, `catalog.kdtree`, `catalog.query_radius`, `catalog.by_id`, `catalog.hip_ids` kullan. Truth'a erişme.

### `extract_features(observed)`  → O(f·lg b)
Gözlenen her yıldız için aynı (d1, d2, theta)'yı hesapla (en yakın 2 gözlem). Çıktı: gözlem başına `(obs_center, obs_n1, obs_n2, d1, d2, theta)`.

### `match(features, db)`  → O(n) lineer
Her gözlem pattern'i için DB'de tolerans içinde eşleşen katalog pattern'lerini ara:
`|d1−d1'| < tol_d`, `|d2−d2'| < tol_d`, `|theta−theta'| < tol_t`.
Eşleşen her aday, merkez gözlem ↔ merkez katalog yıldızı için bir oy üretir. Tüm gözlemler tarandıktan sonra **tutarlı** eşleşme kümesi seçilir (aynı obs_id'ye en çok oyu alan hip; çelişkili/çoklu adaylar elenir). Çıktı `list[CandidateMatch]`.

### Liebe'nin ele aldığı iki incelik (uygula)
1. **d1 ≈ d2 belirsizliği:** iki en yakın uzaklık birbirine `tol_d` kadar yakınsa, hem (n1,n2) hem (n2,n1) sıralamasıyla dene (theta zaten simetrik değil; her iki atamayı da aday yap).
2. **Eşik civarı kaçan yıldız:** magnitude limitine yakın bir komşu görülemeyebilir; bu yüzden tek bir merkez yıldızın eşleşememesi tüm çözümü düşürmemeli — oylama çoğunluğa dayanır.

## Toleranslar (parametrik)
`LiebeConfig(tol_d_arcsec=15.0, tol_theta_deg=0.5, min_votes=2)` gibi. Sensör ölçeği 25.8″/px; `tol_d` ≈ birkaç × beklenen centroid hatası. Default'lar gürültüsüz sahnede ≥%99 id-rate verecek, gürültüde grace ile düşecek şekilde seçilsin. Tüm eşikler config'te, sabit gömme yok.

## Kabul testleri (`test_liebe.py`)
1. **Gürültüsüz, zengin sahne** (≥8 yıldız): `id_rate ≥ 0.99`, `false_id = False`, attitude hatası < birkaç arcsec.
2. **DB boyutu O(n):** kayıt sayısı = ≥2 komşulu katalog yıldızı sayısı; `db_size_bytes` Liebe < (ileride) triangle DB'si (brief 03 ile karşılaştırmalı — şimdilik sadece kaydet).
3. **d1≈d2 vakası:** elle kurulmuş, iki en yakın komşusu neredeyse eşit uzaklıkta bir merkez yıldız doğru eşleşir.
4. **Gürültü grace:** centroid σ ∈ {2,5,10,20}″ taramasında id_rate monotonca düşer ama σ=5″'te ≥%90 kalır (eğri `results/`'a).
5. **Spike toleransı:** 3 spike eklenince false_id nadir; Liebe Pyramid kadar robust değildir — beklenen davranış, sadece *katastrofik* yanlış-attitude olmadığını doğrula (mümkünse çözümsüzlük > yanlış çözüm).
6. **Determinizm:** sabit seed → aynı sonuç.

## Yapma
- Binary-tree / k-vector arama yapma (sırasıyla Quine=04, SLA=05).
- Magnitude'u feature'a katma (Liebe magnitude'u kullanmaz; survey: "neglecting the stellar magnitudes").
- Bench core'u veya kontratı değiştirme.
