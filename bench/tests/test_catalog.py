"""Kabul testi 1: katalog (brief 01 §Kabul testleri)."""
import numpy as np


def test_catalog_size(catalog):
    # Mv<6'da makul N yıldız (~birkaç bin)
    assert 1000 < len(catalog) < 20000


def test_catalog_unit_vectors(catalog):
    v = catalog.vectors
    norms = np.linalg.norm(v, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-9)


def test_catalog_mag_limit(catalog):
    mags = np.array([s.mag for s in catalog.stars])
    assert mags.max() < 6.0


def test_catalog_by_id(catalog):
    star = catalog.stars[0]
    assert catalog.by_id(star.hip_id) is star
