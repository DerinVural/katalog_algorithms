# Faz 2 / Brief 05 — Mortari SLA / k-vector Tamamlama Raporu

**Brief:** `docs/briefs/05_sla_kvector.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, 6/6 kabul testi (T1–T6) geçti (tüm paket 43/43).
**Uygulayan:** Claude Code (brief uygulayıcısı)
**Dokunulan dosyalar:** `bench/algorithms/sla_kvector.py`, `bench/tests/test_sla.py`.
Bench core / kontrat değişmedi.

---

## 1. Ne yapıldı

Search-Less Algorithm: pattern **değişti** (herhangi yıldız çifti + ara açı) ve arama
DB boyutundan **tamamen koparıldı**.

- **Çift kataloğu** (O(n·f)): FOV çapına (2·fov_radius) sığan tüm yıldız çiftlerinin
  ara açıları (rad). 230719 kayıt.
- **k-vector** (Mortari 2000): sıralı dizide aralık sorgusunu O(1)-erişimle yapan
  önhesaplı tamsayı indeks (`build_kvector` / `kvector_range` — Pyramid buradan import edecek).
- **extract** (O(b)): en parlak b=4 yıldız → C(4,2)=6 ara açı.
- **match**: her çift için `kvector_range` ile aday katalog çiftleri → SLA cross-check
  (en büyük geometrik-tutarlı atama) → çekirdek attitude → **tam-kare yayılım** → opsiyonel
  ortak doğrulayıcı.

## 2. Kabul testleri (T1–T6) — 6/6 PASSED

| # | Test | Sonuç |
|---|---|---|
| T1 | k-vector birim doğruluğu (searchsorted ile birebir) | ✅ 12000+ sorgu + uç vakalar, **0 uyuşmazlık** |
| T2 | search DB-boyutundan bağımsız | ✅ taşma ~sabit (aşağıda) |
| T3 | gürültüsüz id_rate≥0.99, σ=5″≥0.90 | ✅ 1.000 / 1.000 |
| T4 | tek-spike dayanımı | ✅ id_rate 0.93, wrong_att 0.025 |
| T5 | native vs +verify | ✅ verify kötüleştirmiyor |
| T6 | determinizm | ✅ |

## 3. T2 — Aramanın DB-boyutundan bağımsızlığı (Tablo 1'in ana iddiası)

Sentetik kataloglar (sabit-küre, yoğunluk ∝ n), `results/sla_scaling.csv`:

| n | çift kataloğu m | **k-vector taşması** | aday/sorgu (k) |
|---|---|---|---|
| 2 000 | 32 743 | 1.33 | 27 |
| 5 000 | 203 966 | 1.41 | 155 |
| 10 000 | 819 222 | 1.47 | 636 |
| 20 000 | 3 276 212 | 1.25 | 2371 |

**Okuma:** DB (m) **100× büyürken** (32K→3.3M), k-vector'ün gerçek arama maliyeti
(**taşma = bracket dışında incelenen eleman**) **~1.4'te sabit** — yani aramanın yapısal
maliyeti DB boyutundan **tamamen bağımsız**. Aday sayısı k ise **yoğunlukla** büyüyor
(27→2371), n ile değil — survey'in not ettiği gibi (k = indirgenemez sonuç boyutu).
Quine'ın O(lg m) ikili-arama konumlandırmasının aksine k-vector iki aritmetik işlemle
konumlanır; bu, "search O(k), DB-bağımsız" tezinin doğrudan kanıtı.

> Not: brief Quine aday/sorgu'yu aynı tabloya istemişti; Quine `(d1,d2,theta)` (en yakın-2)
> öznitelik uzayını, SLA ise çift-açı uzayını indeksler — aynı sorgu iki yapıda **karşılığı
> olmayan** şeyler olduğundan doğrudan kıyas yanıltıcı. Anlamlı eksen k-vector'ün kendi
> taşma/bracket maliyetinin m'den bağımsızlığıdır (yukarıda). CSV'deki quine sütunu bu
> nedenle N/A.

## 4. DB boyutu — üç-algoritma tablosu

| Algoritma | DB | Sınıf |
|---|---|---|
| Liebe | 0.72 MB | O(n) |
| **SLA (çift kataloğu)** | **8.0 MB** | **O(n·f)** |
| Triangle | 49.6 MB | O(n·f²) |

SLA tam beklenen yere oturuyor: Liebe'nin pattern-başına-yıldız O(n)'i ile Triangle'ın
üçlü O(n·f²)'i arasında, çift-tabanlı O(n·f).

## 5. Çıktıların yorumu

### Zamanlama (`results/sla_kvector_timing.png`) — en çarpıcı bulgu
| aşama | medyan |
|---|---|
| build_database | ~0.1 s (tek seferlik) |
| **extract** | **0.019 ms** (O(b=4) — Liebe/Quine'ın ~10 ms'ine karşı!) |
| **match** | **1.85 ms** (tüm algoritmaların **en hızlısı**: Liebe/Quine 4 ms, Triangle 152 ms) |

Grafikte `match` süresi **gözlem sayısından bağımsız ~1.8 ms düz** (10→58 yıldız) —
çünkü extract yalnız b=4 sabit pattern kullanır, match O(k) k-vector + 4-yıldız cross-check
+ O(N) yayılımdır. Triangle'ın kübik patlamasının ve Liebe/Quine'ın yıldız-sayısıyla
doğrusal büyümesinin **tam zıttı**. SLA'nın iki kazancı: arama DB-bağımsız (T2) **ve**
feature gözlem-sayısı-bağımsız (O(b)).

### Gürültü grace (`sla_kvector_grace.{csv,png}`)
1.000 / 1.000 / 0.932 / 0.427 @ σ=2/5/10/20″. σ=10″'e kadar güçlü; yüksek gürültüde
çift-açı toleransla taşınca düşüyor (beklenen).

### Spike dayanımı (T4) ve SLA'nın sınırı
- **Tek** parlak spike: id_rate 0.93, wrong_attitude 0.025 (nadir), no_solution 0.05 —
  cross-check 4 yıldızdan 1'i spike olsa diğer 3'ü tutarlı bulup doğru attitude üretiyor;
  "çözüm ya doğru ya çözümsüz".
- **İki+** parlak spike: en-parlak-4 seçimine birden çok spike girince çekirdek <3 → büyük
  oranda `no_solution` (GÜVENLİ, wrong_attitude değil). Bu SLA'nın **bilinen zayıflığı**
  (survey); permütasyon-optimize non-star reddi **Pyramid'in işi** (brief 06). SLA'nın
  başarısızlığı tehlikeli değil — yanlış attitude üretmiyor, çözüm vermiyor.

### native vs +verify (T5)
SLA cross-check geometrik olarak katı; yanlış çekirdek nadir → başarısızlıklar
`no_solution` (güvenli), `wrong_attitude`≈0. Dolayısıyla ortak doğrulayıcının düzeltecek
fazla şeyi yok (Quine'daki bulguya paralel): SLA'da robustluk **pattern+cross-check**ten
gelir. Yayılım adımındaki olası spike eşleşmelerini verify temizler ama wrong_attitude
zaten ~0.

### Sahne
`results/sla_kvector_scene.png`.

## 6. PM'e notlar (tasarım kararları / sapmalar)

1. **Tam-kare yayılım (önemli):** SLA'nın yayınlanmış hâli b=4'lük pattern'i tanır. Bench'in
   id_rate'i (TÜM yıldızlar) ≥0.99 olabilmesi için, çekirdek attitude'dan sonra **standart
   attitude-tabanlı tam-kare tanıma** (direct match) eklendi — gerçek izleyicilerin LIS'i
   böyle tamamlar. Bu olmadan id_rate ≈ 4/N olurdu. Brief'te açıkça yoktu; gerekli tamamlama
   olarak eklendi ve `_propagate`'te dokümante edildi.
2. **cos vs açı:** brief cos önerdi (ucuz); **açı (rad)** seçildi — tolerans tüm aralıkta
   uniform olsun diye; arccos yalnız tek-seferlik build'de. (`build_database`'te dokümante.)
3. **co-visibility yarıçapı = 2·fov_radius** (FOV çapı): gözlemlenebilen TÜM çiftleri kapsar
   (Triangle'daki A-merkezli daraltmanın aksine burada eksiksiz kapsama; çift sayısı yönetilebilir).
4. **SLA spike-kırılganlığı** (en-parlak-4 + parlak spike) bir bulgudur, kusur değil — Pyramid'in
   motivasyonu. Faz 2 ablation'ı bunu net gösteriyor.

## 7. Çalıştırma
```bash
python -m pytest bench/tests/test_sla.py -v
```

## 8. Çıkış koşulu
Brief 05 kabul kriterleri sağlandı. k-vector çekirdeği (`build_kvector`/`kvector_range`)
Pyramid (brief 06) için hazır. Faz 2'nin asıl sıçraması (DB-bağımsız arama) tamam.
