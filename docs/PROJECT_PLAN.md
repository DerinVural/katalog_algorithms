# Star-ID Algoritma Karşılaştırma Bench'i — Proje Planı

**Repo:** `katalog_algorithms`
**Kaynak doküman:** Spratling & Mortari (2009), *A Survey on Star Identification Algorithms*
**Amaç:** Survey'deki yıldız eşleştirme (Star-ID) metotlarını **tek bir adil test bench'i** üzerinde uygulamak ve performanslarını ölçmek.
**KAT bağlantısı:** Bu bench'in `catalog` modülü KAT-01'in, `algorithms` + `match` katmanı KAT-02'nin referans implementasyonudur.

---

## 0. Temel mimari ilke (en kritik karar)

Her algoritmayı baştan sona ayrı program olarak **yazmıyoruz**. Survey'in kendi değerlendirme ekseni (feature extraction / database / database search) bize şunu söylüyor: bir algoritmayı diğerinden ayıran tek şey bu üç parça. Geri kalan boru hattı ortak.

Bu yüzden:

- **Ortak boru hattı bir kez** yazılır (`bench/core/`).
- Her algoritma, sadece kendi farklı olduğu üç parçayı dolduran bir **eklenti (plugin)** olur (`bench/algorithms/<isim>.py`, tipik 50–150 satır).
- Bench herkese **birebir aynı** katalog, sahne, gürültü, QUEST ve metrik koduyla davranır → çıktılar kıyaslanabilir.

> **Adil-karşılaştırma kuralı:** 2009 survey'ini genişleten 2020 takip çalışması (Rijlaarsdam et al.), bu literatürdeki karşılaştırmaların standart koşul olmadığında tutarsız sonuç verdiğini gösterir. Bu yüzden katalog, sahne simülasyonu, gürültü modeli ve donanım profili tüm algoritmalar için **sabit** tutulur. Tek değişken algoritmanın kendisidir.

---

## 1. Sensör profili (sabit)

| Parametre | Değer | Not |
|---|---|---|
| Dedektör | CMV4000 | 2048 × 2048 |
| Piksel pitch | 5.5 µm | |
| Yatay FOV | 14.7° | |
| Odak uzaklığı (türetilen) | ≈ 43.7 mm | f = (w/2) / tan(FOV/2), w = 2048·5.5µm = 11.264 mm |
| Piksel ölçeği (türetilen) | ≈ 25.8 arcsec/px | 14.7°·3600 / 2048 |
| Köşegen FOV (türetilen) | ≈ 20.6° | |
| Magnitude limiti | Mv < 6 | |
| FOV başına ort. yıldız (kestirim) | ~15–20 | galaktik enleme bağlı; kesin dağılımı simülatör üretir |

v1'de proper-motion epoch propagation **kapalı** (J2000 katalog konumları doğrudan kullanılır). v2'de açılır.

---

## 2. Repo dizin yapısı (öneri — mevcut arşivi bozmaz)

```
katalog_algorithms/
├── literature/              # MEVCUT arşiv — DOKUNULMUYOR (paperlar, KAT01_references.xlsx, ...)
├── bench/
│   ├── core/                # ortak boru hattı (KAT-01 + KAT-02 referans impl.)
│   │   ├── interfaces.py    # StarIDAlgorithm protokolü + veri tipleri
│   │   ├── sensor.py        # CMV4000 profil sabitleri (yukarıdaki tablo)
│   │   ├── catalog.py       # Hipparcos ingest, mag-limit  [KAT-01]
│   │   ├── pinhole.py       # focal-plane <-> body unit vektör (Liebe denk. 1)
│   │   ├── scene.py         # sahne simülatörü + gürültü modeli
│   │   ├── quest.py         # QUEST attitude çözücü
│   │   └── metrics.py       # id-rate, false-id, timing, memory, coverage
│   ├── algorithms/          # HER METOD = BİR EKLENTİ
│   │   ├── oracle.py        # ground-truth döndüren sahte algo (bench doğrulaması)
│   │   ├── liebe.py
│   │   ├── triangle_planar.py
│   │   ├── quine.py
│   │   ├── sla_kvector.py
│   │   ├── pyramid.py
│   │   └── ...
│   ├── runner.py            # bench koşucusu + Monte Carlo döngüsü
│   ├── tests/
│   └── results/             # plot + csv (büyük dosyalar .gitignore)
├── docs/
│   ├── PROJECT_PLAN.md      # bu dosya
│   └── briefs/              # Claude Code iş emirleri
│       └── 01_bench_core.md
└── README.md
```

---

## 3. Plugin arayüz kontratı (tüm algoritmalar bunu doldurur)

```python
# bench/core/interfaces.py
from typing import Protocol, Sequence, Any
from dataclasses import dataclass
import numpy as np

@dataclass
class CatalogStar:
    hip_id: int
    u_inertial: np.ndarray   # birim vektör (3,), J2000 body-of-reference
    mag: float

@dataclass
class Catalog:
    stars: list[CatalogStar]
    # yardımcılar: by_id(), kdtree, vs. core içinde sağlanır

@dataclass
class BodyVector:
    obs_id: int              # bu gözlemin yerel indeksi
    u_body: np.ndarray       # birim vektör (3,), sensör gövde çerçevesi
    mag: float               # instrumental magnitude (gürültülü)
    centroid_px: np.ndarray  # (2,) opsiyonel, S-curve/timing için

@dataclass
class CandidateMatch:
    obs_id: int              # gözlenen yıldız
    hip_id: int              # eşleştiği katalog yıldızı
    confidence: float = 1.0

@dataclass
class SceneTruth:
    q_true: np.ndarray       # (4,) doğru attitude quaternion
    true_matches: dict[int, int]  # obs_id -> hip_id

class StarIDAlgorithm(Protocol):
    name: str

    def build_database(self, catalog: Catalog) -> Any:
        """Algoritmaya özel DB/index üret (k-vector, binary tree, grid, ...).
        Bellek boyutu burada ölçülür."""
        ...

    def extract_features(self, observed: Sequence[BodyVector]) -> Any:
        """Gözlenen yıldızlardan algoritmanın feature'larını çıkar.
        Survey Tablo 1'deki 'feature extraction' süresi burada ölçülür."""
        ...

    def match(self, features: Any, db: Any) -> list[CandidateMatch]:
        """DB araması + error checking. Survey'deki 'database search' süresi
        burada ölçülür."""
        ...

    # Opsiyonel — sadece recursive modu olan algoritmalar
    def identify_recursive(
        self, observed: Sequence[BodyVector], db: Any, q_prior: np.ndarray
    ) -> list[CandidateMatch]:
        ...
```

`build_database` / `extract_features` / `match` ayrı tutuluyor ki survey Tablo 1'deki üç ekseni (feature / db size / search) **ayrı ayrı** ölçebilelim.

Bench koşucusu herkese aynı şekilde davranır:

```python
# bench/runner.py (özet)
db = algo.build_database(catalog)                  # 1 kez, bellek ölçülür
for trial in monte_carlo_trials:                   # ORTAK
    scene, truth = simulate_scene(catalog, SENSOR, attitude, noise)  # ORTAK
    feats  = timed(algo.extract_features, scene.body_vectors)        # algo-özel, süre
    cands  = timed(algo.match, feats, db)                            # algo-özel, süre
    q_est  = quest(cands, catalog, scene)          # ORTAK
    record(evaluate(q_est, cands, truth))          # ORTAK
```

---

## 4. Metot envanteri (survey'den)

Her metot 3 eksene göre haritalandı. "Anahtar nokta" = implementasyonda dikkat edilecek asıl şey.

### Tier A — Çekirdek (KAT-02'nin kalbi, önce bunlar)

| Metot | Yıl | Feature | DB / Search | Anahtar nokta |
|---|---|---|---|---|
| Liebe | 1992 | merkez yıldız + 2 en yakın; 2 ara açı + 1 iç açı | O(n) / lineer | en yakın 2 yıldız seçimi gürültüde belirsizleşir; magnitude eşiğine yakın yıldız kaçma durumu |
| Quine | 1996 | Liebe feature'ı | binary tree / O(lg n) | DB aramasını ilk ciddi hızlandıran; ağaç inşası |
| Mortari SLA | 1997 | herhangi yıldız çifti, ara açı | **k-vector** / DB boyutundan bağımsız | k-vector inşası; çoklu liste cross-check O(b·k²) |
| Pyramid | 2004 | SLA + optimal permütasyon | k-vector | **non-star (spike) reddi** asıl değer; 5 gerçek + 63 sahte testini geç |
| Padgett Grid | 1997 | en yakın yıldıza göre roll-hizalı grid maskesi | O(n) / lineer | roll çözümü için rotasyon; büyük hücre → spike'a robust |
| Samaan non-dim | 2003 | üçgen **iç açıları** (kalibrasyona robust) | k-vector | sıcaklık/kalibrasyon kaymasına 1. derece duyarsız; ≥5 yıldız cross-check |
| Rousseau | 2005 | en yakın 2 yıldız, tek iç açının sinüsü | binary tree benzeri | APS hatasına robustluk iddiası; her yıldız için tek DB girdisi |

### Tier B — Tarihsel yay / baseline (neden modernler kazandı'yı gösterir)

| Metot | Yıl | Not |
|---|---|---|
| Junkins | 1981 | triplet + FOV-boyutu sub-catalog; O(f³) search, O(nf²) DB. Klasik baseline. |
| Scholl | 1995 | parlaklığa göre sıralı ara açılar; permütasyon eler ama DB hâlâ O(nf²) |
| Baldini | 1993 | çok adımlı, 5 yıldız; ardışık liste daraltma |
| Ketchum | 1995 | parlaklık tabanlı ardışık filtre; katalogun ~%43'ünü tarayabilir |
| Guangjun | 2007 | Liebe benzeri radial+cyclic feature, lineer search |
| Kolomenkin (geometric voting) | 2008 | SLA + oylama; f² < k rejiminde teorik kazanç (CubeSat'ta tartışmalı) |

### Tier C — Opsiyonel / dikkatli (eksik tanımlı ya da CubeSat'a ağır) — STRETCH

| Metot | Yıl | Not |
|---|---|---|
| Hong (NN + fuzzy) | 2000 | massively parallel; >¼ milyon çarpım. CubeSat güç profiline uymaz; ilginç referans. |
| Groth | 1986 | yüksek polinom; sadece analitik karşılaştırma yeterli olabilir |
| Anderson | 1991 | permütasyon matrisi + array processor |
| Sasaki / Van Bezooijen | 1987/1989 | survey search prosedürünü tam vermiyor / slew gerektiriyor → ya dokümante varsayımlı rekonstrüksiyon ya sadece analitik |

### Recursive mod (ayrı senaryo — a-priori attitude varken)

| Metot | Not |
|---|---|
| Direct match | en basit; tahmini konuma yakınlıkla eşleştir |
| SP-Search | k-vector'ü x,y,z aralıkları için 3 kez kullanır; cross-comparison O(k³) |
| SNA | her yıldızın önceden hesaplanmış 6 en yakın komşusu tablosu; O(b) |

---

## 5. Değerlendirme metrikleri (bench ne ölçer)

1. **Identification rate** — doğru eşlenen yıldız oranı.
2. **False-ID rate** — yanlış attitude üreten eşleşme oranı. **En kritik metrik** (yanlış attitude, "çözüm yok"tan kötüdür).
3. **Robustness eğrileri** — şuna karşı id-rate / false-id:
   - centroid pozisyon gürültüsü (arcsec / piksel kesri),
   - magnitude gürültüsü,
   - false-star / spike sayısı,
   - eksik (görülemeyen) yıldız sayısı.
4. **Ölçülen koşu süresi** — feature extraction ve database search **ayrı ayrı**; survey Tablo 1'in ampirik doğrulaması.
5. **DB / katalog bellek boyutu** — `build_database` çıktısının byte cinsinden boyutu.
6. **Sky coverage** — full-sky Monte Carlo; attitude çözülebilen gökyüzü yüzdesi.
7. **(Doğrulama çıktısı)** Ölçülen ampirik ölçeklemenin Tablo 1'deki asimptotik beklentiyle uyumu.

Tüm metrikler `results/` altına CSV + plot olarak yazılır.

---

## 6. Faz planı + kabul kriterleri

| Faz | İçerik | Kabul kriteri |
|---|---|---|
| **0 — Bench** | `core/` tümü + `oracle.py` + `runner.py` | Katalog Mv<6'da N yıldız yükler; bilinen attitude için sahne üretip pinhole geri-dönüşü açıları katalogla tolerans içinde eşler; QUEST gürültüsüz sentetik eşleşmeden attitude'u <1 arcsec geri kazanır; oracle algo bench'ten uçtan uca geçer (harness gerçek algoritmadan **önce** doğrulanır) |
| **1 — İlk algoritmalar** | `liebe.py` + `triangle_planar.py` | Her ikisi de gürültüsüz sahnede ≥%99 id-rate; gürültü taramasında anlamlı eğri üretir |
| **2 — Hızlı search** | `quine.py`, `sla_kvector.py`, `pyramid.py` | Pyramid: 5 gerçek + 63 spike testini geçer; SLA/Quine ölçülen search süresi Tablo 1 trendiyle uyumlu |
| **3 — Pattern & non-dim** | `padgett_grid.py`, `samaan_nondim.py`, `rousseau.py`, `guangjun.py` | non-dim: kalibrasyon kayması enjekte edildiğinde Liebe'den daha robust |
| **4 — Recursive** | direct match, SP-Search, SNA | a-priori attitude'la LIS'ten belirgin hızlı |
| **5 — Baseline & stretch** | Tier B + (opsiyonel) Tier C | tarihsel karşılaştırma tablosu tamam |
| **6 — Rapor** | cross-comparison | tüm metotlar için tek tablo + plot seti; Tablo 1 doğrulaması |

---

## 7. İş bölümü

- **PM (Claude, bu sohbet):** kapsam, faz sıralaması, kabul kriterleri, her metot için Claude Code iş emri (matematik + referans + arayüz kontratı + test vakaları), çıktıların paper'a göre doğruluk review'u, scope/adil-karşılaştırma disiplini.
- **Claude Code:** kodlama, test koşumu, plot üretimi — her brief tek bir izole dosyayı hedefler.
- **Sen:** üst düzey kararlar, domain hakemliği, KAT-01/02 entegrasyonu.

## 8. Claude Code ile çalışma akışı

Her iş emri `docs/briefs/NN_<isim>.md` olarak repoda durur. Claude Code'a verilen prompt basit: *"`docs/briefs/02_liebe.md`'yi oku, `bench/core/interfaces.py` kontratını dolduran `bench/algorithms/liebe.py`'yi yaz, `bench/tests/test_liebe.py` testlerini geçir."* Brief, algoritmanın doğru implement edildiğini bağımsız doğrulanabilir kılan kabul testlerini içerir.

**Sıra önemli:** Faz 0 (bench) onaylanmadan hiçbir algoritma brief'i başlatılmaz — algoritmalar bench'in arayüzüne bağımlı.
