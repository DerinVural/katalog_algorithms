# Brief 05 — Mortari SLA / k-vector (1997) (Faz 2)

**Hedef dosya:** `bench/algorithms/sla_kvector.py` (+ `bench/tests/test_sla.py`)
**Bağımlılık:** Brief 04 (Quine) onaylandı; core/verify mevcut.
**Referans:** Spratling & Mortari §3.3 (Mortari 1997, SLA); Mortari, *K-vector range searching techniques* (2000); Mortari, *Search-less algorithm for star pattern recognition*, J. Astronaut. Sci. 1997.
**Survey Tablo 1 hedefi:** Feature **O(b)**, DB **O(n·f)** (çift kataloğu), search **O(k)** — **DB boyutundan bağımsız**, validation O(b·k²).

> Faz 2'nin asıl sıçraması. Quine, Liebe'nin pattern'ini hızlı aradı (O(lg n)); SLA pattern'i **değiştirir** (herhangi yıldız çifti + ara açı) ve aramayı DB boyutundan tamamen koparır: sorgu maliyeti yalnız tolerans içindeki aday sayısına (k) bağlıdır. KAT-02'nin merkezi mekanizması.

---

## Amaç
k-vector range search üzerine kurulu Search-Less Algorithm. İki yeni parça: (1) **çift kataloğu** — FOV içine sığabilen tüm yıldız çiftlerinin ara açıları; (2) **k-vector** — sıralı bu dizide aralık sorgusunu O(1)-erişimle yapan önhesaplı indeks. Üstüne SLA'nın çoklu-çift cross-check doğrulaması.

## Algoritma tanımı

### `build_database(catalog)` → çift kataloğu O(n·f) + k-vector
1. **Çift kataloğu:** her yıldız için `query_radius(u, FOV_çapı)` ile komşuları al; her (i<j) çifti için `cos(açı)` (veya açı — birini seç, tutarlı kal; öneri: **cos**, monotonluk ters ama hesap ucuz; dokümante et) + `(hipA, hipB)` kaydet. Dedup (her çift bir kez). Beklenen boyut ~ n·f/2 mertebesi.
2. Açıya göre **sırala**.
3. **k-vector inşası (Mortari 2000):** sıralı dizi `y(1..m)` üzerinde uç noktalardan geçen doğru `z(i) = a·i + b` (a=(y_m−y_1)/(m−1), b=y_1−a; pratik sağlamlık için Mortari'nin ξ=ε makine-epsilon kaydırması uygulanabilir, dokümante et). `K[i] = z(i) doğrusunun altında kalan eleman sayısı` — yani `K[i] = count(y ≤ a·i+b)`. Tamsayı dizi, boyut m+1.
4. DB nesnesi: `pair_angles (sorted), pair_hipA, pair_hipB, K, a, b, catalog`.

### k-vector sorgusu (çekirdek yardımcı — ayrı, test edilebilir fonksiyon)
`kvector_range(db, y_lo, y_hi) -> slice`:
- `i_lo = floor((y_lo − b)/a)`, `i_hi = ceil((y_hi − b)/a)` (sınır kıskaçları ile),
- başlangıç `K[i_lo]`, bitiş `K[i_hi]` → aday dilim; dilimin **iki ucunda** gerçek `y` değerleriyle daraltma (k-vector "en fazla birkaç eleman taşar" garantisi; Mortari 2000).
- **Hiç ikili arama yok, hiç ağaç yok** — iki aritmetik işlem + dizi erişimi. O(1)-erişim + O(k) aday. Bu fonksiyonun *kendi başına* doğruluğu test edilir (aşağıda T1).

### `extract_features(observed)` → O(b)
SLA orijinali: görüntüden **4 yıldız** seç (b=4) → C(4,2)=6 ara açı. Seçim: en parlak 4 (deterministik; spike dayanımı Pyramid'in işi — burada basit tut). f<4 ise eldeki b yıldızla C(b,2) çift (b≥3 şart, yoksa boş feature).

### `match(features, db)` → O(k) arama + O(b·k²) cross-check
1. Her gözlem çifti için `kvector_range` ile tolerans aralığındaki aday katalog çiftlerini al (her sorgu bir aday listesi, tipik k~50–200).
2. **Cross-check (SLA'nın doğrulaması):** 6 aday listesi arasında tutarlılık — aynı katalog yıldızının birden çok listede aynı gözlem yıldızına oturması aranır. Pratik implementasyon: her aday çiftten (obs_i↔hipA, obs_j↔hipB) ve ters atama için oy üret; tüm listelerden oyları topla; her gözlem için en yüksek oyu alan hip + **global birebir** zorlaması (Liebe `_resolve` deseninin çift-tabanlı hâli — `_resolve`'u içe aktarabilir veya yerel eşdeğer yazabilirsin, dokümante et).
3. Tutarlı küme <3 → `[]` (çözümsüz > yanlış).
4. `SLAConfig(use_core_verify: bool=False)` ablation anahtarı (Faz 2 zorunlu politikası): native = SLA'nın kendi cross-check'i; +verify = üstüne `core/verify.ransac_confirm`.

> Katalog erişim kuralı önceki brief'lerle aynı; truth'a erişme. `b=4` ve tolerans `SLAConfig`'te parametrik (`n_pattern_stars=4, tol_angle_arcsec=15.0` — Liebe/Quine ile aynı tolerans ölçeği, adil kıyas).

## Kabul testleri (`test_sla.py`)
1. **T1 — k-vector birim doğruluğu (en kritik):** rastgele sıralı dizide 500 rastgele `(y_lo,y_hi)` sorgusu; `kvector_range` sonucu brute-force `np.searchsorted` sonucuyla **birebir aynı** eleman kümesi. Ayrıca uç vakalar: aralık dizi dışı (boş), tüm dizi, tek eleman.
2. **T2 — search DB-boyutundan bağımsız (Tablo 1'in ana iddiası):** n ∈ {2k, 5k, 10k, 20k} sentetik kataloglarda sorgu başına incelenen aday sayısı (k) ve `kvector_range` aritmetik maliyeti **n'den bağımsız ~sabit**; karşılaştırma için Quine'ın aday/sorgu değeri de aynı tabloya (`results/sla_scaling.csv`). Not: k yoğunlukla büyür, n ile değil — tabloda görünmeli.
3. **T3 — uçtan uca:** gürültüsüz zengin sahne id_rate ≥ 0.99, wrong_attitude = 0; σ=5″ id_rate ≥ 0.90.
4. **T4 — non-star tek-spike dayanımı:** survey'in işaret ettiği özellik — SLA seçilen 4 yıldızdan 1'i spike olsa diğerlerinin kimliğini koruyabilir. En parlak 4'ün 1'i spike olacak kurgu bir sahnede: çözüm ya doğru ya çözümsüz; `wrong_attitude` nadir (≤ T3 seviyesi). (Tam permütasyon optimizasyonu Pyramid = Brief 06; burada yalnız "tek spike çökertmiyor" doğrulanır.)
5. **T5 — native vs +verify ablation:** σ=8″+5 spike'ta iki mod raporu; +verify `wrong_attitude_rate`'i düşürmeli veya eşit tutmalı.
6. **T6 — determinizm:** sabit seed → aynı sonuç.

## Raporda istenen (PM review için)
- DB boyutu (MB) — Liebe O(n) ve Triangle O(n·f²) arasına oturmalı; üç algoritmalı boyut tablosu.
- T2 tablosu + kısa yorum: "k-vector aday sayısı n ile değil tolerans×yoğunlukla ölçeklenir".
- Quine raporundaki dürüst nüansın devamı: duvar-saati vs iş-miktarı ayrımı korunarak.

## Yapma
- Pyramid'in permütasyon optimizasyonunu ekleme (Brief 06).
- Liebe pattern'ini/komşu yapısını kullanma — SLA çift-tabanlıdır.
- core veya kontratı değiştirme; k-vector yardımcıları `sla_kvector.py` içinde kalsın (Pyramid bunları oradan import edecek).
