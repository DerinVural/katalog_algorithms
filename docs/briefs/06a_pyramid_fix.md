# Brief 06a — Pyramid Revizyonu: Gürültü Altında Sahte-Piramit Reddi

**Hedef dosya:** `bench/algorithms/pyramid.py` (revizyon), `bench/tests/test_pyramid.py` (T2 yeniden)
**Durum:** Brief 06 ŞARTLI ONAY aldı. Yapı sadık; ancak PM bağımsız doğrulaması gerçekçi gürültüde sahte-piramit kaçağı buldu.

## PM bulgusu (revizyonun gerekçesi)
Tam-5-gerçek + 63 spike, 60 deneme:
- σ=0 → wrong_attitude **0** (mevcut T2'nin kurgusu; geçiyor)
- **σ=5″ → wrong_attitude 7/60 (~%12)** — kabul edilemez; Pyramid'in varlık sebebi tam bu sayının 0 olması.

Mekanizma: gürültüde gerçek piramidin 6 açısından biri ara sıra 15″'i kaçırır → tarama onbinlerce spike-üçlüsüne devam eder → tek-üçlü düşük yanlış-kabul olasılığı ~50k denemeyle birikir → 6 açısı tesadüfen tutarlı sahte dörtlü kabul edilir. `min_solution_stars=4` koruması boştur: yayılımın ilk 4 eşleşmesi QUEST'in fit ettiği çekirdeğin kendisidir, sahte piramidi hiçbir zaman elemez.

> Spec notu: Brief 06 T2'de σ'yı sabitlememişti — σ=0 okuması implementasyon hatası değil spec boşluğuydu. Bu brief boşluğu kapatır. Deneme sayısının 15'e düşürülmesi ise brief ihlaliydi (≥50 isteniyordu); tekrarlanmasın.

## Yapılacaklar

### 1. İkinci doğrulayıcı yıldız (Mortari-sadık güçlendirme)
`PyramidConfig`'e `n_confirm_stars: int = 2` ekle. `_confirm_pyramid` artık **en az `n_confirm_stars` FARKLI r** bulmalı (her biri üç kesişimde tam-1 hipR ile). Mortari 2004'ün "görüntüde yeterli yıldız varsa ek yıldızlarla doğrula" yaklaşımının karşılığı. Kenar durumu: kalan gözlem sayısı < n_confirm_stars ise eldeki maksimumla yetin **ama** bunu `last_confirm_count` teşhisine yaz; tek-onaylı çözümler T2'de ayrıca sayılsın.

### 2. Çekirdek artık-açı kapısı (ucuz, etkili)
Onaylı dörtlüden QUEST sonrası, **çekirdeğin kendi 4 yıldızının** artıkları (pred-obs açı) `core_residual_gate_arcsec` (öneri: 3×σ_beklenen ~ 20″, config'te) içinde olmalı; değilse üçlüyü reddet, taramaya devam. Sahte dörtlüler 15″ açı-tutarlılığını geçse de QUEST artıkları tipik olarak büyüktür — ucuz bir ikinci filtre.

### 3. `min_solution_stars` anlamlandır
Anlamı "çekirdek dahil toplam" → "**çekirdek DIŞI** en az `min_extra_stars` ek yıldız" (default 1) olarak değiştir; gözlemde çekirdek dışında gerçek yıldız kalmamışsa (f_core==f) şart düşer. Sahte attitude çekirdek dışını açıklayamaz; gerçek attitude açıklar.

### 4. T2'yi yeniden yaz (spec netleştirildi)
- **≥50 deneme** (pazarlıksız), **σ ∈ {0″, 5″}** iki ayrı blok; her ikisinde `wrong_attitude = 0` ZORUNLU.
- Tam-5-gerçek kurgusu (p_missing yerine deterministik 5 gerçek seçimi — PM'in deney kurgusu örnek alınabilir).
- Ek blok: tam-3-gerçek + 63 spike + σ=5″ → beklenen davranış baskın `no_solution` (güvenli), wrong_attitude ≤ 1/50.
- `results/pyramid_torture.csv` üç bloğu da içersin.

### 5. T3 spike taramasını yeni yapılandırmayla yeniden üret
Önceki T3 grafiği güncellensin; Pyramid eğrisinin id_rate maliyeti (güçlendirme bir miktar no_solution artışı getirebilir — kabul edilebilir, raporda görünsün).

## Kabul
- T2 (yeni): üç blok da geçer; σ=5″ bloğunda wrong_attitude=0.
- T1/T4/T5/T6 regresyonsuz; T4 ablation'a `n_confirm_stars=1` modu da eklensin (eski davranış, kıyas için).
- Rapor: güçlendirmenin maliyeti (no_solution / id_rate / süre değişimi) dürüstçe tablolansın.

## Yapma
- Toleransı (15″) değiştirme — sorun toleransta değil, kabul kriterinin istatistiksel gücünde.
- Tarama sırasını / k-vector'ü değiştirme.
- SLA'ya dokunma.
