"""In-process generation worker (03 §3.3, 17 step 8).

A run is submitted to a thread pool; the worker loads the immutable spec snapshot
from ``store``, drives the single ``engine.pipeline`` entry point, streams
progress to the :class:`EventHub`, persists artifacts + report, and flips the
``GenerationRun`` (and its dataset) status. Cancellation is cooperative — checked
at each pipeline stage boundary by :class:`HubProgressEmitter`.

This is the only code path that turns a queued run into artifacts; the CLI and
``datadoom.generate()`` share the same engine underneath, never a fork of it.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from datadoom.engine import generate, parse_spec
from datadoom.store import (
    ArtifactRepository,
    ArtifactStore,
    Database,
    DatasetRepository,
    ReportRepository,
    RunRepository,
    SpecRow,
    utcnow_iso,
)

from .progress import EventHub, HubProgressEmitter, RunCancelled


class WorkerPool:
    def __init__(
        self,
        db: Database,
        artifacts: ArtifactStore,
        hub: EventHub,
        package_version: str,
        max_workers: int = 2,
    ) -> None:
        self.db = db
        self.artifacts = artifacts
        self.hub = hub
        self.package_version = package_version
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dd-run")

    def submit(self, run_id: str) -> None:
        """Schedule a queued run for execution (returns immediately)."""
        self._pool.submit(self._execute, run_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    # --- execution ----------------------------------------------------------------
    def _execute(self, run_id: str) -> None:
        try:
            self._run_pipeline(run_id)
        except RunCancelled:
            self._mark_cancelled(run_id)
        except Exception as exc:  # noqa: BLE001 — persist any failure, never crash the pool
            self._mark_failed(run_id, exc)

    def _run_pipeline(self, run_id: str) -> None:
        # Load run + spec; flip to running.
        with self.db.session() as s:
            run = RunRepository(s).get(run_id)
            if run is None:
                return
            if self.hub.is_cancelled(run_id):
                raise RunCancelled("queued")
            spec_row = s.get(SpecRow, run.spec_id)
            assert spec_row is not None
            spec_body = dict(spec_row.body)
            dataset_id = run.dataset_id
            seed = run.seed
            run.status = "running"
            run.stage = "intake"
            run.started_at = utcnow_iso()
            ds = DatasetRepository(s).get(dataset_id)
            if ds is not None:
                ds.status = "running"
                ds.updated_at = utcnow_iso()

        spec = parse_spec(spec_body)
        out_dir: Path = self.artifacts.run_dir(dataset_id, run_id)
        emitter = HubProgressEmitter(self.hub, run_id)

        result = generate(spec, seed=seed, out_dir=out_dir, progress=emitter)
        emitter.finish()

        # Persist artifacts + report + final status (one transaction).
        with self.db.session() as s:
            arts = ArtifactRepository(s)
            for art in result.artifacts:
                abs_path = out_dir / art.path
                arts.add(
                    run_id=run_id,
                    version="clean",
                    fmt=art.format,
                    storage_uri=self.artifacts.to_uri(abs_path),
                    checksum_sha256=art.checksum_sha256,
                    size_bytes=art.size_bytes,
                    split="full",
                )
            report = ReportRepository(s).upsert(run_id, result.report.to_dict())
            run = RunRepository(s).get(run_id)
            assert run is not None
            run.status = "completed"
            run.stage = "packaging"
            run.progress_pct = 100
            run.finished_at = utcnow_iso()
            run.metrics = {"compliance_score": result.compliance.score}
            ds = DatasetRepository(s).get(dataset_id)
            if ds is not None:
                ds.status = "completed"
                ds.latest_run_id = run_id
                ds.updated_at = utcnow_iso()
            report_id = report.report_id

        self.hub.publish(
            run_id,
            {
                "type": "completed",
                "run_id": run_id,
                "compliance_score": result.compliance.score,
                "report_id": report_id,
            },
        )

    # --- terminal states ----------------------------------------------------------
    def _mark_cancelled(self, run_id: str) -> None:
        with self.db.session() as s:
            run = RunRepository(s).get(run_id)
            if run is not None:
                run.status = "cancelled"
                run.finished_at = utcnow_iso()
                ds = DatasetRepository(s).get(run.dataset_id)
                if ds is not None and ds.status == "running":
                    ds.status = "draft"
                    ds.updated_at = utcnow_iso()
        self.hub.publish(run_id, {"type": "cancelled", "run_id": run_id})

    def _mark_failed(self, run_id: str, exc: Exception) -> None:
        stage = "unknown"
        tb = traceback.format_exc()
        with self.db.session() as s:
            run = RunRepository(s).get(run_id)
            if run is not None:
                stage = run.stage or "unknown"
                run.status = "failed"
                run.error = {"message": str(exc), "traceback": tb, "stage": stage}
                run.finished_at = utcnow_iso()
                ds = DatasetRepository(s).get(run.dataset_id)
                if ds is not None:
                    ds.status = "failed"
                    ds.updated_at = utcnow_iso()
        self.hub.publish(
            run_id,
            {"type": "failed", "stage": stage, "message": str(exc), "traceback": tb},
        )
