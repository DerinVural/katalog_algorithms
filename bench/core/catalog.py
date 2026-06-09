"""Hipparcos katalog ingest (KAT-01).

- Vizier I/239/hip_main, Vmag < mag_limit.
- RA/Dec (ICRS, J2000) -> birim vektör.
- Proper motion v1'de KAPALI (J2000 konumları doğrudan).
- Sonuç yerel .npz olarak cache'lenir (tekrar sorgu/ağ gerektirmez).
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from .interfaces import Catalog, CatalogStar
from .sensor import MAG_LIMIT

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HIP_CATALOG = "I/239/hip_main"


def radec_to_unit(ra_deg: np.ndarray, dec_deg: np.ndarray) -> np.ndarray:
    """(RA, Dec) derece -> (N, 3) birim vektör (ICRS).

    x = cos(dec) cos(ra), y = cos(dec) sin(ra), z = sin(dec)
    """
    ra = np.radians(np.asarray(ra_deg, dtype=float))
    dec = np.radians(np.asarray(dec_deg, dtype=float))
    cd = np.cos(dec)
    return np.stack([cd * np.cos(ra), cd * np.sin(ra), np.sin(dec)], axis=-1)


def _cache_path(mag_limit: float) -> Path:
    return DATA_DIR / f"hipparcos_mv{mag_limit:g}.npz"


def _fetch_from_vizier(mag_limit: float) -> dict[str, np.ndarray]:
    """Vizier'den Hipparcos'u çek (HIP, RAICRS, DEICRS, Vmag)."""
    from astroquery.vizier import Vizier

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        v = Vizier(
            columns=["HIP", "RAICRS", "DEICRS", "Vmag"],
            column_filters={"Vmag": f"<{mag_limit}"},
        )
        v.ROW_LIMIT = -1
        result = v.query_constraints(catalog=HIP_CATALOG)

    if not result:
        raise RuntimeError("Vizier Hipparcos sorgusu boş döndü.")
    t = result[0]
    # masked / eksik satırları at
    mask = ~(t["RAICRS"].mask | t["DEICRS"].mask | t["Vmag"].mask) \
        if hasattr(t["Vmag"], "mask") else np.ones(len(t), dtype=bool)
    return {
        "hip": np.asarray(t["HIP"][mask], dtype=np.int64),
        "ra": np.asarray(t["RAICRS"][mask], dtype=float),
        "dec": np.asarray(t["DEICRS"][mask], dtype=float),
        "vmag": np.asarray(t["Vmag"][mask], dtype=float),
    }


def load_catalog(
    mag_limit: float = MAG_LIMIT,
    use_cache: bool = True,
    refresh: bool = False,
) -> Catalog:
    """Hipparcos kataloğunu yükle (cache -> yoksa Vizier -> cache yaz)."""
    cache = _cache_path(mag_limit)
    if use_cache and not refresh and cache.exists():
        d = np.load(cache)
        cols = {k: d[k] for k in ("hip", "ra", "dec", "vmag")}
    else:
        cols = _fetch_from_vizier(mag_limit)
        if use_cache:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            np.savez(cache, **cols)

    units = radec_to_unit(cols["ra"], cols["dec"])
    stars = [
        CatalogStar(hip_id=int(h), u_inertial=units[i], mag=float(m))
        for i, (h, m) in enumerate(zip(cols["hip"], cols["vmag"]))
    ]
    return Catalog(stars=stars)
