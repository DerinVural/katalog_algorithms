"""CMV4000 sensör profili (PROJECT_PLAN.md §1).

Türetilen değerler (focal length, pixel scale) dokümante edilen sabit
değerlerle assert ile karşılaştırılır — tutarlılık kontrolü.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- Dokümante edilen sabitler (brief 01) ---
DETECTOR = "CMV4000"
NPIX = 2048
PIXEL_PITCH_UM = 5.5
FOV_H_DEG = 14.7
FOCAL_LENGTH_MM = 43.7      # türetilen, doğrula
PIXEL_SCALE_ARCSEC = 25.8   # türetilen
MAG_LIMIT = 6.0

# --- Türetilen değerler ---
# Dedektör genişliği: w = NPIX * pixel_pitch
SENSOR_WIDTH_MM = NPIX * PIXEL_PITCH_UM / 1000.0           # 11.264 mm
# f = (w/2) / tan(FOV/2)
_FOCAL_COMPUTED_MM = (SENSOR_WIDTH_MM / 2.0) / np.tan(np.radians(FOV_H_DEG / 2.0))
# arcsec/px = FOV[arcsec] / NPIX
_PIXEL_SCALE_COMPUTED = FOV_H_DEG * 3600.0 / NPIX
# köşegen FOV
FOV_DIAG_DEG = float(
    np.degrees(2.0 * np.arctan(np.sqrt(2.0) * np.tan(np.radians(FOV_H_DEG / 2.0))))
)

# Tutarlılık kontrolü: türetilen ≈ dokümante (yuvarlama toleransı 0.1)
assert abs(_FOCAL_COMPUTED_MM - FOCAL_LENGTH_MM) < 0.1, (
    f"Focal length tutarsız: hesaplanan {_FOCAL_COMPUTED_MM:.3f} mm vs "
    f"sabit {FOCAL_LENGTH_MM} mm"
)
assert abs(_PIXEL_SCALE_COMPUTED - PIXEL_SCALE_ARCSEC) < 0.1, (
    f"Pixel scale tutarsız: hesaplanan {_PIXEL_SCALE_COMPUTED:.3f} arcsec/px vs "
    f"sabit {PIXEL_SCALE_ARCSEC} arcsec/px"
)


@dataclass(frozen=True)
class SensorProfile:
    """Sahne ve pinhole modülünün kullandığı sabit sensör profili."""

    detector: str
    npix: int
    pixel_pitch_um: float
    fov_h_deg: float
    focal_length_mm: float
    pixel_scale_arcsec: float
    mag_limit: float

    @property
    def focal_length_px(self) -> float:
        """Pinhole modeli için odak uzaklığı (piksel cinsinden).

        Birincil ölçülen büyüklüklerden (FOV, NPIX) türetilir; böylece
        pinhole ve sahne kendi içinde tutarlı kalır.
        """
        return (self.npix / 2.0) / np.tan(np.radians(self.fov_h_deg / 2.0))

    @property
    def fov_radius_deg(self) -> float:
        """Dairesel FOV yarıçapı = FOV_H / 2 (brief 01, scene)."""
        return self.fov_h_deg / 2.0

    @property
    def fov_radius_rad(self) -> float:
        return np.radians(self.fov_radius_deg)


SENSOR = SensorProfile(
    detector=DETECTOR,
    npix=NPIX,
    pixel_pitch_um=PIXEL_PITCH_UM,
    fov_h_deg=FOV_H_DEG,
    focal_length_mm=FOCAL_LENGTH_MM,
    pixel_scale_arcsec=PIXEL_SCALE_ARCSEC,
    mag_limit=MAG_LIMIT,
)
