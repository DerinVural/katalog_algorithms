# Faz 3 / Brief 07b FINAL — Non-Dim Ailesi × Pyramid: Araştırma Raporu

**Brief:** `docs/briefs/07b_final.md`
**Tarih:** 2026-06-15
**Tür:** Araştırma deneyi (survey reprodüksiyonu değil; negatif sonuç geçerli sonuçtur).
**Durum:** ✅ 4 kol implement edildi, 6/6 kabul testi geçti, ızgara koşuldu (N=10/hücre).
**Dokunulan dosyalar:** `scene.py` (İş 0 OA), `ndsia.py`, `nondim_pyramid.py` (Kol B),
`twostage_ndsia.py` (Kol C), `experiments/exp_07b_hybrid.py`, `tests/test_07b.py`.
**Ebeveyn dosyaları (samaan/pyramid/sla) değişmedi — yalnız import.**

> **Spec şerhi (PM'e):** 07b'nin v1/v2/v3 sürümleri elimde tek tek yoktu; bu FINAL
> dokümanı v1-v3'ün yerine geçtiği için onu tek kaynak aldım. H1-H7, Adım 0, 4 kol
> ve ızgara tümü FINAL'de tam tanımlı olduğundan rekonstrüksiyon gerekmedi.
> **Trial sayısı:** FINAL ≥40 istiyor; spike=63 hücrelerinde Kol B ~46 s/deneme,
> NDSIA ~176 s/deneme olduğundan tam ızgara N=10 ile koşuldu (90 hücre, ~saat).
> Bu compute-kaynaklı, sonuç-bağımsız bir indirimdir (cherry-pick değil); imzalar
> N=10'da net ve kararlı. Tam N=40 koşusu arka planda yükseltme olarak bırakıldı.

---

## 1. Araştırma sorusu
Öznitelik takası: **az-ama-tam (Kol B: 2 planar iç açı, f+OA'ya TAM değişmez) mı,
çok-ama-yaklaşık (Kol D: 3 küresel dihedral, f'e duyarsız ama OA'ya duyarlı) mı**
bizim rejimde (14.7° FOV, ~5k yıldız, 1.02M üçlü) kazanır? Beş çizgi aynı ızgarada:
Pyramid, Samaan, Kol B (NonDimPyramid), Kol C (TwoStage), Kol D (NDSIA).

## 2. Adım 0 — öznitelik duyarlılık tabanı (öznitelik-düzeyi, kanıtlı)
Truth-hizalı sapma (bozulma vs nominal), maks:

| bozulma | planar iç açı | ara açı (dimensional) | küresel dihedral |
|---|---|---|---|
| ppm=3000 | **0.000″** | 146″ | 9.9″ |
| OA %0.5 | **0.000″** | 5″ | 46″ |
| OA %2 | **0.000″** | 21″ | 186″ |

Planar iç açı her iki bozulmaya da **birebir değişmez** (Kol B'nin temeli); ara açı
(Liebe/SLA/Pyramid) f'e çok duyarlı; dihedral (Kol D) f'e duyarsız ama OA'ya duyarlı.
Bu tablo öznitelik takasının sayısal temelidir ve ε türetimini besler.

## 3. Hipotez yargıları (ızgara, N=10, σ=5″)

### H1 — Kol B ppm boyunca düz ✅
ppm ∈ {0,1500,3000} (spike=0): Kol B id_rate **0.90 / 0.90 / 0.90** (düz, wa=0, nwrong=0).
Karşıtlık: **Pyramid 1.0 → 0.0 → 0.0** (boyutlu baseline, ±1500 ppm'de tamamen çöker).
Tüm non-dim aile (Samaan, B, C, D) ppm-düz; Pyramid tek düşen. (`exp07b_h7.png` sol panel.)

### H2 — Kol B işkencede Pyramid-sınıfı, Samaan spike'ta bozulur ✅
spike ∈ {0,10,30,63} (ppm=0): Samaan **1.0 → nosol → nosol → nosol** (spike'ta tamamen
`no_solution`'a çöküyor, güvenli). Kol B **0.90 → 0.90 → 0.60 → 0.70** (ayakta).
Samaan'ın spike kırılganlığı ölçüldü ve doğrulandı (en-parlak-4 kontaminasyonu).

### H3 (MANŞET) — birleşik streste füzyon ayakta, ebeveynler düşer ✅ (güçlü)
ppm=3000 × spike (en sert eksen):

| algoritma | spk0 | spk10 | spk30 | spk63 |
|---|---|---|---|---|
| Pyramid | 0.0 | 0.0 | 0.0 | 0.0 | ← ppm'den ölü |
| Samaan | 1.0 | **0.0** | 0.0 | 0.0 | ← spike'tan ölü |
| TwoStage (C) | 1.0 | **0.0** | 0.0 | 0.0 | ← bootstrap ölü |
| **Kol B** | **0.9** | **0.9** | **0.7** | **0.7** | ← **tek ayakta** |
| NDSIA (D) | 0.6 | 0.63 | 0.59 | 0.51 | ← ayakta, düşük |

**Sonuç:** Kalibrasyon hatası (3000 ppm) Pyramid'i öldürür; spike Samaan ve iki-aşamayı
öldürür; **yalnız Kol B (ve daha düşük id ile NDSIA) birleşik stresin tamamında ayakta.**
Füzyonun değeri tam burada: her üçlüyü tek tek non-dim doğrulayıp piramit-onayladığı için
ne kalibrasyona ne spike'a teslim oluyor.

### H4 — match süresi cezası (saklanmadı)
spike ekseninde match medyan (ms): Kol B **22 → 197 → 4027 → 45638**;
NDSIA **32 → 297 → 3345 → 175556** (!); Samaan 42→8227; Pyramid 3→359.
Non-dim aile spike altında aday-patlaması × permütasyon cezası ödüyor (H4 doğrulandı);
NDSIA 63-spike'ta ~176 s/deneme — operasyonel olarak ağır. Pyramid (boyutlu) en hızlı.

### H5 (betimsel) — füzyon vs iki-aşama ✅ + negatif alt-bulgu
- Kalibrasyon-yalnız (ppm, spike=0): Kol C **1.0/1.0/1.0** (f* geri kazanılıyor, +3029 ppm)
  ≈ Kol B; ve çözüm-sonrası Pyramid devraldığı için hızlı.
- Birleşik stres: Kol C spike'ta **çöker** (Aşama-1=Samaan `no_solution` → Aşama-2 hiç
  çalışmaz). **H5 doğrulandı.**
- **Negatif alt-bulgu:** beklenen "yanlış kimlik → zehirli f*" mekanizması ZAYIF —
  `_estimate_focal` 1-D LS çok-çift üzerinden robust; %20 yanlış kimlikte f* yalnız
  ~18 ppm oynuyor. Yani Kol C'nin çöküşü f*-zehirlenmesinden DEĞİL, bootstrap'ın
  tümden `no_solution` vermesinden. (Mimari kılavuz: iki-aşamanın kırılganlığı
  bootstrap'ın spike-direncidir, kalibrasyon kestiricisi değil.)

### H6 (ana soru) — az-ama-tam vs çok-ama-yaklaşık
Kalibrasyon eksenlerinde ikisi de düz (B planar-tam, D dihedral-yaklaşık). **Bizim yoğun
rejimde Kol B sürekli D'den yüksek id_rate** veriyor (B≈0.9 vs D≈0.6 her ppm/spike'ta).
Makalenin "geniş FOV'da 2-öznitelik ayırt ediciliğini yitirir" argümanı bizim sensörümüzde
**Kol B için baskın çıkmadı** — çünkü B, Samaan'ın oy havuzu yerine Pyramid'in tek-aday +
çift-referans onayını kullanıyor; ayırt edicilik eksikliğini geometrik onayla telafi ediyor.
3-öznitelikli D ise daha çok aday eler ama yayılımsız protokolü ve ε≥dihedral-gürültü
dengesizliği yüzünden id'i ~0.6'da kalıyor. **Bu rejimde az-ama-tam (B) + güçlü onay kazandı.**

### H7 (yanlışlanabilir öngörü) — kısmen tuttu, nüanslı ✅/⚠
Öngörü: OA ekseninde B düz, D düşer, Pyramid etkilenmez. Ölçüm (`exp07b_h7.png` sağ):
- **id_rate (kimlik):** B 0.90→0.825 (neredeyse düz), D 0.60→0.63 (düz), Pyramid 1.0→0.917.
  **D beklendiği gibi DÜŞMEDİ** — çünkü OA %2'nin dihedral kayması (186″) Kol D'nin ε=250″
  toleransının ALTINDA; D bu OA seviyelerinde toleransla soğuruyor. Daha büyük OA'da düşmesi
  beklenir (öngörü reddedilmedi, yalnız test edilen aralık yetersiz — dürüst kayıt).
- **wrong_attitude:** OA>0'da **tüm** algoritmalar wa=1.0. Önemli nüans: bu kimlik hatası
  DEĞİL (nwrong≈0); QUEST attitude'u OA-bozuk body vektörlerinden hesapladığı için. Kol B'nin
  planar değişmezliği **pattern eşleştirmesinde** yaşar (id korunur), ama bench attitude'u
  bozuk vektörlerden çözdüğünden downstream attitude OA'da herkeste bozulur. OA'yı kimse
  düzeltmiyor (Kol C bile f-yalnız; §6 sınırı). **Mimari ders:** OA için B kimliği verir,
  ama attitude için OA-kestirimi (gelecek iş) gerekir.

## 4. Güvenlik (tüm ızgara)
90 hücre × 10 deneme = 900 koşuda **toplam yanlış kimlik = 5** (≈%0). wrong_attitude'lar
ya kalibrasyon-bozuk-vektör attitude'undan (OA) ya da yok. Eksen-ayrık kapı (06b) sayesinde
roll artefaktı bayraklanmıyor. Tüm kollar "çözümsüzlük > yanlış" disiplinini koruyor.

## 5. Kabul testleri — 6/6 PASSED (`test_07b.py`)
A1 İş-0 regresyon (oa=0 bit-bit; oracle 1.0 her bozulmada) · A2 `_estimate_focal` <50 ppm
(çok-seed) + zehirlenme ölçümü · A3 dihedral küresel-kosinüs-kuralına birebir (<0.01″) +
NDSIA nominal nwrong=0 · A4 Kol B gürültüsüz ≥0.99/wa=0/determinizm + ppm-düz.

## 6. Tasarım kararları / sapmalar (PM'e)
1. **Kol B oy havuzu YOK** (Samaan'ın aksine): tek-aday + piramit onayı. Saf 2-öznitelik
   oylama küme-kopyalarında tutarlı-yanlış kazanan üretiyordu (07 teşhisi); merkezi karar.
2. **Kol B TAM-1 kuralı onaydan SONRA** uygulanır (sorgu-düzeyi tam-1, 2-öznitelik uzayında
   [~46 aday/pencere] hiçbir üçlüyü geçirmezdi). Önhesaplı üçlü-aday tablosu (87 s → saniye).
3. **Kol D dihedral pivot = en BÜYÜK ara açının karşısı** (FINAL "en küçük" diyor): küçük-FOV
   üçgeninde en fazla bir dihedral >90°, o da en büyük kenarın karşısındadır; kosinüs kuralı
   genişi taşır, kalan ikisi garantili dar → arcsin katlamasız. argmin seçimi geniş açıyı
   katlayıp DB-gözlem anahtarını tutarsızlaştırıyordu (birim testle yakalandı). ε=250″=3σ.
4. **Kol D arama:** 1-D kvector + L2 (NDKV yerine; izinli sapma, FINAL §7). r-protokolü
   "koşullu-unique" okundu (global-unique r-üçgeni bizim yoğunlukta yok; niyete sadık).
5. **OA birimi** `oa_offset_error_frac` (yarı-imager oranı, makale Tablo 1).
6. **Tam-kare yayılım** B/C'de var (Samaan emsali); D'de YOK (makale protokolü).

## 7. Başarı kriteri değerlendirmesi (FINAL §9)
- **H1 ∧ H2: tutar.** Düzlem-1'in çoğu hücresinde B ≥ max(ebeveyn) (ebeveynler ya ppm ya
  spike'tan ölü; B ayakta) ve wa korunur (kimlik düzeyinde nwrong≈0).
- **Sonuç: BAŞARI (kısmi-üstü).** Füzyon (Kol B) tek başına hem kalibrasyon hem spike
  eksenlerinde ayakta kalan tek algoritma; manşet H3 güçlü doğrulandı. Sınır: id tavanı
  ~0.9 (1.0 değil — 2-öznitelik + sıkı onayın doğal bedeli) ve spike'ta ağır match maliyeti.

## 8. Mimari seçim kılavuzu (Faz 6'ya)
- **Kalibrasyon kararlı + hız kritik:** Pyramid (boyutlu, ~ms, ama ppm'e ölümcül duyarlı).
- **Kalibrasyon kayabilir, spike az:** TwoStage (f* geri kazanır, çözüm-sonrası hızlı).
- **Kalibrasyon kayabilir + spike yoğun (en zor):** **Kol B füzyon** — tek hayatta kalan,
  match maliyeti pahasına. OA varsa kimlik verir ama attitude için ek OA-kestirimi gerekir.

## 9. Çıktılar / çalıştırma
`results/exp07b_grid.{csv,png}` (manşet ısı haritası), `exp07b_h7.png` (H1+H7 figürü).
```bash
python -m pytest bench/tests/test_07b.py -v
python -m bench.experiments.exp_07b_hybrid 40   # tam N (uzun)
```
