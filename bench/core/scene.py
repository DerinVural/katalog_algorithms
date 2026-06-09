"""Sahne simülatörü (brief 01).

Girdi: catalog, sensor, q_true, noise_cfg, rng.
Çıktı: (list[BodyVector], SceneTruth).

q_true ile katalog yıldızları gövde çerçevesine döndürülür; dairesel FOV
(yarıçap = FOV_H/2) içinde kalanlar seçilir. Gürültü parametriktir
(noise_cfg ile aç/kapa): centroid pozisyon gürültüsü, magnitude gürültüsü,
false-star/spike, eksik yıldız. Spike'lar truth'a KONULMAZ.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .interfaces import BodyVector, Catalog, SceneTruth
from .pinhole import body_to_focal, focal_to_body
from .quest import rotate
from .sensor import SENSOR, SensorProfile


@dataclass
class NoiseConfig:
    """Gürültü parametreleri. Hepsi 0/kapalı = gürültüsüz sahne."""

    sigma_centroid_arcsec: float = 0.0   # centroid pozisyon gürültüsü (Gaussian)
    sigma_mag: float = 0.0               # magnitude gürültüsü (Gaussian)
    n_spikes: int = 0                    # FOV içine rastgele sahte gözlem sayısı
    p_missing: float = 0.0               # her gerçek yıldızı düşürme olasılığı
    spike_mag_range: tuple[float, float] = (1.0, 6.0)

    @property
    def enabled(self) -> bool:
        return (
            self.sigma_centroid_arcsec > 0
            or self.sigma_mag > 0
            or self.n_spikes > 0
            or self.p_missing > 0
        )


NOISELESS = NoiseConfig()


def _visible_indices(u_body: np.ndarray, sensor: SensorProfile) -> np.ndarray:
    """Dairesel FOV (yarıçap FOV_H/2) ve boresight yarıküresi içindekiler."""
    in_front = u_body[:, 2] > 0
    cos_lim = np.cos(sensor.fov_radius_rad)
    in_fov = u_body[:, 2] >= cos_lim          # boresight=+z, cos(angle)=u_z
    return np.where(in_front & in_fov)[0]


def simulate_scene(
    catalog: Catalog,
    q_true: np.ndarray,
    noise_cfg: NoiseConfig = NOISELESS,
    rng: np.random.Generator | None = None,
    sensor: SensorProfile = SENSOR,
) -> tuple[list[BodyVector], SceneTruth]:
    if rng is None:
        rng = np.random.default_rng()

    # 1) katalog -> gövde çerçevesi, FOV seçimi
    u_body_all = rotate(q_true, catalog.vectors)        # (N,3)
    vis = _visible_indices(u_body_all, sensor)

    sigma_px = noise_cfg.sigma_centroid_arcsec / sensor.pixel_scale_arcsec

    observations: list[tuple[np.ndarray, float, int | None]] = []  # (u_body, mag, hip)
    for idx in vis:
        if noise_cfg.p_missing > 0 and rng.random() < noise_cfg.p_missing:
            continue  # eksik yıldız
        star = catalog.stars[idx]
        u = u_body_all[idx]
        # centroid gürültüsü: piksel düzleminde Gaussian, sonra geri projeksiyon
        px = body_to_focal(u, sensor)
        if sigma_px > 0:
            px = px + rng.normal(0.0, sigma_px, size=2)
        u_noisy = focal_to_body(px[0], px[1], sensor)
        mag = star.mag + (rng.normal(0.0, noise_cfg.sigma_mag)
                          if noise_cfg.sigma_mag > 0 else 0.0)
        observations.append((u_noisy, mag, star.hip_id))

    # 2) spike (false star): FOV içinde rastgele konum, truth'ta YOK
    lo, hi = noise_cfg.spike_mag_range
    r_max = sensor.focal_length_px * np.tan(sensor.fov_radius_rad)
    for _ in range(noise_cfg.n_spikes):
        # dairesel FOV içinde üniform piksel konumu
        rad = r_max * np.sqrt(rng.random())
        ang = 2 * np.pi * rng.random()
        px = np.array([rad * np.cos(ang), rad * np.sin(ang)])
        u_spike = focal_to_body(px[0], px[1], sensor)
        observations.append((u_spike, float(rng.uniform(lo, hi)), None))

    # 3) karıştır + obs_id ata; truth yalnız gerçek yıldızlar için
    order = rng.permutation(len(observations))
    body_vectors: list[BodyVector] = []
    true_matches: dict[int, int] = {}
    for obs_id, src in enumerate(order):
        u, mag, hip = observations[src]
        body_vectors.append(
            BodyVector(
                obs_id=obs_id,
                u_body=u,
                mag=mag,
                centroid_px=body_to_focal(u, sensor),
            )
        )
        if hip is not None:
            true_matches[obs_id] = hip

    truth = SceneTruth(q_true=np.asarray(q_true, dtype=float), true_matches=true_matches)
    return body_vectors, truth
