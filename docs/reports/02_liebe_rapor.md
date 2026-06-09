# Faz 1 / Brief 02 — Liebe (1992) Tamamlama Raporu

**Brief:** `docs/briefs/02_liebe.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, 6/6 kabul testi geçti.
**Uygulayan:** Claude Code (brief uygulayıcısı)
**Dokunulan dosyalar:** `bench/algorithms/liebe.py`, `bench/tests/test_liebe.py` (bench core / kontrat değiştirilmedi).

---

## 1. Ne yapıldı

Liebe'nin "merkez yıldız + 2 en yakın komşu" pattern'i `StarIDAlgorithm`
kontratını dolduran tek eklenti olarak uygulandı.

- **Feature** `(d1, d2, theta)`: en yakın 2 komşunun açısal uzaklıkları
  (`d1 ≤ d2`, rad) + iki komşunun merkezdeki iç açısı (teğet düzlemde
  hesaplanan gerçek vertex açısı).
- **`build_database`** → O(n): KD-tree ile en yakın komşular, `d1`'e göre sıralı
  numpy dizilerinde saklanır (lineer pencere daraltma için).
- **`extract_features`** → gözlenen yıldızların aynı pattern'i.
- **`match`** → lineer (sıralı `d1` üzerinde ikili arama penceresi) + çoğunluk
  oylaması; tutarlı, birebir eşleşme kümesi seçilir.
- d1≈d2 belirsizliği (her iki sıralama denenir) ve eşik civarı kaçan yıldız
  (oylama çoğunluğa dayanır) brief'teki gibi ele alındı.
- Magnitude **kullanılmadı** (survey: "neglecting the stellar magnitudes").

## 2. Kabul testleri (brief §Kabul testleri) — 6/6 PASSED

| # | Test | Kriter | Sonuç |
|---|---|---|---|
| 1 | `test_liebe_noiseless` | gürültüsüz id_rate ≥ 0.99, false_id yok, attitude < birkaç ″ | ✅ id_rate **1.000** |
| 2 | `test_liebe_db_on_order` | DB O(n), tekil merkez ~ katalog | ✅ 14976 kayıt / 4992 merkez |
| 3 | `test_liebe_d1_approx_d2` | iki komşu eşit uzaklıkta -> doğru eşleşme | ✅ |
| 4 | `test_liebe_noise_grace` | id_rate monoton düşer, σ=5″'te ≥ %90 | ✅ σ=5″ **0.992** |
| 5 | `test_liebe_spike_tolerance` | 3 spike -> false_id nadir, katastrofik değil | ✅ false_id **1/30** |
| 6 | `test_liebe_deterministic` | sabit seed -> aynı sonuç | ✅ |

Tüm bench paketi: **22/22 test** geçiyor (16 Faz 0 + 6 Liebe).

## 3. Çıktıların yorumu

### Gürültü grace eğrisi (`results/liebe_grace.csv` + `.png`)

| centroid σ [″] | id_rate |
|---|---|
| 0 | 1.000 |
| 2 | 1.000 |
| 5 | 0.992 |
| 10 | 0.842 |
| 20 | 0.404 |

**Okuma:** Eğri ~5″'e kadar düz, sonra hızla çöküyor. Bu beklenen: feature
toleransı `tol_d=15″` (≈ 3× makul centroid hatası). Centroid gürültüsü bu
toleransa yaklaşınca (σ≈10–20″) pattern'ler yanlış DB kayıtlarıyla örtüşmeye
başlıyor, eşleşmeler dağılıyor. σ=25.8″ = 1 piksel olduğundan σ=20″ neredeyse
1-piksel hatadır — tek bir yıldız izleyici için zaten aşırı gürültü. Sensör
ölçeğiyle (25.8″/px) tutarlı.

### DB boyutu (`db_size_bytes`)

- **14976 kayıt ≈ 702 KB** (yıldız başına C(3,2)=3 kayıt). Asimptotik **O(n)**:
  merkez sayısı = 4992 = katalog. Survey Tablo 1'in Liebe için DB=O(n)
  beklentisiyle uyumlu. Bu değer Faz 2'de k-vector (SLA) ve Faz 1'in triangle
  yöntemiyle kıyaslanacak referans.

### Attitude hatası ve false-ID

- Gürültüsüz/düşük gürültüde false_id = 0; attitude hatası birkaç arcsec.
- σ arttıkça önce id_rate düşer (eşleşme bulunamaz → çözümsüzlük), yanlış
  attitude (false_id) ancak yüksek gürültüde (σ≥20″) belirginleşir. Bu, Liebe'nin
  "çözümsüzlük > yanlış çözüm" eğiliminde olduğunu gösterir — istenen güvenli
  başarısızlık davranışı.
- Spike (3 sahte yıldız) ile false_id 1/30 (~%3). **Liebe Pyramid kadar robust
  değildir** (brief'in beklediği gibi); spike reddi olmadığından nadiren bir
  spike geçerli pattern'e benzeyip yanlış oy üretebiliyor. Bu, Faz 2'de
  Pyramid'in non-star reddiyle kıyaslanacak başlangıç çizgisidir.

### Timing
- Feature çıkarma ve match süreleri trial başına ~10 µs mertebesinde (CSV'de
  `t_extract_s`, `t_match_s`). Lineer search beklendiği gibi; Faz 2'de k-vector
  ile hız kıyası yapılacak (survey Tablo 1 doğrulaması).

## 4. PM'e not — uygulama kararı (brief'ten sapma)

Brief "yıldız başına **bir** kayıt (en yakın 2)" diyor. Saf bu şema, **FOV-kenarı
etkisi** yüzünden gürültüsüz sahnede yalnız **~0.945** id_rate verdi: bir yıldızın
katalogdaki en yakın komşuları bu bakıştaki dairesel FOV'un dışında kalabiliyor,
böylece görüntüdeki en yakın-2 komşusu farklı yıldızlar oluyor ve merkez feature
hiçbir DB kaydıyla örtüşmüyor (teşhiste 3/55 yıldız bu nedenle kaçtı, biri sıfır
örtüşmeyle).

Bunu brief'in **≥0.99** kabul kriterini (çıkış koşulu) sağlayacak şekilde çözmek
için yıldız başına **en yakın K=3 komşunun ikili kombinasyonları** (C(3,2)=3
kayıt) saklandı. Bu hâlâ "merkez + 2 komşu" pattern'idir ve DB **hâlâ O(n)**
(sabit çarpan). `neighbors_k` config'te; K=2'ye düşürülürse brief'in literal
"tek kayıt" hâline döner (o zaman id_rate≈0.945). Kontrat/bench core
değiştirilmedi; yalnız algoritma-içi indeksleme kararı. PM literal "tek kayıt"
isterse `neighbors_k=2` yapılır ve kabul eşiği gözden geçirilmelidir.

## 5. Çalıştırma

```bash
python -m pytest bench/tests/test_liebe.py -v
```
Grace eğrisi çıktıları: `bench/results/liebe_grace.{csv,png}` (gitignore'lu).

## 6. Çıkış koşulu

Brief 02 kabul kriterleri **sağlandı**. Faz 1'in ikinci yarısı (triangle_planar,
brief 03) ile kıyas için DB boyutu ve grace eğrisi referans olarak kaydedildi.
