# Brief 08 — Padgett Grid Algorithm

**Primary source:** Padgett, C. & Kreutz-Delgado, K., "A Grid Algorithm for Autonomous Star
Identification," *IEEE Trans. Aerospace and Electronic Systems*, Vol. 33, No. 1, Jan. 1997, pp. 202–213.
**Plugin:** `algorithms/padgett_grid.py`
**Role split:** PM (this brief, review, adversarial experiments, verdict) / Claude Code (implementation).
**Sensor profile:** CMV4000 — 2048×2048, 5.5 µm pitch, 14.7° horizontal FOV, ~43.7 mm focal length,
~25.8 arcsec/pixel, Mv ≤ 6 catalog.

---

## 0. Status & sequencing note

Numbered `08` per request. I cannot verify from my side that this slot is consistent with the
current repo state (my last confirmed brief ordering ended at the Samaan/NDSIA Phase 3 line). Confirm
the number against `docs/briefs/` before merge; renumber if it collides.

Grid is proposed as a **paradigm-orthogonal** entry to the benchmark. Every algorithm implemented so
far (Liebe, planar triangle, Quine, SLA, Pyramid, Samaan/NDSIA) matches **interstar angles**. Grid
matches a **spatial bit-signature** built from a rotation-normalized grid overlay. Putting it on the
same bench (shared catalog, scene simulator, pinhole model, QUEST/ESOQ solver, metrics) isolates the
question: *does spatial hashing buy anything over geometric angle-matching at this FOV/catalog density,
and where does it break?*

---

## 1. Benchmark rationale

What Grid contributes that the angle-family does not:

1. **A hashing baseline.** O(1)-ish signature lookup vs. the k-vector range search. The
   speed/robustness trade-off is different in kind, not degree.
2. **A fragility case study.** Grid's rotation invariance hangs entirely on one nearest-neighbor (NN)
   choice. This is a *single point of failure* the angle methods don't have. Measuring exactly how and
   when it fails is scientifically useful — it stress-tests our `no_solution` vs. `wrong_attitude`
   instrumentation harder than any angle method has.
3. **A completeness-sensitivity probe.** Grid encodes the *presence/absence* of neighbors as bits, so a
   single missing or extra star flips multiple bits at once. Angle methods only lose the affected
   angles. This makes Grid the natural algorithm for exercising catalog-completeness and spike axes.

---

## 2. Algorithm summary (faithful)

### 2.1 Signature construction (per reference star `s`)

1. **Neighbor set.** Collect all stars within angular `pattern_radius` (r_p) of `s` (in the tangent
   plane about `s`, or equivalently small-angle image plane).
2. **Nearest-neighbor orientation.** Select the closest neighbor `nn` whose separation exceeds
   `buffer_radius` (r_b). The buffer excludes noise-dominated near-coincident stars from setting the
   orientation. Vector `s → nn` defines the pattern's reference direction.
3. **Normalize.** Translate `s` to origin; rotate the frame so `nn` lies on the +x axis. This removes
   **roll (rotation about boresight)** — the source of Grid's rotation invariance.
4. **Grid overlay.** Superimpose a `grid_size × grid_size` (g×g) grid over the disc/square of radius
   r_p. Set bit = 1 for every cell containing at least one neighbor star; else 0. Flatten to a g²-bit
   vector — the **signature** of `s`.

### 2.2 Catalog database (built a priori)

For every catalog star, compute its signature under the same rules using cataloged neighbors within
r_p. Store as a bit matrix `N_catalog × g²`. This is the Grid analog of the k-vector table.

### 2.3 Matching (online)

For each observed reference star, build its signature and score against every catalog signature by
**matching-cell count** (equivalently, `g² − HammingDistance`). Best score above `match_threshold`
proposes an ID; runner-up margin gates confidence (see §5).

### 2.4 Correspondence output

Grid IDs stars **individually**. The plugin runs the per-star ID over all observed stars, then emits the
set of (observed_idx → catalog_idx) correspondences. Attitude is **not** solved inside the plugin — the
bench QUEST/ESOQ stage consumes the correspondences, identical to every other plugin's contract.

---

## 3. Interface contract

Same `StarIDAlgorithm` contract as existing plugins. No changes to the shared pipeline signature.

```python
class PadgettGrid(StarIDAlgorithm):
    def build(self, catalog, config) -> None:
        # precompute N_catalog × g² signature matrix; persist size for reporting
    def match(self, body_vectors, config) -> MatchResult:
        # returns correspondences + status ∈ {solved, no_solution}
        # NEVER fabricates an ID to avoid no_solution
```

`MatchResult` must carry the same `status` field used by the metrics layer so that the
`no_solution` / `wrong_attitude` split is computed downstream exactly as for the angle plugins.

---

## 4. Configuration parameters

| Param | Symbol | Default (starting point) | Rationale / tuning axis |
|---|---|---|---|
| `pattern_radius` | r_p | 6.0° | Must keep the full pattern disc inside a 14.7° FOV for typical reference-star placements. Larger → more discriminative, more edge truncation. |
| `buffer_radius` | r_b | 0.30° | NN noise guard. Roughly ≫ centroid error (~2.6″ ≈ 0.0007°); set well above to avoid near-tie NN selection. Key robustness knob. |
| `grid_size` | g | 40 | g² = 1600 bits/star. Cell angular size ≈ 2·r_p/g ≈ 0.30°. Trades bit-flip tolerance (coarse) vs. discriminative power (fine). |
| `match_threshold` | τ | tune | Min matching cells to accept. Set from the score histogram (true vs. random), targeting near-zero wrong_attitude. |
| `margin_threshold` | Δ | tune | Min (best − runner-up) score gap. Below Δ → ambiguous → `no_solution`. This is the primary safety gate (see §5). |
| `min_consensus` | c | 3 | Min mutually-consistent per-star IDs required before the frame is declared `solved`. |

All defaults are **starting points**, not the paper's values — the original grid/radius conventions must
be read off the primary source during implementation and reconciled here.

---

## 5. Native verification & the no_solution / wrong_attitude gate

Grid has **no built-in spike rejection** (unlike Pyramid's four-star confirmation). Safety therefore
lives entirely in the acceptance gates, and the brief makes them mandatory:

1. **Threshold gate.** Best score < τ → that reference star yields no ID.
2. **Margin gate.** (best − runner-up) < Δ → ambiguous → no ID for that star. This is the single most
   important gate; near-tie signatures are exactly the failure signature of a corrupted NN orientation.
3. **Consensus gate.** Fewer than `min_consensus` mutually geometrically-consistent per-star IDs →
   frame status = `no_solution`. Consistency = the candidate catalog stars reproduce the observed
   interstar angles within the shared angular tolerance (reuse the bench's angle check).

**Design intent:** Grid must *prefer `no_solution` over `wrong_attitude`*, matching the project-wide
safety philosophy. A frame that passes the consensus gate but still yields an attitude outside the
axis-separated error gates (cross-boresight 60″, roll 600″) is counted as `wrong_attitude` — the
outcome we are trying to drive to zero.

---

## 6. Ablation (shared RANSAC verifier)

Per the Phase-2+ mandate, report **two modes**:

- **Native:** threshold + margin + consensus gates as in §5.
- **Ablation:** replace the native gates with the shared RANSAC verifier used across the bench, feeding
  it the raw per-star candidate lists.

This isolates how much of Grid's robustness (or lack of it) comes from the signature quality vs. the
verification layer — the same decomposition we required for Pyramid.

---

## 7. Acceptance tests (theory-derived)

Each test is derived from a property of the algorithm, not from expected output alone.

**T1 — Rotation invariance (roll).** Render one star field, then re-render at a sweep of pure boresight
roll angles (0°→360°). By construction the NN alignment removes roll; signatures must be **identical**
(exact, up to grid-cell quantization at boundaries). *Pass:* signature Hamming distance across roll ≈ 0
except for a small boundary-flip floor. This is the direct analog of the planar-angle exact-invariance
test from Phase 3.

**T2 — Translation/pointing dependence.** Cross-boresight offset (δx, δy) changes which stars are in
FOV, so signatures *should* change. *Pass:* signatures vary under (δx, δy) but not under roll — proving
the invariance is specifically rotational, not a bug that ignores geometry.

**T3 — Signature determinism.** Same input → same signature, bit-for-bit, across repeated builds. Guards
against nondeterministic NN tie-breaking. *Pass:* zero variance; ties broken by a documented rule.

**T4 — Self-identification.** For a noise-free scene drawn directly from the catalog, every reference
star must self-identify (score = g²). *Pass:* 100% id_rate, zero wrong_attitude at zero noise.

**T5 — Database size accounting.** Reported signature DB size must equal `N_catalog × g² / 8` bytes
(± header). *Pass:* computed matches reported, included in the mandatory database-size column.

**T6 — Cell-size / boundary consistency.** Verify cell angular size ≈ 2·r_p/g and that a star nudged by
< half a cell does not flip its bit; nudged by > one cell does. Ties the noise model to the geometry.

---

## 8. Adversarial experiments

Run on the shared scene simulator; report both native and ablation modes.

**A1 — Spike sweep (the headline experiment).** Inject 0, 2, 4, …, 24 spikes (matching the Pyramid
sweep so results are directly comparable). Track `id_rate`, `no_solution`, `wrong_attitude` vs. spike
count. *Purpose:* quantify NN-fragility (H8a).

**A2 — Centroid-noise sweep.** σ = 0 → several px. Track id_rate degradation and locate the boundary-
flip onset. *Purpose:* H8c.

**A3 — Catalog-completeness mismatch.** Deliberately offset the scene magnitude limit vs. the catalog
magnitude limit so that boundary-magnitude stars are present-in-scene-but-absent-in-catalog (and vice
versa). Track bit-flip count and wrong_attitude. *Purpose:* H8d.

**A4 — Degenerate NN geometry.** Construct scenes with two near-equidistant NN candidates for the
reference star (separation just above r_b, Δ-separation below noise). *Purpose:* confirm the margin gate
converts these into `no_solution` rather than `wrong_attitude`.

**A5 — Head-to-head vs. Pyramid.** Same 1,000-frame random-attitude batch, matched spike/noise
conditions. Report the wrong_attitude/no_solution ratio side by side. This is the paradigm comparison
the brief exists to produce.

---

## 9. Falsifiable predictions (H8 family)

State up front so the experiments can refute them.

- **H8a — NN-fragility.** A single spike landing in the annulus (r_b, r_p) of a reference star *and*
  closer than the true NN corrupts that star's entire signature. Consequently Grid's
  wrong_attitude-vs-spike curve rises **steeper** than Pyramid's, and Grid's wrong_attitude/no_solution
  ratio at matched spike count is **worse**. *Falsifier:* Grid matches Pyramid's spike robustness ⇒ the
  NN single-point-of-failure model is wrong.

- **H8b — Roll invariance.** id_rate is **flat** under pure roll (T1/A-none) but **drops** under
  cross-boresight offset. Mirror image of the planar-angle invariance signature. *Falsifier:* id_rate
  moves under roll ⇒ NN normalization is broken.

- **H8c — Boundary bit-flip onset.** id_rate begins measurable degradation when centroid noise
  approaches **half the grid-cell angular size** (~0.15° at defaults). *Falsifier:* degradation onset
  far from cell-size/2 ⇒ noise model or cell geometry is misspecified.

- **H8d — Completeness sensitivity.** Grid's id_rate is **more** sensitive to magnitude-limit mismatch
  than the angle methods, because one missing/extra star flips several bits rather than corrupting a
  single angle. *Falsifier:* Grid degrades no faster than angle methods under A3.

---

## 10. Reporting requirements (mandatory)

- **Database size column.** Grid signature DB in MB, alongside Pyramid (1.59 MB), NDSIA (99.46 MB),
  Astrometry.net (~5 GB). Grid at defaults (N≈5000, g=40) ≈ **1.0 MB** — expected to sit near Pyramid;
  confirm empirically and report the exact figure with g and r_p noted.
- **Native + ablation** rows for every metric.
- **Axis-separated error gates** applied: cross-boresight 60″, roll 600″; roll reported separately
  because roll accuracy is structurally 6–16× worse (Liebe §V).
- **no_solution vs. wrong_attitude** split reported, never collapsed into a single "failure" number.
- Config block (r_p, r_b, g, τ, Δ, c) printed with every result set for reproducibility.

---

## 11. PM verdict criteria

On the first Claude Code push: fresh clone → independent review → run T1–T6 and A1–A5 → formal verdict.

- **Approved** — all acceptance tests pass; A-series runs clean; native prefers no_solution over
  wrong_attitude; database size reported; predictions H8a–H8d either confirmed or cleanly refuted with
  data.
- **Conditionally approved** — core tests pass but a gate (usually the margin gate Δ) needs tuning, or a
  prediction is untested. Ship with a tracked follow-up.
- **Revision required** — any of: roll invariance broken (T1 fail), silent `wrong_attitude` where a gate
  should have produced `no_solution` (A4 fail), or fabricated IDs bypassing the threshold gate.

---

## 12. Open questions / primary-source verification

Before implementation, read the 1997 paper and reconcile:

1. **Grid geometry** — square vs. circular pattern region, and exact cell indexing convention.
2. **NN definition** — whether the original uses strict nearest neighbor or a k-nearest scheme for the
   orientation reference, and the exact buffer treatment.
3. **Scoring** — whether the paper weights central vs. peripheral cells, or treats all g² cells equally
   (defaults here assume unweighted; revisit if the source differs).
4. **Reference-star selection** — brightest-first vs. all-stars; affects consensus voting cost.

Flag any divergence between the paper and this brief in the implementation PR so the faithful-vs-adapted
distinction stays explicit (same discipline applied to the NDSIA faithful arm).
