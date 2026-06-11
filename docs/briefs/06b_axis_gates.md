# Brief 06b — Eksen-Ayrık Hata Kapısı (Liebe §V) + Geçmiş Sayıların Yeniden Denetimi

**Hedef dosyalar:** `bench/core/metrics.py`, `bench/compare.py`, `bench/runner.py`, T2/T3 yeniden üretim, `bench/tests/test_metrics.py`
**Bağımlılık:** 06a onaylandı. **Hiçbir algoritma dosyası değişmez.**
**Dayanak:** Liebe (2002) tutorial §V + denk. (12)/(16): roll NEA, cross-boresight'tan **tipik 6–16× kötüdür** (örneği: 2.3″ cross vs 23″ roll). 06a karşı-bulgusu (PM tarafından bağımsız doğrulandı): tek 60″ toplam-hata kapısı, kimliği kusursuz çözümlerin doğal roll gürültüsünü "tehlikeli" diye damgalıyor — fizik, algoritma hatası sayılıyor.

---

## İş 1 — `wrong_attitude` eksen-ayrık tanım (core/metrics.py)
```python
FALSE_ID_CROSS_ARCSEC = 60.0     # cross-boresight kapısı (mevcut anlamın devamı)
FALSE_ID_ROLL_ARCSEC  = 600.0    # roll kapısı = 10× (Liebe §V: 6–16×; örneğindeki oran 10×)

wrong_attitude = solved and (cross_err > gate_cross or roll_err > gate_roll)
```
- İki kapı da `evaluate` parametresi (default'lar yukarıda, sabit gömme yok).
- `attitude_error_arcsec` (toplam) raporlama için aynen kalır; karar artık eksen-ayrık.
- `no_solution` tanımı değişmez. Eski tek-kapı davranışı isteyen için `false_id_threshold_arcsec=None` benzeri geri-uyum **EKLENMESİN** — temiz kırılım, tek tanım.
- Docstring'e Liebe §V atfı + 06a karşı-bulgu gerekçesi yazılsın.

## İş 2 — Geçmiş sayıların yeniden denetimi (tek seferlik script: `bench/audit_roll.py`)
Faz 1–2'nin yayımlanmış wrong_attitude sayıları eski kapıyla üretildi; yeniden sınıflandırılmalı:
- `phase1_compare` ve `phase2_spike_sweep` koşularını yeni metrikle yeniden üret (aynı seed'ler).
- Ek olarak kısa bir denetim tablosu: her algoritma için eski-kapı wa sayısı → yeni-kapıda {hâlâ-tehlikeli (cross-ihlal veya aşırı-roll), saf-roll-aklanan} ayrımı. `results/roll_audit.csv`.
- Rapora net cümle: hangi Faz-1/2 sonucu değişti, hangisi dayanıklı çıktı. (Beklenti: Liebe'nin "11/300 tehlikeli"sinin bir kısmı aklanır; Triangle/Pyramid'in sahte=0 iddiaları dayanıklı kalır. Beklenti tutmazsa olduğu gibi raporlanır.)

## İş 3 — T2/T3 yeniden koşum
- Pyramid T2: yeni kapıyla σ=5″ bloğunda literal `wrong_attitude=0` artık fiziksel olarak erişilebilir (bayraklı vakalar cross 1–8″, roll 60–96″ < 600″ idi) → T2'ye bu assert geri konabilir; kimlik-düzeyi sahte=0 ve tripwire de KALIR (çift güvence).
- T3 spike taraması yeni kapıyla yeniden; grafik güncellenir.

## Kabul testleri
1. saf-roll vakası (cross=5″, roll=90″) → `wrong_attitude=False` (yeni), eski kapıda True olurdu — test bunu belgeler.
2. cross-ihlal (cross=70″, roll=10″) → True. aşırı-roll (cross=5″, roll=700″) → True.
3. no_solution davranışı regresyonsuz; tüm mevcut testler güncellenmiş anlamla geçer.
4. `audit_roll.csv` üretilir ve rapora özetlenir.

## Yapma
- Algoritma dosyalarına dokunma. Kapı default'larını "testler geçsin" diye ayarlama — 60″/600″ Liebe-dayanaklı sabitlerdir; değişiklik önerisi PM'e gelir.
- Toplam-hata alanını kaldırma (raporlamada kalsın).
