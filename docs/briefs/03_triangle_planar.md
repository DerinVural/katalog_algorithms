# Brief 03 — Planar Triangle Baseline (Faz 1)

**Hedef dosya:** `bench/algorithms/triangle_planar.py` (+ `bench/tests/test_triangle_planar.py`)
**Bağımlılık:** Faz 0 bench core (onaylandı).
**Referans:** Spratling & Mortari §2 (Junkins 1981 üçgen + sub-catalog soyu); modern, iyi-tanımlı bir üçgen baseline olarak uygulanır.
**Survey Tablo 1 hedefi (Junkins soyu):** DB boyutu **O(n·f²)** (büyük), search lineer/üçgen-eşleme. Bu brief'in amacı tam da bu maliyeti **ölçüp** Liebe'nin O(n)'iyle kontrast oluşturmak.

> Bu, "neden modern yöntemler kazandı"yı sayısal gösteren **baseline**. Hız/bellek için değil, dürüst karşılaştırma için var.

---

## Amaç
Üç yıldızın **ara açılarını** permütasyon-bağımsız anahtar olarak kullanan klasik üçgen eşleştirmesini uygula. Liebe ile aynı katalog, sahne, QUEST, metrik — tek fark feature+DB+search.

## Algoritma tanımı

### Pattern (feature)
Bir yıldız üçlüsü (A,B,C) için 3 ara açı: `aAB, aAC, aBC` (her biri `acos(û_i·û_j)`). Permütasyon belirsizliğini gidermek için **artan sıralı** üçlü `(a_min, a_mid, a_max)` anahtar olarak kullanılır (Scholl/Anderson'ın permütasyon-bağımsızlık fikri).

### `build_database(catalog)`  → DB boyutu O(n·f²)
Bütün C(n,3) üçlüleri **enumerate ETME** (infeasible). Yalnız bir FOV'da **birlikte görülebilir** üçlüleri üret (Junkins'in sub-catalog fikri):
1. Her katalog yıldızı A için, `query_radius(A, FOV_çapı)` ile co-visible komşularını al.
2. Bu komşulardan A ile birlikte tüm (B,C) çiftlerini kur; üçlünün **3 ara açısının da** FOV çapına sığdığını doğrula.
3. Her geçerli üçlü için `(a_min, a_mid, a_max, hipA, hipB, hipC)` kaydet; tekrarları (aynı üçlü kümesi) dedup et.
`a_min`'e göre sıralı numpy dizi tut. Beklenen kayıt sayısı ~ `n × C(f,2)` mertebesinde (milyonlar) — **kasıtlı olarak büyük**; `db_size_bytes` ile ölç ve raporla.

> FOV çapı için `sensor` köşegen FOV'unu kullan (iki yıldız zıt kenarlarda olabilir). Katalog erişim kuralı brief 02 ile aynı; truth'a erişme.

### `extract_features(observed)`
Gözlenen yıldızlardan üçlüler kur. f küçük (~15–20) olduğu için tüm C(f,3) üçlüleri üretmek kabul edilebilir; her biri için sıralı açı anahtarı.

### `match(features, db)`
Her gözlem üçlüsü için, DB'de `(a_min,a_mid,a_max)` anahtarı tolerans içinde eşleşen katalog üçlülerini ara (sıralı dizide `a_min` üzerinden aralık + diğer ikisinde filtre). Aday üçlüler yıldız-yıldız eşleşmelere açılır; **4. bir yıldızla doğrulama** (aday attitude'la 4. yıldızın yerini öngör, gözlemde var mı) yanlış üçlüleri eler. Tutarlı küme → `CandidateMatch` listesi.

## Toleranslar (parametrik)
`TriangleConfig(tol_angle_arcsec=15.0, require_confirm=True)`. Liebe ile **aynı** açısal tolerans ölçeğini kullan ki karşılaştırma adil olsun.

## Kabul testleri (`test_triangle_planar.py`)
1. **Gürültüsüz, zengin sahne:** `id_rate ≥ 0.99`, `false_id = False`.
2. **DB boyutu kontrastı:** `db_size_bytes(triangle_db)` >> `db_size_bytes(liebe_db)` (aynı katalogda); oran raporlanır — survey Tablo 1'in O(n·f²) vs O(n) farkının ampirik kanıtı.
3. **Gürültü grace:** centroid σ taraması; eğri `results/`'a.
4. **Doğrulama adımı işliyor:** 4. yıldız onayı kapatılınca false_id artar, açılınca düşer (mekanizmanın etkisini göster).
5. **Determinizm:** sabit seed → aynı sonuç.

## Karşılaştırma çıktısı (PM için)
Bu brief bitince Liebe vs Triangle ilk **head-to-head** mümkün olur: aynı sahne setinde id_rate, false_id, ölçülen search süresi, DB boyutu. Bunu `results/phase1_compare.csv` olarak üret (runner'a küçük bir karşılaştırma fonksiyonu ekleyerek; core'u değiştirmeden, `bench/compare.py` gibi ayrı dosyada).

## Yapma
- C(n,3) tam enumerasyon yapma (yalnız FOV-co-visible üçlüler).
- k-vector / binary-tree kullanma (sonraki fazlar).
- Bench core veya kontratı değiştirme.
