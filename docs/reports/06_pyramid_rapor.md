# Faz 2 Finali / Brief 06 — Pyramid (Mortari 2004) Tamamlama Raporu

**Brief:** `docs/briefs/06_pyramid.md`
**Tarih:** 2026-06-09
**Durum:** ✅ Tamamlandı, 6/6 kabul testi (T1–T6) geçti (tüm paket 49/49).
**Uygulayan:** Claude Code (brief uygulayıcısı)
**Dokunulan dosyalar:** `bench/algorithms/pyramid.py`, `bench/tests/test_pyramid.py`.
Bench core / kontrat / SLA dosyası değişmedi (SLA'dan import edildi).

---

## 1. Ne yapıldı

Pyramid'in tüm katkısı **non-star (spike) reddi**:
- **Akıllı üçlü permütasyonu** (`pyramid_triad_order`): ardışık denemeler aynı yıldızda
  ısrar etmez → kalıcı spike denemeleri zehirleyemez.
- **Üçgen eşleme**: 3 çift açı için 3 `kvector_range` → tam 1 tutarlı (hI,hJ,hK)
  (0/≥2 → reddet, sıradakine geç).
- **Piramit doğrulaması**: 4. yıldız r ile (i,r),(j,r),(k,r) aynı hipR'de tutarlı → kabul.
- **Tam-kare tutarlılık reddi**: onaylı piramit propagate'te ≥`min_solution_stars`
  yıldız açıklamazsa reddedilir (residual sahte piramitleri eler).

build_database + k-vector + yayılım **SLA'dan import** edildi (kopya kod yok).

## 2. Kabul testleri (T1–T6) — 6/6 PASSED

| # | Test | Sonuç |
|---|---|---|
| T1 | akıllı permütasyon (kapsama + ortak-yıldız-yok + deterministik) | ✅ |
| T2 | **işkence: 5 gerçek + 63 spike** | ✅ **wrong_attitude=0, yanlış-kimlik=0, id_rate=1.0** (15 deneme) |
| T3 | Faz 2 spike taraması (5 algoritma) | ✅ Pyramid wrong_att en düşük |
| T4 | ablation (4. yıldız onayı izole) | ✅ onay kapalı → wrong_att artar |
| T5 | gürültüsüz id_rate≥0.99, wrong=0 | ✅ 1.000 |
| T6 | determinizm | ✅ |

## 3. T2 — İşkence testi (survey'in referans işkencesi)

5 gerçek yıldız + **63 spike** (noiseless reals, spike-reddini izole eder),
`results/pyramid_torture.csv`: **15/15 denemede wrong_attitude=0, yanlış-kimlik=0,
id_rate=1.00**. Pyramid 63 sahte yıldız arasından 5 gerçeği kusursuz ayıkladı —
survey'in "robustness to non-star spikes" iddiasının doğrudan doğrulaması.

> Not: T2 σ=0 (noiseless reals) kullanır — testin amacı **spike reddi**, gürültü değil
> (o T3/grace). σ=5″'te 5 yıldızla dar-FOV roll hatası ara sıra 60″ kapısını aşar (kimlik
> DOĞRU, geometrik artefakt); σ=0 ile wrong_attitude saf kimlik-doğruluğunu yansıtır.

## 4. T3 — Faz 2 kapanış figürü (`results/phase2_spike_sweep.{csv,png}`)

Zengin (~22 yıldız) sahne, σ=5″, spike ∈ {0,5,20}, beş algoritmanın **davranış imzaları**:

| algoritma | spike altında imza |
|---|---|
| **Liebe / Quine** | wrong_attitude **0→0.125** (TEHLİKELİ yanlış kimlik), id_rate 0.88→0.59 |
| **SLA** | wrong_attitude 0 ama **no_solution→1.0** (parlak-4 spike'la kirlenir, güvenli çöküş) |
| **Triangle** | wrong_attitude 0, id_rate 1.0 (RANSAC confirm — robust ama 49.6 MB + 152 ms) |
| **Pyramid** | **wrong_attitude 0 + id_rate 1.0 her seviyede** — robust **ve** verimli |

**Faz 2'nin punch-line'ı:** Pyramid, Triangle-seviyesi robustluğu **SLA-seviyesi maliyetle**
(8 MB paylaşımlı DB, ~6 ms match) elde eder. Liebe/Quine spike'ta tehlikeli; SLA güvenli
ama çöker; Pyramid hem güvenli hem çalışır.

## 5. Çıktıların yorumu

### DB paylaşımı doğrulaması (brief gereği)
`db_size_bytes(Pyramid) == db_size_bytes(SLA)` = **8.04 MB, birebir eşit** → Pyramid'in
**ek DB maliyeti: 0** (SLA'nın çift kataloğu + k-vector'ünü aynen kullanır).

### Zamanlama (`pyramid_timing.png`)
- extract medyan **0.048 ms** (tüm çiftler, vektörize).
- match medyan **6.1 ms** (mean 8.3) — lazy partner-dict cache ile (yalnız denenen
  çiftler hesaplanır; zengin alanda başarı ilk birkaç üçlüde).

### Gürültü grace (`pyramid_grace.{csv,png}`) — sürpriz: en robust
1.000 / 1.000 / 0.981 / **0.909** @ σ=2/5/10/20″. σ=20″'te Pyramid **0.909**, oysa
SLA 0.427, Liebe 0.404. Pyramid yalnız spike'a değil **gürültüye de en dayanıklı** —
tüm çiftleri kullanması (en-parlak-4 kısıtı yok) + tam-kare yayılım sayesinde.

### Üçlü deneme istatistiği ("permütasyon zehirden uzaklaşır" ölçümü)
Zengin alanda denenen üçlü sayısı (medyan): spike 0→**1**, 5→**2**, 20→**7**, 50→**53**.
Spike arttıkça az artıyor — normal yıldız alanında (gerçekler çoğunlukta) akıllı sıra
gerçek üçlüyü hızla buluyor. (İşkencedeki ~6000, yalnız 5 gerçek/68 aşırı-seyreklik
yüzünden; oradaki "zehirden uzaklaşma" tek spike'a takılmamayı sağlar.)

### T4 ablation — 4. yıldız onayının izole katkısı
`min_solution_stars=2` (tam-kare net gevşetilip 4. yıldız onayı izole edilir),
σ=8″+10 spike:
- native (onay açık): wrong_attitude **0.000**
- piramit-kapalı (onay yok): wrong_attitude **~0.075** ← onayın katkısının kanıtı
- +core_verify: 0.000

**Nüans (Quine bulgusunun devamı):** Üretim ayarında (`min_solution_stars=4`) tam-kare
tutarlılık reddi tek başına da sahteleri eler; 4. yıldız onayının katkısı ancak bu net
gevşetilince izole görünür. Pyramid'in robustluğu **iki katmandan** gelir: 4. yıldız
onayı + tam-kare tutarlılık. İkisi de gevşeyince yanlış-attitude belirir.

### Sahne
`results/pyramid_scene.png`.

## 6. Faz 2 özet tablosu (beş algoritma)

| algoritma | DB | match medyan | spike davranışı | search sınıfı |
|---|---|---|---|---|
| Liebe | 0.72 MB | ~4 ms | tehlikeli (wrong↑) | O(n) lineer |
| Quine | 0.72 MB | ~4 ms | =Liebe | O(lg n) ağaç |
| Triangle | 49.6 MB | ~152 ms | robust, pahalı | O(n·f²) DB |
| SLA | 8.0 MB | ~1.8 ms | güvenli-kırılgan | O(k) DB-bağımsız |
| **Pyramid** | **8.0 MB** | ~6 ms | **robust + verimli** | O(k) + spike reddi |

## 7. PM'e notlar (tasarım kararları / sapmalar)
1. **Tam-kare yayılım** SLA ile paylaşıldı (aynı dipnot: yayınlanmış Pyramid pattern'i
   tanır; bench id_rate'i için attitude-tabanlı tam-kare tanıma eklendi).
2. **`min_solution_stars` (tam-kare tutarlılık reddi):** tek-shot 4. yıldız onayı nadiren
   (50'de 1) sahte piramidi geçiriyordu (4 spike tesadüfen tutarlı+onaylı). Onaylı
   piramidin propagate'te ≥4 yıldız açıklamasını şart koşan tam-kare tutarlılık katmanı
   eklendi — bu, gerçek izleyicilerin yaptığı doğrulamadır ve wrong_attitude'u %2→0
   indirdi. Brief'te açık değildi; gerekli sağlamlaştırma olarak eklendi, raporlandı.
3. **Lazy partner-dict cache:** C(f,2) çiftin tümünü önceden hesaplamak yerine talep
   üzerine (cache'li) — zengin alanda 20-100× hızlandırdı (512→6 ms).

## 8. Çalıştırma
```bash
python -m pytest bench/tests/test_pyramid.py -v
```

## 9. Çıkış koşulu
Brief 06 kabul kriterleri sağlandı. **Faz 2 tamamlandı** (Quine, SLA, Pyramid). Pyramid
KAT-02'nin uçuş-sınıfı güvenilirlik referansı: spike altında wrong_attitude=0, id_rate=1.0,
O(k) DB-bağımsız arama, ek DB maliyeti 0.
