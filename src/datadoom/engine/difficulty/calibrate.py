"""Adaptive difficulty calibration: bisection on the dial (05 §5.2, 17 step 15).

The loop measures the probe metric μ on the realized frame and turns the single
:class:`DifficultyDial` until μ lands in the target band ``[a, b]`` (from an
explicit band or a named tier). Because μ(d) is monotone non-increasing in the
dial, the search is a clean bisection:

    generate → evaluate μ
    μ ∈ [a, b]   → success
    μ > b        → too easy  → turn the dial up (more noise)
    μ < a        → too hard  → turn the dial down

Honest failure (invariant #3): if even the pristine data is already below the
band (no easing knob exists) or the maximum dial can't push μ down into the band
(signal too strong for the available knobs), the loop returns the *closest*
achieved point and flags ``band_met = False`` with a plain-language note — never
a silent miss.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

from .knobs import ACTIVE_KNOBS, DIAL_MAX, DifficultyDial
from .probes import PROBES, ProbeResult, evaluate

if TYPE_CHECKING:
    from ..pipeline import RunContext

# Named tiers → validated AUROC bands for binary classification (05 §5.3). These
# are calibration *targets*, kept honest by the calibration test in tests/.
TIER_BANDS: dict[str, tuple[float, float]] = {
    "beginner": (0.90, 0.99),
    "intermediate": (0.80, 0.90),
    "advanced": (0.72, 0.80),
    "kaggle": (0.62, 0.72),
}


@dataclass
class Target:
    task: str
    metric: str
    band: tuple[float, float]
    tier: str | None = None


@dataclass
class DifficultyResult:
    target: dict[str, Any]
    achieved_metric: float
    metric_name: str
    probe: str
    iterations: int
    band_met: bool
    dial: float
    feature_noise: float
    label_flip: float
    knobs_requested: list[str]
    knobs_active: list[str]
    reference: dict[str, Any]
    trace: list[dict[str, float]]
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "achieved_metric": self.achieved_metric,
            "metric_name": self.metric_name,
            "probe": self.probe,
            "iterations": self.iterations,
            "band_met": self.band_met,
            "dial": self.dial,
            "feature_noise": self.feature_noise,
            "label_flip": self.label_flip,
            "knobs_requested": self.knobs_requested,
            "knobs_active": self.knobs_active,
            "reference": self.reference,
            "trace": self.trace,
            "note": self.note,
        }


@dataclass
class _Best:
    """Tracks the closest-to-band point seen, for honest fallback reporting."""

    dial: float = 0.0
    result: ProbeResult | None = None
    distance: float = float("inf")

    def offer(self, dial: float, result: ProbeResult, band: tuple[float, float]) -> None:
        a, b = band
        m = result.metric
        dist = 0.0 if a <= m <= b else min(abs(m - a), abs(m - b))
        if dist < self.distance:
            self.distance, self.dial, self.result = dist, dial, result


def resolve_target(target: str | dict[str, Any]) -> Target:
    """Map a tier name or explicit-band dict to a concrete :class:`Target`."""
    if isinstance(target, str):
        band = TIER_BANDS[target]  # validated upstream
        return Target(task="classification", metric="auroc", band=band, tier=target)
    band_raw = target["band"]
    band = (float(band_raw[0]), float(band_raw[1]))
    return Target(
        task=str(target.get("task", "classification")),
        metric=str(target.get("metric", "auroc")),
        band=band,
        tier=None,
    )


def calibrate_difficulty(
    ctx: RunContext, base_frame: pd.DataFrame
) -> tuple[DifficultyResult, pd.DataFrame]:
    """Run the adaptive loop; return the report + the calibrated frame to ship."""
    spec = ctx.spec
    assert spec.difficulty is not None
    cfg = spec.difficulty
    target = resolve_target(cfg.target)
    band = target.band
    probe = PROBES[cfg.probe]

    requested = list(cfg.knobs)
    active = [k for k in requested if k in ACTIVE_KNOBS]
    dial_obj = DifficultyDial(base_frame, cfg.label, ctx.rng, active, ctx.used_namespaces)

    # Probe seeds are derived from the run's RNG so the split/estimator are
    # reproducible without touching the data namespaces.
    split_seed = int(ctx.rng.probe("split").integers(0, 2**31 - 1))
    est_seed = int(ctx.rng.probe("estimator").integers(0, 2**31 - 1))
    ctx.used_namespaces.extend(["probe:split", "probe:estimator"])

    trace: list[dict[str, float]] = []

    def mu(dial: float) -> tuple[ProbeResult, pd.DataFrame]:
        frame, _ = dial_obj.realize(dial)
        result = evaluate(probe, frame, cfg.label, split_seed=split_seed, est_seed=est_seed)
        trace.append({"dial": round(dial, 6), "metric": round(result.metric, 6)})
        return result, frame

    a, b = band
    best = _Best()

    r0, frame0 = mu(0.0)
    best.offer(0.0, r0, band)
    note: str | None = None
    band_met = False
    final_dial = 0.0
    final_result = r0
    final_frame = frame0

    if r0.metric <= b:
        # Pristine data is already at or below the upper bound.
        final_dial, final_result, final_frame = 0.0, r0, frame0
        if r0.metric >= a:
            band_met = True
        else:
            note = (
                "clean data is already harder than the target band; v0.1 has no "
                "easing knob, so the pristine dataset is shipped as-is"
            )
    else:
        # Too easy → push the dial up. Probe the hard end to bracket the root.
        rmax, framemax = mu(DIAL_MAX)
        best.offer(DIAL_MAX, rmax, band)
        if rmax.metric > b:
            note = (
                "maximum difficulty is still too easy for the target band; the "
                "label is too separable for the active knobs to obscure"
            )
            final_dial, final_result, final_frame = DIAL_MAX, rmax, framemax
        elif a <= rmax.metric <= b:
            band_met = True
            final_dial, final_result, final_frame = DIAL_MAX, rmax, framemax
        else:
            # Bracketed: μ(0) > b and μ(DIAL_MAX) < a. Bisect for the band.
            lo, hi = 0.0, DIAL_MAX
            for _ in range(cfg.max_iters):
                mid = (lo + hi) / 2.0
                rmid, framemid = mu(mid)
                best.offer(mid, rmid, band)
                if a <= rmid.metric <= b:
                    band_met = True
                    final_dial, final_result, final_frame = mid, rmid, framemid
                    break
                if rmid.metric > b:
                    lo = mid  # still too easy → harder
                else:
                    hi = mid  # too hard → easier
            else:
                # Exhausted iterations without landing in the band: ship closest.
                final_dial = best.dial
                final_result = best.result if best.result is not None else r0
                final_frame, _ = dial_obj.realize(final_dial)
                note = (
                    f"target band not reached within max_iters={cfg.max_iters}; "
                    "shipping the closest achieved difficulty"
                )

    state = dial_obj.realize(final_dial)[1]
    reference = {
        "linear_separability": final_result.linear_separability,
        "class_balance": final_result.class_balance,
        "noise_to_signal": dial_obj.noise_to_signal(state.feature_noise),
        "probe_features": final_result.n_features,
        "rows": dial_obj.n,
    }
    result = DifficultyResult(
        target={
            "tier": target.tier,
            "task": target.task,
            "metric": target.metric,
            "band": [a, b],
        },
        achieved_metric=final_result.metric,
        metric_name=final_result.metric_name,
        probe=cfg.probe,
        iterations=len(trace),
        band_met=band_met,
        dial=final_dial,
        feature_noise=state.feature_noise,
        label_flip=state.label_flip,
        knobs_requested=requested,
        knobs_active=active,
        reference=reference,
        trace=trace,
        note=note,
    )
    return result, final_frame
