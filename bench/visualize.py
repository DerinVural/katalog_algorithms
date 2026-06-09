"""Üretilen sahneyi gözlemleme aracı.

Simüle edilen bir sahneyi sensör düzleminde (piksel) çizer:
gerçek yıldızlar vs spike (false-star), parlaklığa göre işaret boyutu,
dairesel FOV sınırı. CSV + PNG değil, doğrudan görsel inceleme içindir.

Kullanım (proje kökünden):
    python -m bench.visualize
    python -m bench.visualize --seed 3 --centroid 10 --spikes 5 --missing 0.1
"""
from __future__ import annotations

import argparse

import numpy as np

from .core.catalog import load_catalog
from .core.scene import NoiseConfig, simulate_scene
from .core.sensor import SENSOR
from .tests.conftest import find_rich_attitude


def visualize_scene(catalog, q_true, noise_cfg, sensor=SENSOR, seed=0, ax=None):
    """Bir sahne simüle edip sensör düzleminde çizer. (fig, ax, observed, truth)."""
    import matplotlib.pyplot as plt

    observed, truth = simulate_scene(
        catalog, q_true, noise_cfg, rng=np.random.default_rng(seed), sensor=sensor
    )
    true_ids = truth.true_matches

    real_xy, real_mag, spike_xy, spike_mag = [], [], [], []
    for o in observed:
        if o.obs_id in true_ids:
            real_xy.append(o.centroid_px)
            real_mag.append(o.mag)
        else:
            spike_xy.append(o.centroid_px)
            spike_mag.append(o.mag)
    real_xy = np.array(real_xy).reshape(-1, 2)
    spike_xy = np.array(spike_xy).reshape(-1, 2)

    if ax is None:
        fig, ax = plt.subplots(figsize=(7.5, 7.5))
    else:
        fig = ax.figure

    half = sensor.npix / 2.0
    # dedektör çerçevesi
    ax.add_patch(plt.Rectangle((-half, -half), sensor.npix, sensor.npix,
                               fill=False, ec="gray", ls="--", lw=1))
    # dairesel FOV sınırı
    r_fov = sensor.focal_length_px * np.tan(sensor.fov_radius_rad)
    ax.add_patch(plt.Circle((0, 0), r_fov, fill=False, ec="steelblue", lw=1.2))

    def sizes(mags):
        return np.clip((6.5 - np.asarray(mags)) * 25, 8, 220)

    if len(real_xy):
        ax.scatter(real_xy[:, 0], real_xy[:, 1], s=sizes(real_mag),
                   c="white", edgecolors="black", linewidths=0.8,
                   label=f"gerçek yıldız ({len(real_xy)})", zorder=3)
    if len(spike_xy):
        ax.scatter(spike_xy[:, 0], spike_xy[:, 1], s=sizes(spike_mag),
                   marker="x", c="crimson", linewidths=1.6,
                   label=f"spike / false-star ({len(spike_xy)})", zorder=4)

    ax.set_facecolor("#0b1020")
    ax.set_xlim(-half * 1.05, half * 1.05)
    ax.set_ylim(-half * 1.05, half * 1.05)
    ax.set_aspect("equal")
    ax.set_xlabel("x [piksel] (boresight = 0)")
    ax.set_ylabel("y [piksel]")
    ax.set_title(
        f"Simüle sahne — {sensor.detector}, FOV {sensor.fov_h_deg}°, "
        f"{len(observed)} gözlem\n"
        f"centroid σ={noise_cfg.sigma_centroid_arcsec}″, "
        f"mag σ={noise_cfg.sigma_mag}, spike={noise_cfg.n_spikes}, "
        f"eksik p={noise_cfg.p_missing}"
    )
    ax.legend(loc="upper right", framealpha=0.9)
    fig.tight_layout()
    return fig, ax, observed, truth


def main() -> None:
    import matplotlib.pyplot as plt
    from pathlib import Path

    p = argparse.ArgumentParser(description="Simüle yıldız sahnesini görselleştir")
    p.add_argument("--seed", type=int, default=0, help="sahne RNG tohumu")
    p.add_argument("--att-seed", type=int, default=0, help="attitude seçim tohumu")
    p.add_argument("--centroid", type=float, default=8.0, help="centroid gürültüsü [arcsec]")
    p.add_argument("--mag", type=float, default=0.1, help="magnitude gürültüsü")
    p.add_argument("--spikes", type=int, default=3, help="spike sayısı")
    p.add_argument("--missing", type=float, default=0.1, help="eksik yıldız olasılığı")
    p.add_argument("--save", default="bench/results/scene.png", help="PNG çıktı yolu")
    p.add_argument("--no-show", action="store_true", help="pencere açma, yalnız kaydet")
    args = p.parse_args()

    print("Katalog yükleniyor...")
    catalog = load_catalog()
    q = find_rich_attitude(catalog, min_stars=8, seed=args.att_seed)
    cfg = NoiseConfig(
        sigma_centroid_arcsec=args.centroid,
        sigma_mag=args.mag,
        n_spikes=args.spikes,
        p_missing=args.missing,
    )
    fig, ax, observed, truth = visualize_scene(catalog, q, cfg, seed=args.seed)

    out = Path(args.save)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"Kaydedildi: {out}  ({len(observed)} gözlem, "
          f"{len(truth.true_matches)} gerçek yıldız, "
          f"{len(observed) - len(truth.true_matches)} spike)")
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
