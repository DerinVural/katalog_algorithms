# Brief 01 — Bench Core (Faz 0)

**Hedef dosyalar:** `bench/core/*.py`, `bench/algorithms/oracle.py`, `bench/runner.py`, `bench/tests/*`
**Bağımlılık:** yok (ilk faz)
**Çıkış koşulu:** PROJECT_PLAN.md §6 Faz 0 kabul kriterleri geçer.

> Bu brief, sonraki tüm algoritma brief'lerinin de şablonudur: *Amaç → Arayüz kontratı → Yapılacaklar (dosya dosya) → Matematik → Kabul testleri → Yapma.*

---

## Amaç
Tüm algoritmaların üzerine takılacağı ortak boru hattını kur. Henüz **hiçbir gerçek Star-ID algoritması yazma** — sadece ortak altyapı + harness'ı doğrulayan sahte "oracle" algoritma.

## Stack
Python 3.11+, numpy, scipy, astropy (katalog/koordinat), matplotlib. k-vector gibi sıcak döngüler v1'de saf numpy; gerekirse sonra Cython.

## Sensör sabitleri (`bench/core/sensor.py`)
```python
DETECTOR = "CMV4000"
NPIX = 2048
PIXEL_PITCH_UM = 5.5
FOV_H_DEG = 14.7
FOCAL_LENGTH_MM = 43.7      # türetilen, doğrula
PIXEL_SCALE_ARCSEC = 25.8   # türetilen
MAG_LIMIT = 6.0
```
`sensor.py` bu sabitlerden focal length ve pixel scale'i **hesaplayıp** sabit değerlerle assert ile karşılaştırsın (tutarlılık kontrolü).

## Yapılacaklar (dosya dosya)

### `core/interfaces.py`
PROJECT_PLAN.md §3'teki dataclass'ları ve `StarIDAlgorithm` Protocol'ünü birebir uygula.

### `core/catalog.py`  [KAT-01]
- Hipparcos kataloğunu yükle (astropy/Vizier veya yerel dosya), Mv < 6 filtrele.
- Her yıldız için J2000 birim vektörü (RA/Dec → unit vector) hesapla.
- `Catalog` döndür; `by_id()`, ve hızlı komşu sorgusu için bir KD-tree (3D unit vektör) yardımcı.
- Proper motion v1'de **kapalı**.

### `core/pinhole.py`
- `focal_to_body(x, y) -> u_body`: Liebe denk. (1), pinhole model.
- `body_to_focal(u_body) -> (x, y)`: ters dönüşüm (sahne render için).
- Yuvarlanma testi: focal → body → focal, < 1e-9 px hata.

### `core/scene.py`  (sahne simülatörü)
Girdi: `catalog`, `SENSOR`, `q_true`, `noise_cfg`. Çıktı: `(list[BodyVector], SceneTruth)`.
- `q_true` ile katalog yıldızlarını body çerçevesine döndür.
- FOV içinde kalanları seç (dairesel FOV yarıçapı = FOV_H/2; köşe etkilerini v1'de basit tut).
- Her yıldıza enjekte et (noise_cfg ile aç/kapa, parametrik):
  - centroid pozisyon gürültüsü (Gaussian, arcsec),
  - magnitude gürültüsü,
  - false-star / spike (rastgele konumda sahte gözlem),
  - eksik yıldız (görülebilir yıldızı rastgele düşür).
- `SceneTruth.true_matches` sadece gerçek yıldızlar için doldurulur (spike'lar truth'ta yok).

### `core/quest.py`
- QUEST (Shuster & Oh 1981) veya Davenport q-method; eşleşen body↔inertial vektör çiftlerinden quaternion.
- Gürültüsüz eşleşmede attitude'u < 1 arcsec geri kazanmalı.

### `core/metrics.py`
- `evaluate(q_est, cands, truth)` → id_rate, false_id_flag, attitude_error_arcsec (cross-boresight ve roll ayrı).
- timing yardımcısı `timed(fn, *args)` → (sonuç, süre).
- `db_size_bytes(obj)` → DB bellek ölçümü.

### `algorithms/oracle.py`
- `build_database`: katalogu olduğu gibi sar.
- `extract_features`: gözlemleri aynen döndür.
- `match`: **truth'a bakarak** doğru `CandidateMatch` listesini döndürür (spike'ları atar).
- Amaç: harness'ı gerçek algoritmadan önce uçtan uca doğrulamak.

### `runner.py`
- Tek attitude + Monte Carlo döngüsü (PROJECT_PLAN.md §3 özeti).
- Çoklu attitude → sky coverage için full-sky grid.
- Sonuçları `results/` altına CSV + plot.

## Kabul testleri (`tests/`)
1. `test_catalog`: Mv<6'da makul N yıldız (~birkaç bin); tüm vektörler birim.
2. `test_pinhole`: focal→body→focal roundtrip < 1e-9 px.
3. `test_scene_angles`: gürültüsüz sahnede gözlenen yıldız çiftlerinin ara açıları, karşılık gelen katalog yıldızlarının açılarıyla < 1 arcsec içinde eşleşir.
4. `test_quest`: gürültüsüz oracle eşleşmesinden geri kazanılan attitude, `q_true`'ya < 1 arcsec.
5. `test_oracle_end_to_end`: oracle algo `runner` üzerinden tam döngüden geçer, id_rate = %100, false_id = 0.
6. `test_metrics`: elle kurulmuş bir vakada id_rate / false_id doğru hesaplanır.

## Yapma
- Hiçbir gerçek Star-ID algoritması yazma (Liebe dahil) — o Faz 1.
- Arayüz kontratını değiştirme; eksik görürsen PM'e (bu sohbet) bildir, brief güncellensin.
- Spike'ları truth'a koyma.
