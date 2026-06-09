"""Pinhole kamera modeli — focal-plane <-> body birim vektör.

Liebe (1992) denk. (1) ile aynı gnomonik bağıntı. Boresight = +z gövde ekseni;
piksel koordinatları görüntü merkezine (principal point) göredir.

Konvansiyon (ileri ve ters dönüşüm birebir tutarlı):
    focal_to_body(x, y) : u = normalize([x, y, f])
    body_to_focal(u)    : (x, y) = (f * u_x / u_z, f * u_y / u_z),  u_z > 0
"""
from __future__ import annotations

import numpy as np

from .sensor import SENSOR, SensorProfile


def focal_to_body(
    x: np.ndarray | float,
    y: np.ndarray | float,
    sensor: SensorProfile = SENSOR,
) -> np.ndarray:
    """Piksel koordinatından (merkez referanslı) gövde birim vektörü.

    Liebe denk. (1). Tek nokta için (3,), N nokta için (N, 3) döner.
    """
    f = sensor.focal_length_px
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    vec = np.stack([x, y, np.full_like(x, f)], axis=-1)
    norm = np.linalg.norm(vec, axis=-1, keepdims=True)
    return vec / norm


def body_to_focal(
    u_body: np.ndarray,
    sensor: SensorProfile = SENSOR,
) -> np.ndarray:
    """Gövde birim vektöründen piksel koordinatı (sahne render için).

    u_z > 0 (boresight yarıküresi) gerektirir. Tek vektör için (2,),
    (N, 3) için (N, 2) döner.
    """
    f = sensor.focal_length_px
    u = np.asarray(u_body, dtype=float)
    uz = u[..., 2]
    if np.any(uz <= 0):
        raise ValueError("body_to_focal: boresight arkasındaki yıldız (u_z <= 0)")
    x = f * u[..., 0] / uz
    y = f * u[..., 1] / uz
    return np.stack([x, y], axis=-1)
