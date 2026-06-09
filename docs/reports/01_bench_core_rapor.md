# Faz 0 — Bench Core Tamamlama Raporu

**Brief:** `docs/briefs/01_bench_core.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, kabul kriterleri geçti, push edildi.
**Uygulayan:** Claude Code (brief uygulayıcısı)

---

## 1. Amaç

Tüm Star-ID algoritmalarının üzerine takılacağı ortak boru hattını (`bench/core/`)
kurmak ve harness'ı, gerçek bir algoritmadan **önce**, ground-truth döndüren sahte
"oracle" algoritmasıyla uçtan uca doğrulamak. Bu fazda hiçbir gerçek Star-ID
algoritması yazılmadı (brief §Yapma).

## 2. Teslim edilen dosyalar

Brief'teki dosya-dosya liste birebir uygulandı:

| Dosya | İçerik |
|---|---|
| `bench/core/interfaces.py` | Plugin kontratı (PROJECT_PLAN §3) + `Catalog` yardımcıları (by_id, KD-tree) |
| `bench/core/sensor.py` | CMV4000 profili; focal length & pixel scale türetilip sabitlerle assert |
| `bench/core/catalog.py` | Hipparcos (Vizier I/239/hip_main) ingest, Mv<6, J2000→birim vektör, `.npz` cache [KAT-01] |
| `bench/core/pinhole.py` | Liebe denk. (1) pinhole modeli; focal↔body, birebir roundtrip |
| `bench/core/scene.py` | Sahne simülatörü + parametrik gürültü (centroid, magnitude, spike, eksik yıldız) |
| `bench/core/quest.py` | Davenport q-method attitude çözücü + quaternion yardımcıları |
| `bench/core/metrics.py` | id-rate, false-id, attitude hatası (cross-boresight & roll), timing, DB bellek boyutu |
| `bench/algorithms/oracle.py` | Ground-truth döndüren sahte algoritma (bench self-test) |
| `bench/runner.py` | Monte Carlo + full-sky koşucu; CSV + plot çıktısı |
| `bench/tests/*` | 6 kabul testi grubu (16 test) |
| `.gitignore`, `requirements.txt` | Proje yapılandırması |

## 3. Kabul testleri sonucu (brief §Kabul testleri)

Tüm test paketi: **16 test / 16 geçti** (`python -m pytest bench/tests -q`).

| # | Test | Kriter | Sonuç |
|---|---|---|---|
| 1 | `test_catalog` | Mv<6'da makul N yıldız, tüm vektörler birim | ✅ 4992 yıldız, ‖v‖=1 |
| 2 | `test_pinhole` | focal→body→focal roundtrip < 1e-9 px | ✅ |
| 3 | `test_scene_angles` | gürültüsüz gözlem çift açıları katalogla < 1 arcsec | ✅ |
| 4 | `test_quest` | gürültüsüz oracle eşleşmesinden attitude < 1 arcsec | ✅ |
| 5 | `test_oracle_end_to_end` | oracle runner'dan geçer, id_rate %100, false_id 0 | ✅ |
| 6 | `test_metrics` | elle kurulmuş vakada id_rate / false_id doğru | ✅ |

### Uçtan uca demo (`python -m bench.runner`)

- Katalog: **4992 yıldız** (Hipparcos, Mv<6).
- Gürültülü Monte Carlo (200 trial): ortalama id_rate = **1.000**, false_id = 2/200
  (10 arcsec centroid gürültüsü + spike + %10 eksik yıldızda QUEST hatası ara sıra
  60 arcsec eşiğini aşıyor — gerçekçi gürültü davranışı, kabul kriteri değil).
- Full-sky coverage (gürültüsüz oracle): **%100**.
- Çıktılar: `bench/results/` (CSV + PNG; gitignore'lu).

## 4. Tasarım konvansiyonları

- Quaternion **scalar-last** `[x, y, z, w]` (scipy uyumlu). Attitude inertial→body:
  `u_body = R(q) @ u_inertial`.
- Pinhole boresight = +z gövde ekseni; piksel koordinatları görüntü merkezine göre.
- Katalog Vizier'den çekilip `bench/data/*.npz` olarak cache'lenir (gitignore'lu;
  yalnız ilk yükleme ağ gerektirir). Proper motion v1'de kapalı.
- Sahne gürültüsü tamamen parametrik (`NoiseConfig`); hepsi 0 = gürültüsüz sahne.
  Spike'lar truth'a konulmaz.

## 5. PM'e not — arayüz sapması (brief §Yapma gereği)

`StarIDAlgorithm.match(features, db)` imzasında truth kanalı yok; ancak oracle'ın
görevi truth'a bakarak doğru eşleşmeleri döndürmek. Oracle bunu **Protocol-dışı**
`set_truth()` metoduyla alır; `runner` bu metodu yalnızca oracle'da (`hasattr`)
çağırır. **`StarIDAlgorithm` kontratı değiştirilmedi** — yalnız oracle'a ek bir
metod eklendi. Sapma `bench/algorithms/oracle.py` başında dokümante edildi. Brief
güncellemesi gerekip gerekmediği PM kararıdır.

## 6. Çalıştırma

```bash
pip install -r requirements.txt
python -m pytest bench/tests -q        # kabul testleri
python -m bench.runner                 # uçtan uca demo (CSV + plot)
```

## 7. Faz 0 çıkış koşulu

PROJECT_PLAN §6 Faz 0 kabul kriterleri **sağlandı**. Bench, gerçek algoritma
brief'lerini almaya hazır.
