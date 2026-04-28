# Star Identification Literature — Learning Path

> **Repo:** https://github.com/DerinVural/katalog_algorithms
> **Amaç:** Yıldız tanıma (star identification) algoritmalarını sıfırdan öğrenmek için yapılandırılmış okuma sırası.
> **Kullanım:** Bu dosyayı Claude Code'a verip düzenleyebilir, durum (status) ve not (notes) alanlarını güncelleyebilir, kendi yol haritana göre özelleştirebilirsin.

---

## Açıklama: Alanlar Ne Anlama Geliyor?

Her paper aşağıdaki alanlarla tanımlanır:

- **id**: Kısa, benzersiz tanımlayıcı (kod içinde referans için)
- **filename**: Repodaki dosya adı
- **title**: Tam başlık
- **authors / year / venue**: Bibliyografik bilgi
- **reading_order**: 1'den başlayan okuma sırası
- **stage**: Hangi aşamaya ait (Foundations, Catalogs, vb.)
- **difficulty**: `beginner` / `intermediate` / `advanced` / `expert`
- **estimated_hours**: Tahmini okuma süresi
- **topics**: Ana konular
- **prerequisites**: Önce okunması gereken paper id'leri
- **key_concepts**: Bu paper'dan öğrenilecek temel kavramlar
- **summary**: Kısa özet
- **is_essential**: Pratik uygulama yolu için kritik mi (true/false)
- **status**: `not_started` / `reading` / `done` / `skipped`
- **priority**: 1 (yüksek) — 5 (düşük)
- **notes**: Kişisel notlar (sen doldur)

---

## AŞAMA 1 — Temel Kavramlar ve Genel Bakış

### 1. Liebe (2002) — Accuracy Performance of Star Trackers: A Tutorial

```yaml
id: liebe2002
filename: Accuracy_performance_of_star_trackers__a_tutorial.pdf
title: Accuracy Performance of Star Trackers - A Tutorial
authors: Carl Christian Liebe
year: 2002
venue: IEEE Transactions on Aerospace and Electronic Systems
reading_order: 1
stage: foundations
difficulty: beginner
estimated_hours: 4.0
topics:
  - star tracker hardware
  - field of view (FOV)
  - centroiding
  - calibration
  - error tree
prerequisites: []
key_concepts:
  - pinhole model
  - noise equivalent angle (NEA)
  - S-curve error
  - sky coverage
  - PSF (point spread function)
summary: >
  Yıldız izleyicinin sistem-seviye tanıtımı. Algoritmadan önce donanım
  ve doğruluk parametrelerini öğretir. NOT: Bu PDF repoda yok ama
  elinde mevcut.
is_essential: true
status: not_started
priority: 1
notes: ""
```

### 2. A Survey on Star Identification Algorithms

```yaml
id: survey
filename: A Survey on Star Identification Algorithms.pdf
title: A Survey on Star Identification Algorithms
authors: null
year: null
venue: null
reading_order: 2
stage: foundations
difficulty: beginner
estimated_hours: 3.0
topics:
  - overview
  - classification
  - comparison
prerequisites:
  - liebe2002
key_concepts:
  - subgraph isomorphism
  - pattern matching
  - grid algorithms
summary: >
  Tüm yıldız tanıma yaklaşımlarının kuşbakışı haritası.
  Detay yok, taksonomi var.
is_essential: true
status: not_started
priority: 1
notes: ""
```

### 3. Standard Photometric Systems

```yaml
id: photometric
filename: STANDARD PHOTOMETRIC SYSTEMS.pdf
title: Standard Photometric Systems
authors: null
year: null
venue: null
reading_order: 3
stage: foundations
difficulty: beginner
estimated_hours: 2.0
topics:
  - magnitude
  - spectral class
  - filter systems
prerequisites: []
key_concepts:
  - UBV system
  - Johnson-Cousins
  - apparent magnitude
  - color index
summary: >
  Yıldız parlaklık ölçüm sistemleri. Algoritma girdilerini doğru
  yorumlamak için gerekli.
is_essential: false
status: not_started
priority: 2
notes: ""
```

---

## AŞAMA 2 — Yıldız Katalogları

### 4. The Hipparcos and Tycho Catalogue

```yaml
id: hipparcos
filename: The Hipparacos and Tycho Catalogue.pdf
title: The Hipparcos and Tycho Catalogue
authors: ESA
year: 1997
venue: ESA
reading_order: 4
stage: catalogs
difficulty: intermediate
estimated_hours: 3.0
topics:
  - star catalog
  - astrometry
  - data format
prerequisites:
  - photometric
key_concepts:
  - proper motion
  - parallax
  - catalog completeness
summary: >
  Klasik referans katalog. Çoğu yıldız izleyici hâlâ Hipparcos
  türevi katalogları kullanır.
is_essential: true
status: not_started
priority: 1
notes: ""
```

### 5. Gaia Early Data Release 3

```yaml
id: gaia_edr3
filename: Gaia Early Data Release 3.pdf
title: Gaia Early Data Release 3
authors: Gaia Collaboration
year: 2020
venue: Astronomy & Astrophysics
reading_order: 5
stage: catalogs
difficulty: intermediate
estimated_hours: 4.0
topics:
  - star catalog
  - high precision astrometry
prerequisites:
  - hipparcos
key_concepts:
  - 1.8 billion stars
  - microarcsecond precision
  - DR vs EDR
summary: >
  Modern, çok daha hassas katalog. Hipparcos'tan sonra okunmalı ki
  iyileştirme görülsün.
is_essential: false
status: not_started
priority: 2
notes: ""
```

---

## AŞAMA 3 — Klasik Algoritmalar

### 6. Liebe (1992) — Pattern Recognition of Star Constellations

```yaml
id: liebe1992
filename: Liebe_pattern_recognition_of_star_cons_for_Spacecraft_app.pdf
title: Pattern Recognition of Star Constellations for Spacecraft Applications
authors: Carl Christian Liebe
year: 1992
venue: IEEE AES Magazine
reading_order: 6
stage: classic_algorithms
difficulty: intermediate
estimated_hours: 3.0
topics:
  - triangle algorithm
  - angular distance
prerequisites:
  - survey
  - hipparcos
key_concepts:
  - pairwise angular distance
  - triangle matching
  - feature database
summary: >
  Üçgen-tabanlı yöntem. Yıldız tanımanın "Hello World"u. Sonraki
  tüm yöntemlerin atası.
is_essential: true
status: not_started
priority: 1
notes: ""
```

### 7. Star Pattern Identification by Modified Grid

```yaml
id: modified_grid
filename: star-pattern-identification-technique-by-modified-grid-4eu2i2apff.pdf
title: Star Pattern Identification Technique by Modified Grid
authors: null
year: null
venue: null
reading_order: 7
stage: classic_algorithms
difficulty: intermediate
estimated_hours: 3.0
topics:
  - grid algorithm
  - binary pattern
prerequisites:
  - liebe1992
key_concepts:
  - Padgett grid
  - binary signature
  - boresight reference
summary: >
  Üçgen yönteminden Grid yöntemine geçiş. Boresight'a göre
  yıldızları ızgaraya yerleştirip ikili örüntü oluşturma.
is_essential: false
status: not_started
priority: 3
notes: ""
```

### 8. A Two-Step Matching Algorithm for Autonomous Star Identification

```yaml
id: two_step
filename: A two-step matching algorithm for autonomous star identification.pdf
title: A Two-Step Matching Algorithm for Autonomous Star Identification
authors: null
year: null
venue: null
reading_order: 8
stage: classic_algorithms
difficulty: intermediate
estimated_hours: 2.5
topics:
  - two-stage matching
  - verification
prerequisites:
  - liebe1992
key_concepts:
  - coarse matching
  - verification stage
  - false match rejection
summary: >
  İki aşamalı eşleme. Önce kaba eşleme, sonra doğrulama. Bu yaklaşım
  modern algoritmalarda standart hâle geldi.
is_essential: false
status: not_started
priority: 3
notes: ""
```

---

## AŞAMA 4 — Veri Yapıları ve Hızlandırma

### 9. Foundations of Multidimensional and Metric Data Structures

```yaml
id: samet_book
filename: Foundations of Multidimensional and.pdf
title: Foundations of Multidimensional and Metric Data Structures
authors: Hanan Samet
year: 2006
venue: Morgan Kaufmann (book)
reading_order: 9
stage: data_structures
difficulty: advanced
estimated_hours: 8.0
topics:
  - k-d tree
  - range tree
  - R-tree
  - nearest neighbor search
prerequisites: []
key_concepts:
  - spatial indexing
  - multidimensional search
  - metric trees
summary: >
  Kitap. Tamamı okunmaz; k-d tree ve en yakın komşu araması
  bölümleri yeterli.
is_essential: false
status: not_started
priority: 3
notes: "Kitap - sadece ilgili bölümler"
```

### 10. The n-Dimensional k-Vector and Its Application

```yaml
id: kvector
filename: The n-dimensional k-vector and its application to.pdf
title: The n-Dimensional k-Vector and Its Application to Data Searching
authors: Daniele Mortari
year: null
venue: null
reading_order: 10
stage: data_structures
difficulty: advanced
estimated_hours: 4.0
topics:
  - k-vector
  - O(1) search
  - sorted table search
prerequisites:
  - samet_book
key_concepts:
  - range search in O(1)
  - precomputed index
  - Mortari's k-vector
summary: >
  Mortari'nin k-vector tekniği. Sıralı tablodan O(1) zamanda arama.
  Pyramid dahil birçok modern algoritmanın temeli.
is_essential: true
status: not_started
priority: 1
notes: ""
```

### 11. Clustering Database

```yaml
id: clustering
filename: clustering db.pdf
title: Clustering Database
authors: null
year: null
venue: null
reading_order: 11
stage: data_structures
difficulty: intermediate
estimated_hours: 2.0
topics:
  - clustering
  - search space reduction
prerequisites: []
key_concepts:
  - cluster-based indexing
  - k-means style grouping
summary: >
  Kümeleme tabanlı yaklaşım. Yıldızları gruplara ayırıp arama uzayını
  daraltma. Hash tablolarına geçişten önce iyi bir köprü.
is_essential: false
status: not_started
priority: 4
notes: ""
```

---

## AŞAMA 5 — Modern / İleri Algoritmalar

### 12. Nondimensional Star Identification

```yaml
id: nondimensional
filename: Nondimensional Star.pdf
title: Nondimensional Star Identification
authors: null
year: null
venue: null
reading_order: 12
stage: modern_algorithms
difficulty: advanced
estimated_hours: 3.0
topics:
  - scale-invariant identification
  - dimensionless features
prerequisites:
  - liebe1992
key_concepts:
  - scale invariance
  - focal length independence
  - ratio-based features
summary: >
  Ölçek-bağımsız tanıma. FOV veya odak uzaklığı tam bilinmediğinde
  bile çalışır.
is_essential: false
status: not_started
priority: 4
notes: ""
```

### 13. Fast Star Pattern Recognition

```yaml
id: fast_pattern
filename: Fast Star Pattern Recognition.pdf
title: Fast Star Pattern Recognition
authors: null
year: null
venue: null
reading_order: 13
stage: modern_algorithms
difficulty: advanced
estimated_hours: 3.0
topics:
  - speed optimization
  - pattern recognition
prerequisites:
  - liebe1992
  - kvector
key_concepts:
  - fast lookup
  - reduced search space
summary: >
  Hız optimizasyonlarına odaklı. Önceki algoritmaları hızlandırma
  teknikleri.
is_essential: false
status: not_started
priority: 3
notes: ""
```

### 14. Search-Less Algorithm for Star Pattern Recognition

```yaml
id: searchless
filename: Search-Less Algorithm for.pdf
title: Search-Less Algorithm for Star Pattern Recognition
authors: Daniele Mortari
year: 1997
venue: Journal of Astronautical Sciences
reading_order: 14
stage: modern_algorithms
difficulty: advanced
estimated_hours: 4.0
topics:
  - search-less identification
  - direct lookup
prerequisites:
  - kvector
key_concepts:
  - no iterative search
  - direct indexing
  - speed advantage
summary: >
  Mortari'nin "arama yapmayan" yöntemi. Çok hızlı ama daha karmaşık.
  k-vector'ü anlamadan okumak zor.
is_essential: false
status: not_started
priority: 3
notes: ""
```

### 15. Mortari — The Pyramid Star Identification Technique

```yaml
id: pyramid
filename: NAVIGATION - 2014 - MORTARI - The Pyramid Star Identification Technique.pdf
title: The Pyramid Star Identification Technique
authors: Daniele Mortari
year: 2014
venue: NAVIGATION (Journal of the Institute of Navigation)
reading_order: 15
stage: modern_algorithms
difficulty: expert
estimated_hours: 5.0
topics:
  - pyramid algorithm
  - false star rejection
  - robust identification
prerequisites:
  - liebe1992
  - two_step
  - kvector
key_concepts:
  - pyramid structure (4-star)
  - false star rejection
  - feature uniqueness
summary: >
  Alanın en güvenilir ve en çok kullanılan algoritması. Üçgen +
  iki aşamalı eşleme + k-vector fikirlerini birleştirir. Geç
  okunmalı, erken değil.
is_essential: true
status: not_started
priority: 1
notes: ""
```

### 16. TETRA — Star Identification with Hash Tables

```yaml
id: tetra
filename: "TETRA_ Star Identification with Hash Tables.pdf"
title: "TETRA: Star Identification with Hash Tables"
authors: null
year: null
venue: null
reading_order: 16
stage: modern_algorithms
difficulty: advanced
estimated_hours: 3.5
topics:
  - hash tables
  - CubeSat-friendly algorithms
  - constrained memory
prerequisites:
  - pyramid
key_concepts:
  - hash-based lookup
  - geometric hashing
  - memory-efficient catalog
summary: >
  Hash tablolarıyla yıldız tanıma. CubeSat'lar için tasarlanmış,
  sınırlı hafızada hızlı çalışıyor. Modern ve pratik.
is_essential: false
status: not_started
priority: 2
notes: ""
```

---

## AŞAMA 6 — Sistem-Seviye ve Uygulama

### 17. StarNav III — A Three Fields of View Star Tracker

```yaml
id: starnav3
filename: StarNav_III_a_three_fields_of_view_star_tracker.pdf
title: StarNav III - A Three Fields of View Star Tracker
authors: null
year: null
venue: null
reading_order: 17
stage: system_level
difficulty: advanced
estimated_hours: 3.0
topics:
  - multi-FOV system
  - hardware architecture
prerequisites:
  - liebe2002
  - pyramid
key_concepts:
  - three-FOV design
  - attitude redundancy
  - improved sky coverage
summary: >
  Çok-FOV'lu sistem tasarımı. Tek bir yıldız izleyici yerine üçünü
  birden kullanmak. Algoritmik değil mimari bir çözüm.
is_essential: false
status: not_started
priority: 4
notes: ""
```

### 18. Sensors-15-16412

```yaml
id: sensors_15
filename: sensors-15-16412.pdf
title: "(MDPI Sensors makalesi - başlık doğrulanmalı)"
authors: null
year: 2015
venue: MDPI Sensors
reading_order: 18
stage: system_level
difficulty: intermediate
estimated_hours: 2.5
topics:
  - sensor integration
  - implementation details
prerequisites:
  - liebe2002
key_concepts: []
summary: >
  MDPI Sensors dergisinden bir makale. Açıp tam başlığı/içeriği
  belirlemek gerekiyor.
is_essential: false
status: not_started
priority: 4
notes: "Tam içerik belirlenecek"
```

### 19. Flight Algorithms for Autonomous Tracking (Book)

```yaml
id: flight_book
filename: FLIGHT ALGORITHMS FOR AUTONOMOUS TRACKING BOOK.pdf
title: Flight Algorithms for Autonomous Tracking
authors: null
year: null
venue: book
reading_order: 19
stage: system_level
difficulty: advanced
estimated_hours: 12.0
topics:
  - flight software
  - autonomous tracking
  - integration
prerequisites:
  - liebe2002
key_concepts:
  - reference book
  - mission-level integration
summary: >
  Kitap. Baştan sona okunmaz, referans olarak kullanılır.
  Belirli konuları derinleştirmek için.
is_essential: false
status: not_started
priority: 5
notes: "Referans kitabı"
```

---

## AŞAMA 7 — Kapsamlı Referans

### 20. Zhang — Star Identification: Methods, Techniques and Algorithms

```yaml
id: zhang_book
filename: 782430170-Guangjun-Zhang-Star-Identification-Methods-Techniques-and-Algorithms.pdf
title: "Star Identification: Methods, Techniques and Algorithms"
authors: Guangjun Zhang
year: 2017
venue: Springer (book)
reading_order: 20
stage: reference
difficulty: expert
estimated_hours: 20.0
topics:
  - comprehensive reference
  - all methods
prerequisites:
  - pyramid
  - tetra
key_concepts:
  - encyclopedic coverage
summary: >
  Kapsamlı kitap. Belirli konuları derinleştirmek istediğinde
  başvurulur. İndeksten ihtiyacın olan bölüme bakmak en mantıklısı.
is_essential: false
status: not_started
priority: 5
notes: "Referans kitabı, baştan sona okunmaz"
```

---

## SINIFLANDIRILAMAYANLAR

### LISA Paper

```yaml
id: lisa
filename: LISApaper.pdf
title: "(LISA - Laser Interferometer Space Antenna ile ilgili olabilir)"
authors: null
year: null
venue: null
reading_order: 999
stage: unclassified
difficulty: intermediate
estimated_hours: null
topics: []
prerequisites: []
key_concepts: []
summary: >
  Yıldız tanımayla doğrudan ilgisi olmayabilir. Açıp içeriği
  görmek gerekiyor.
is_essential: false
status: not_started
priority: 5
notes: "İçerik belirlenecek"
```

### Index PDF

```yaml
id: index
filename: index.pdf
title: "(Genel dizin/rehber olabilir)"
authors: null
year: null
venue: null
reading_order: 0
stage: unclassified
difficulty: beginner
estimated_hours: null
topics: []
prerequisites: []
key_concepts: []
summary: >
  Muhtemelen bir genel dizin veya rehber. En başta açıp ne olduğuna
  bakmak iyi olur.
is_essential: false
status: not_started
priority: 5
notes: "En başta aç ve içeriği belirle"
```

---

## HIZLI BAŞLANGIÇ — Pratik Uygulama Yolu

Sadece çalışan bir yıldız tanıma kodu yazmak istiyorsan, şu 6 paper yeterli:

1. **liebe2002** — Sistem-seviye temel
2. **survey** — Algoritma haritası
3. **hipparcos** — Veri kaynağı
4. **liebe1992** — Üçgen algoritması
5. **kvector** — Hızlı arama
6. **pyramid** — Modern standart

Bu altısı işin **%80'ini** görür. Toplam tahmini süre: ~22 saat.

---

## AKADEMİK YOL — Tam Sıra

Tez veya akademik çalışma yapıyorsan, 1'den 20'ye sırayla okumak gerekir. Her yöntemin diğerlerinden farkını bilmek literatür eleştirisi için şart. Toplam tahmini süre: ~80-100 saat.

---

## İLERLEME TAKİBİ

| # | ID | Başlık | Aşama | Durum | Öncelik |
|---|-----|--------|-------|-------|---------|
| 1 | liebe2002 | Star Trackers Tutorial | Foundations | ⬜ | 1 |
| 2 | survey | Survey on Star ID | Foundations | ⬜ | 1 |
| 3 | photometric | Photometric Systems | Foundations | ⬜ | 2 |
| 4 | hipparcos | Hipparcos Catalogue | Catalogs | ⬜ | 1 |
| 5 | gaia_edr3 | Gaia EDR3 | Catalogs | ⬜ | 2 |
| 6 | liebe1992 | Pattern Recognition | Classic | ⬜ | 1 |
| 7 | modified_grid | Modified Grid | Classic | ⬜ | 3 |
| 8 | two_step | Two-Step Matching | Classic | ⬜ | 3 |
| 9 | samet_book | Samet (Data Structures) | Data Structures | ⬜ | 3 |
| 10 | kvector | k-Vector | Data Structures | ⬜ | 1 |
| 11 | clustering | Clustering DB | Data Structures | ⬜ | 4 |
| 12 | nondimensional | Nondimensional Star ID | Modern | ⬜ | 4 |
| 13 | fast_pattern | Fast Pattern Recognition | Modern | ⬜ | 3 |
| 14 | searchless | Search-Less Algorithm | Modern | ⬜ | 3 |
| 15 | pyramid | Pyramid Algorithm | Modern | ⬜ | 1 |
| 16 | tetra | TETRA (Hash Tables) | Modern | ⬜ | 2 |
| 17 | starnav3 | StarNav III | System | ⬜ | 4 |
| 18 | sensors_15 | Sensors-15-16412 | System | ⬜ | 4 |
| 19 | flight_book | Flight Algorithms (book) | System | ⬜ | 5 |
| 20 | zhang_book | Zhang (book) | Reference | ⬜ | 5 |
| ? | lisa | LISA Paper | Unclassified | ⬜ | 5 |
| ? | index | Index PDF | Unclassified | ⬜ | 5 |

> Durum sembolleri: ⬜ Başlanmadı | 🟨 Okunuyor | ✅ Bitti | ⏭️ Atlandı

---

## CLAUDE CODE'A NOT

Bu dosyayı düzenlemek için Claude Code'a şu tarz komutlar verebilirsin:

- "Liebe 1992'yi `done` olarak işaretle ve şu notu ekle: ..."
- "Şu paper'ları essential yap: ..."
- "Aşama 3'teki tüm paper'ların öncelik sıralamasını yeniden değerlendir"
- "Bu YAML bloklarını gerçek bir Python dataclass'ına dönüştür"
- "Tahmini süreleri toplayıp aşama bazında özet çıkar"
- "İlerleme tablosundaki durum sembollerini güncelle"

YAML blokları intentional olarak markdown içinde tutuldu — hem okunabilir hem de programatik olarak parse edilebilir.
