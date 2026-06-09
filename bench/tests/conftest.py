"""Ortak test fixture'ları."""
from __future__ import annotations

import numpy as np
import pytest

from bench.core.catalog import load_catalog
from bench.core.quest import random_quat, rotate
from bench.core.sensor import SENSOR


@pytest.fixture(scope="session")
def catalog():
    """Hipparcos Mv<6 — oturum başına bir kez yüklenir (cache'lenir)."""
    return load_catalog()


def count_visible(catalog, q) -> int:
    u = rotate(q, catalog.vectors)
    cos_lim = np.cos(SENSOR.fov_radius_rad)
    return int(np.sum((u[:, 2] > 0) & (u[:, 2] >= cos_lim)))


def find_rich_attitude(catalog, min_stars: int = 8, seed: int = 0):
    """FOV'da en az `min_stars` yıldız gösteren bir attitude bul."""
    rng = np.random.default_rng(seed)
    for _ in range(2000):
        q = random_quat(rng)
        if count_visible(catalog, q) >= min_stars:
            return q
    raise RuntimeError(f"{min_stars} yıldızlı attitude bulunamadı.")


@pytest.fixture(scope="session")
def rich_attitude(catalog):
    return find_rich_attitude(catalog, min_stars=8, seed=0)
