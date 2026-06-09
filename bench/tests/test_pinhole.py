"""Kabul testi 2: pinhole roundtrip < 1e-9 px (brief 01)."""
import numpy as np

from bench.core.pinhole import body_to_focal, focal_to_body
from bench.core.sensor import SENSOR


def test_roundtrip_focal_body_focal():
    rng = np.random.default_rng(0)
    half = SENSOR.npix / 2.0
    pts = rng.uniform(-half, half, size=(500, 2))
    u = focal_to_body(pts[:, 0], pts[:, 1])
    back = body_to_focal(u)
    err = np.abs(back - pts).max()
    assert err < 1e-9, f"roundtrip hatası {err} px"


def test_boresight_center():
    # merkez piksel -> boresight (+z)
    u = focal_to_body(0.0, 0.0)
    assert np.allclose(u, [0, 0, 1], atol=1e-12)
