"""Paylaşılan opsiyonel doğrulayıcı (brief 03b İş 2).

`ransac_confirm`: herhangi bir algoritmanın `CandidateMatch` çıktısına
uygulanabilen, **truth kullanmayan**, dayanıklı (RANSAC-tarzı) attitude
doğrulaması. En yüksek-güvenli eşleşme çiftlerinden attitude tohumlanır, her
tohum için inlier (artık açısı <= gate) kümesi sayılır, en büyük tutarlı küme
tutulur, inlier'lardan yeniden kestirilip rafine edilir.

Mantık `triangle_planar._confirm` ile birebir; tek fark katalog inertial
vektörüne `catalog.by_id(hip)` üzerinden erişir, böylece her algoritmaya
uygulanabilir. Faz 2 ablation'ında "native vs +ortak doğrulayıcı" ekseni olarak
kullanılır. Bir algoritmanın çıktısına SONRADAN yapıştırmak recall açığını
kapatmaz (doğrulama aday-üretimine gömülü olduğunda etkilidir) — bu yardımcı
"her şeyi düzeltir" diye sunulmaz, kontrollü bir kıyas eksenidir.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .interfaces import BodyVector, CandidateMatch, Catalog
from .quest import davenport_q_method, rotate

_ARCSEC = np.pi / (180.0 * 3600.0)


def ransac_confirm(
    matches: list[CandidateMatch],
    observed: Sequence[BodyVector],
    catalog: Catalog,
    gate_arcsec: float = 60.0,
    max_seeds: int = 8,
) -> list[CandidateMatch]:
    """Dayanıklı attitude doğrulaması (truth'suz).

    <3 tutarlı eşleşme kalırsa `[]` döner (çözümsüz > yanlış). Yalnız gözlem
    body vektörleri + katalog inertial vektörleri kullanılır.
    """
    gate = gate_arcsec * _ARCSEC
    ms = sorted(matches, key=lambda m: -m.confidence)
    by_obs = {o.obs_id: o.u_body for o in observed}

    # geçerli (obs + hip bulunan) eşleşmeleri topla
    kept, body, inertial = [], [], []
    for m in ms:
        if m.obs_id not in by_obs:
            continue
        try:
            star = catalog.by_id(m.hip_id)
        except KeyError:
            continue
        kept.append(m)
        body.append(by_obs[m.obs_id])
        inertial.append(star.u_inertial)

    if len(kept) < 3:
        return matches                      # doğrulayacak kadar veri yok -> dokunma
    body = np.array(body)
    inertial = np.array(inertial)

    def inliers_of(q: np.ndarray) -> np.ndarray:
        pred = rotate(q, inertial)
        resid = np.arccos(np.clip(np.sum(pred * body, axis=1), -1.0, 1.0))
        return resid <= gate

    seeds = range(min(max_seeds, len(kept)))
    best_mask = None
    for a in seeds:
        for b in range(a + 1, min(max_seeds, len(kept))):
            try:
                q = davenport_q_method(body[[a, b]], inertial[[a, b]])
            except Exception:
                continue
            mask = inliers_of(q)
            if best_mask is None or mask.sum() > best_mask.sum():
                best_mask = mask

    if best_mask is None or best_mask.sum() < 3:
        return []                           # tutarlı küme yok -> çözümsüz (>yanlış)

    # rafine: inlier'lardan yeniden kestir, yeniden seç
    try:
        q = davenport_q_method(body[best_mask], inertial[best_mask])
        best_mask = inliers_of(q)
    except Exception:
        pass
    return [m for m, keep in zip(kept, best_mask) if keep]
