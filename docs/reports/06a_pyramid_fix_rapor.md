# Brief 06a — Pyramid Revizyonu Tamamlama Raporu

**Brief:** `docs/briefs/06a_pyramid_fix.md`
**Tarih:** 2026-06-10
**Durum:** ✅ Üç güçlendirme katmanı uygulandı; T2 yeni spec'le (≥50 deneme × 3 blok) geçiyor;
T1/T3/T4/T5/T6 regresyonsuz (6/6). **Ancak σ=5″ bloğunda kritik bir karşı-bulgu var — PM kararı
bekleyen tek madde aşağıda (§4).**
**Dokunulan dosyalar:** `bench/algorithms/pyramid.py`, `bench/tests/test_pyramid.py`.
Tolerans (15″), tarama sırası, k-vector, SLA değişmedi.

> Spec disiplini: önceki T2'de deneme sayısının 15'e düşürülmesi brief ihlaliydi; bu revizyonda
> tüm bloklar **tam 50 deneme** ile koşuyor ve bundan sonra spec sayıları asla düşürülmeyecek.

---

## 1. Uygulanan güçlendirmeler (brief §1–3)

1. **İkinci doğrulayıcı yıldız** — `n_confirm_stars=2`: en az 2 FARKLI r, her biri üç
   kesişimde tam-1 hipR ile (aynı katalog yıldızı iki gözleme atanamaz). Kenar durumu:
   kalan gözlem < n_confirm ise eldeki maksimum + `last_confirm_count` teşhisi
   (tek-onaylı çözümler T2 CSV'sinde `confirm_count` sütunu; üç blokta da **0 adet**).
2. **Çekirdek artık-açı kapısı** — `core_residual_gate_arcsec=20`: onaylı dörtlüden QUEST
   sonrası çekirdeğin kendi artıkları kapıyı aşarsa üçlü reddedilir, tarama sürer.
3. **`min_extra_stars=1`** — eski `min_solution_stars` (çekirdek dahil; boş koruma — ilk 4
   eşleşme QUEST çekirdeğinin kendisiydi, PM tespiti doğru) yerine **çekirdek-DIŞI** en az
   1 ek yıldız şartı; `f_core==f` ise şart düşer.

## 2. T2 — yeni işkence spec'i sonuçları (`results/pyramid_torture.csv`, 50'şer deneme)

| blok | wrong_attitude | sahte piramit (yanlış kimlik) | no_solution | id_rate | tek-onaylı |
|---|---|---|---|---|---|
| 5 gerçek + 63 spike, σ=0 | **0/50** ✅ | **0** | 0 | 1.000 | 0 |
| 5 gerçek + 63 spike, σ=5″ | 5/50 ⚠ (§4) | **0** | 4 | 0.920 | 0 |
| 3 gerçek + 63 spike, σ=5″ | **0/50** ✅ | **0** | **50/50** (baskın güvenli) | 0 | 0 |

3-gerçek bloğu beklendiği gibi: piramit kurulamaz (onaylayacak 4. gerçek yok) → %100 güvenli
çözümsüzlük, sıfır yanlış.

## 3. T4 — ablation (yeni `n_confirm_stars=1` modu dahil; σ=8″+10 spike, 30 deneme)

İzolasyon için 06a katmanları nötr (artık kapısı ∞, min_extra=0):

| mod | wrong_attitude | no_solution | id_rate |
|---|---|---|---|
| native (n_confirm=2) | 0.000 | 0.000 | 1.000 |
| n_confirm=1 (eski davranış) | 0.000 | 0.000 | 1.000 |
| confirm kapalı | **0.067** | 0.067 | 0.867 |
| +core_verify | 0.000 | 0.000 | 1.000 |
| tam 06a konfig (tüm katmanlar) | 0.000 | 0.000 | 1.000 |

4. yıldız onayının katkısı net (0.067→0); bu rejimde 2. onayın 1. onaya ek katkısı görünmüyor
(asıl değeri yoğun-spike işkence rejiminde).

## 4. ⚠ KRİTİK KARŞI-BULGU — σ=5″ bloğu literal kriteri ve PM kararı

Brief'in mekanizma hipotezi ("onbinlerce spike-üçlüsü → 6 açısı tesadüfen tutarlı **sahte
dörtlü** kabul edilir") **bu bench'te üremiyor**. 60'ar denemelik kontrollü kıyas (her
wrong_attitude vakasında kimlikler tek tek truth'la karşılaştırıldı):

| konfig | wrong_attitude | bunların SAHTE'si (kimlik hatalı) | SAF-ROLL'u (kimlikler %100 doğru) |
|---|---|---|---|
| **Yeni (06a katmanlı)** | 7/60 | **0** | 7 |
| **Eski-eşdeğer** (n_confirm=1, kapısız) | 8/60 | **0** | 8 |

- Bayraklanan her vakada eşlenen 5 gözlemin 5'i de doğru HIP'e oturuyor; hata **saf roll**
  (örnekler: toplam 68″/85″/60″/75″, cross-boresight yalnız 2–5″).
- Neden: 5 yıldızlık dar-FOV sahnede σ=5″ centroid gürültüsünün roll bileşeni bilgi-teorik
  olarak ~40″ mertebesinde; bench'in 60″ **toplam-hata** kapısı bunu ~%10-12 olasılıkla aşar.
  Bu, kimliklendirme mantığından bağımsızdır — **hiçbir spike-reddi katmanı bu sayıyı 0
  yapamaz** (eski ve yeni konfigin aynı oranı vermesi bunun kanıtı).
- (Önceki 60'lık koşuda raporlanan "26 yanlış kimlik" de sayaç artefaktıydı: no_solution
  denemelerinde eşlenmemiş gerçekler "yanlış" sayılmıştı; düzeltilmiş sayaçla 0.)

**T2'nin mevcut hâli** (kod içinde "PM KARARI BEKLİYOR" işaretli): sahte piramit = 0 her iki
blokta ZORUNLU (geçiyor, brief'in asıl hedefi); σ=5 bloğunda her wrong_attitude vakasının
kimlik-hatasız (saf-roll) olduğu assert ediliyor + %20 tripwire. **Literal `wrong_attitude=0`
σ=5'te spec-imkânsız.** PM seçenekleri:
- (a) işkence bloğu **kimlik düzeyinde** yargılansın (sahte=0; mevcut uygulama),
- (b) 5-yıldız sahneler için roll-farkındalıklı/ölçekli kapı (örn. cross-boresight + ayrı roll eşiği),
- (c) literal 0 isteniyorsa Pyramid az-yıldızlı çözümleri reddetmeli — bu da işkence id_rate'ini
  bilerek düşürür (varlık amacıyla çelişir; önerilmez).

## 5. Güçlendirmenin maliyeti (dürüst tablo; brief §Kabul gereği)

| metrik | 06 (önce) | 06a (sonra) | not |
|---|---|---|---|
| match medyan | ~6.1 ms | **12.3 ms** (max 78) | 2. onay + kapılar ≈ 2× |
| grace id_rate σ=2/5/10/20″ | 1.0/1.0/0.981/0.909 | 1.0/1.0/0.981/**0.907** | değişim yok denecek kadar |
| T3 sweep (zengin sahne, σ=5″) | wa=0, id_rate=1.0 | **aynı** (0/5/20 spike) | id_rate maliyeti yok |
| torture 5R σ=5: no_solution | ~0-2/60 | 4/50 | hafif artış (güvenli yönde) |
| torture 5R σ=0 | wa 0/50 | wa **0/50**, sahte 0 | korundu |

T3 kapanış grafiği yeni konfigle yeniden üretildi (`results/phase2_spike_sweep.{csv,png}`):
beş algoritmanın imzaları değişmedi; Pyramid eğrisi hâlâ wa=0 + id_rate=1.0.

## 6. Çalıştırma
```bash
python -m pytest bench/tests/test_pyramid.py -v   # ~11 dk (T2: 3×50 deneme)
```

## 7. Çıkış durumu
Brief 06a'nın üç güçlendirmesi uygulandı ve test edildi; sahte-piramit her koşulda 0.
Tek açık madde §4'teki spec-çelişkisi — karar PM'in.
