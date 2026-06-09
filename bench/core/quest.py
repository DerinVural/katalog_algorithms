"""Attitude çözümü — Davenport q-method (Wahba problemi).

Quaternion konvansiyonu: scalar-last [x, y, z, w] (scipy ile uyumlu).
Attitude R, inertial -> body eşlemesidir:  u_body = R @ u_inertial.

q-method: K matrisinin en büyük özdeğerine ait özvektör optimal attitude'u
verir (Davenport 1968; Shuster & Oh 1981 QUEST aynı problemi çözer). Özvektör
işaret belirsizliği (q ~ -q) ve aktif/pasif çerçeve konvansiyonu, eşleşmelere
karşı Wahba kaybı minimize edilerek deterministik olarak çözülür.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


def quat_to_matrix(q: np.ndarray) -> np.ndarray:
    """[x,y,z,w] -> (3,3) rotasyon matrisi (inertial->body)."""
    return Rotation.from_quat(np.asarray(q, dtype=float)).as_matrix()


def rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """q ile v(ler)i döndür: u_body = R(q) @ v_inertial. (N,3) veya (3,)."""
    return Rotation.from_quat(np.asarray(q, dtype=float)).apply(np.asarray(v, dtype=float))


def random_quat(rng: np.random.Generator) -> np.ndarray:
    """Üniform rastgele birim quaternion [x,y,z,w] (Shoemake)."""
    u1, u2, u3 = rng.random(3)
    a = np.sqrt(1.0 - u1)
    b = np.sqrt(u1)
    return np.array([
        a * np.sin(2 * np.pi * u2),
        a * np.cos(2 * np.pi * u2),
        b * np.sin(2 * np.pi * u3),
        b * np.cos(2 * np.pi * u3),
    ])


def _wahba_loss(A: np.ndarray, body: np.ndarray, inertial: np.ndarray,
                w: np.ndarray) -> float:
    resid = body - inertial @ A.T          # b_i - A r_i
    return float(np.sum(w * np.sum(resid ** 2, axis=1)))


def davenport_q_method(
    body: np.ndarray,
    inertial: np.ndarray,
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """Eşleşen body<->inertial çiftlerinden optimal quaternion [x,y,z,w].

    body, inertial: (N, 3) birim vektörler (b_i ≈ A r_i).
    """
    body = np.asarray(body, dtype=float)
    inertial = np.asarray(inertial, dtype=float)
    n = body.shape[0]
    if n < 2:
        raise ValueError("q-method en az 2 eşleşme gerektirir.")
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)

    B = (w[:, None] * body).T @ inertial         # Σ w_i b_i r_iᵀ  (3,3)
    S = B + B.T
    sigma = np.trace(B)
    Z = np.array([B[1, 2] - B[2, 1], B[2, 0] - B[0, 2], B[0, 1] - B[1, 0]])

    K = np.zeros((4, 4))
    K[:3, :3] = S - sigma * np.eye(3)
    K[:3, 3] = Z
    K[3, :3] = Z
    K[3, 3] = sigma

    eigvals, eigvecs = np.linalg.eigh(K)
    q = eigvecs[:, np.argmax(eigvals)]            # [x,y,z,w] (max özdeğer)

    # Özvektör işareti / çerçeve konvansiyonunu Wahba kaybıyla çöz:
    # R(q) ve R(q)ᵀ adaylarından b=A r'ye en uygun olanı seç.
    R = Rotation.from_quat(q).as_matrix()
    candidates = [R, R.T]
    losses = [_wahba_loss(A, body, inertial, w) for A in candidates]
    A_best = candidates[int(np.argmin(losses))]
    return Rotation.from_matrix(A_best).as_quat()


def quest(
    cands,
    catalog,
    observed,
    weights: np.ndarray | None = None,
) -> np.ndarray | None:
    """Bench koşucusunun çağırdığı sarmalayıcı.

    cands: list[CandidateMatch] (obs_id -> hip_id)
    catalog: Catalog (hip_id -> inertial)
    observed: Sequence[BodyVector] (obs_id -> body)
    En az 2 eşleşme yoksa None döner (attitude çözülemedi).
    """
    by_obs = {o.obs_id: o for o in observed}
    body, inertial = [], []
    for c in cands:
        o = by_obs.get(c.obs_id)
        if o is None:
            continue
        try:
            star = catalog.by_id(c.hip_id)
        except KeyError:
            continue
        body.append(o.u_body)
        inertial.append(star.u_inertial)

    if len(body) < 2:
        return None
    return davenport_q_method(np.array(body), np.array(inertial), weights)
