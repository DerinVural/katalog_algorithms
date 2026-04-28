# Katalog Algorithms — Yıldız Tanıma Literatürü

Yıldız tanıma (star identification) algoritmalarını sıfırdan öğrenmek için yapılandırılmış paper koleksiyonu. PDF'ler okuma sırasına göre 7 aşamaya ayrılmıştır.

> Tam öğrenme yolu, prerequisite zincirleri ve YAML metadata için: **[learning_path.md](./learning_path.md)**

---

## Klasör Yapısı

| Klasör | Aşama | İçerik |
|---|---|---|
| [01_Foundations](./01_Foundations) | Temel Kavramlar | Genel bakış, fotometri |
| [02_Catalogs](./02_Catalogs) | Yıldız Katalogları | Hipparcos, Gaia |
| [03_Classic_Algorithms](./03_Classic_Algorithms) | Klasik Algoritmalar | Üçgen, grid, two-step |
| [04_Data_Structures](./04_Data_Structures) | Veri Yapıları | k-d tree, k-vector, clustering |
| [05_Modern_Algorithms](./05_Modern_Algorithms) | Modern Algoritmalar | Pyramid, TETRA, search-less |
| [06_System_Level](./06_System_Level) | Sistem Seviyesi | Donanım, entegrasyon |
| [07_Reference](./07_Reference) | Kapsamlı Referans | Zhang kitabı |
| [99_Unclassified](./99_Unclassified) | Sınıflandırılmamış | İncelenecek dosyalar |

---

## Hızlı Başlangıç (Pratik Yol — ~22 saat)

Sadece çalışan bir yıldız tanıma kodu yazmak istiyorsan, şu 6 paper işin **%80'ini** görür:

1. **Liebe (2002)** — *Accuracy Performance of Star Trackers: A Tutorial* — Sistem-seviye temel _(repoda yok, harici)_
2. **[A Survey on Star Identification Algorithms](./01_Foundations/A%20Survey%20on%20Star%20Identification%20Algorithms.pdf)** — Algoritma haritası
3. **[The Hipparcos and Tycho Catalogue](./02_Catalogs/The%20Hipparacos%20and%20Tycho%20Catalogue.pdf)** — Veri kaynağı
4. **[Liebe (1992) — Pattern Recognition of Star Constellations](./03_Classic_Algorithms/Liebe_pattern_recognition_of_star_cons_for_Spacecraft_app.pdf)** — Üçgen algoritması
5. **[The n-Dimensional k-Vector](./04_Data_Structures/The%20n-dimensional%20k-vector%20and%20its%20application%20to.pdf)** — Hızlı arama
6. **[The Pyramid Star Identification Technique](./05_Modern_Algorithms/NAVIGATION%20-%202014%20-%20MORTARI%20-%20The%20Pyramid%20Star%20Identification%20Technique.pdf)** — Modern standart

---

## Akademik Yol (Tam Sıra — ~80–100 saat)

Tez veya akademik çalışma için 1'den 20'ye sırayla okumak gerekir.

### Aşama 1 — Temel Kavramlar
1. _Liebe (2002) — Star Trackers Tutorial_ (repoda yok)
2. [A Survey on Star Identification Algorithms](./01_Foundations/A%20Survey%20on%20Star%20Identification%20Algorithms.pdf)
3. [Standard Photometric Systems](./01_Foundations/STANDARD%20PHOTOMETRIC%20SYSTEMS.pdf)

### Aşama 2 — Yıldız Katalogları
4. [The Hipparcos and Tycho Catalogue](./02_Catalogs/The%20Hipparacos%20and%20Tycho%20Catalogue.pdf)
5. [Gaia Early Data Release 3](./02_Catalogs/Gaia%20Early%20Data%20Release%203.pdf)

### Aşama 3 — Klasik Algoritmalar
6. [Liebe (1992) — Pattern Recognition of Star Constellations](./03_Classic_Algorithms/Liebe_pattern_recognition_of_star_cons_for_Spacecraft_app.pdf)
7. [Star Pattern Identification by Modified Grid](./03_Classic_Algorithms/star-pattern-identification-technique-by-modified-grid-4eu2i2apff.pdf)
8. [A Two-Step Matching Algorithm](./03_Classic_Algorithms/A%20two-step%20matching%20algorithm%20for%20autonomous%20star%20identification.pdf)

### Aşama 4 — Veri Yapıları ve Hızlandırma
9. [Foundations of Multidimensional and Metric Data Structures (Samet)](./04_Data_Structures/Foundations%20of%20Multidimensional%20and.pdf)
10. [The n-Dimensional k-Vector (Mortari)](./04_Data_Structures/The%20n-dimensional%20k-vector%20and%20its%20application%20to.pdf)
11. [Clustering Database](./04_Data_Structures/clustering%20db.pdf)

### Aşama 5 — Modern / İleri Algoritmalar
12. [Nondimensional Star Identification](./05_Modern_Algorithms/Nondimensional%20Star.pdf)
13. [Fast Star Pattern Recognition](./05_Modern_Algorithms/Fast%20Star%20Pattern%20Recognition.pdf)
14. [Search-Less Algorithm for Star Pattern Recognition](./05_Modern_Algorithms/Search-Less%20Algorithm%20for.pdf)
15. [The Pyramid Star Identification Technique (Mortari, 2014)](./05_Modern_Algorithms/NAVIGATION%20-%202014%20-%20MORTARI%20-%20The%20Pyramid%20Star%20Identification%20Technique.pdf)
16. [TETRA: Star Identification with Hash Tables](./05_Modern_Algorithms/TETRA_%20Star%20Identification%20with%20Hash%20Tables.pdf)

### Aşama 6 — Sistem-Seviye ve Uygulama
17. [StarNav III — Three Fields of View Star Tracker](./06_System_Level/StarNav_III_a_three_fields_of_view_star_tracker.pdf)
18. [Sensors-15-16412 (MDPI)](./06_System_Level/sensors-15-16412.pdf)
19. [Flight Algorithms for Autonomous Tracking (book)](./06_System_Level/FLIGHT%20ALGORITHMS%20FOR%20AUTONOMOUS%20TRACKING%20BOOK.pdf)

### Aşama 7 — Kapsamlı Referans
20. [Zhang — Star Identification: Methods, Techniques and Algorithms](./07_Reference/782430170-Guangjun-Zhang-Star-Identification-Methods-Techniques-and-Algorithms.pdf)

### Sınıflandırılmamış
- [LISA Paper](./99_Unclassified/LISApaper.pdf) — içerik doğrulanacak
- [Index PDF](./99_Unclassified/index.pdf) — içerik doğrulanacak

---

## İlerleme Tablosu

| # | Paper | Aşama | Öncelik | Essential | Durum |
|---|-------|-------|---------|-----------|-------|
| 1 | Liebe 2002 (Tutorial) | Foundations | 1 | ✅ | ⬜ |
| 2 | Survey | Foundations | 1 | ✅ | ⬜ |
| 3 | Photometric Systems | Foundations | 2 |  | ⬜ |
| 4 | Hipparcos | Catalogs | 1 | ✅ | ⬜ |
| 5 | Gaia EDR3 | Catalogs | 2 |  | ⬜ |
| 6 | Liebe 1992 (Pattern Recognition) | Classic | 1 | ✅ | ⬜ |
| 7 | Modified Grid | Classic | 3 |  | ⬜ |
| 8 | Two-Step Matching | Classic | 3 |  | ⬜ |
| 9 | Samet (Data Structures book) | Data Structures | 3 |  | ⬜ |
| 10 | k-Vector (Mortari) | Data Structures | 1 | ✅ | ⬜ |
| 11 | Clustering DB | Data Structures | 4 |  | ⬜ |
| 12 | Nondimensional | Modern | 4 |  | ⬜ |
| 13 | Fast Pattern Recognition | Modern | 3 |  | ⬜ |
| 14 | Search-Less | Modern | 3 |  | ⬜ |
| 15 | Pyramid (Mortari 2014) | Modern | 1 | ✅ | ⬜ |
| 16 | TETRA | Modern | 2 |  | ⬜ |
| 17 | StarNav III | System | 4 |  | ⬜ |
| 18 | Sensors-15-16412 | System | 4 |  | ⬜ |
| 19 | Flight Algorithms (book) | System | 5 |  | ⬜ |
| 20 | Zhang (book) | Reference | 5 |  | ⬜ |

> Durum: ⬜ Başlanmadı · 🟨 Okunuyor · ✅ Bitti · ⏭️ Atlandı

---

## Önerilen Okuma İpuçları

- **Kitaplar (Samet, Flight Algorithms, Zhang):** Baştan sona okunmaz; ilgili bölümler için referans olarak kullanılır.
- **Pyramid (#15)** algoritmanın "altın standardı"dır — ama önce **#6 (Liebe 1992)**, **#8 (Two-Step)** ve **#10 (k-Vector)** okunmalı, yoksa anlaşılmaz.
- **k-Vector (#10)**, Pyramid ve Search-Less'ın temelidir; atlama.
