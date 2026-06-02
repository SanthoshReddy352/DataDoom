"""DataDoom CLI — launcher + headless automation (17 step 6).

In P0 the CLI is the only surface: ``run``, ``validate`` and ``verify`` exercise
the deterministic core. The web Canvas (``datadoom`` with no subcommand) arrives
in P1.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer

from ..engine import generate, load_spec
from ..engine.errors import DataDoomError, ReproducibilityError
from ..engine.export.checksums import sha256_file
from ..version import __version__

app = typer.Typer(
    add_completion=False,
    help="DataDoom — reproducible synthetic data.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the installed DataDoom version."""
    typer.echo(__version__)


@app.command()
def serve(
    host: str = typer.Option(None, "--host", help="Bind host (default 127.0.0.1)"),
    port: int = typer.Option(None, "--port", help="Bind port (default 8000)"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload (development)"),
) -> None:
    """Launch the local web server (REST + WebSocket) and the bundled Canvas UI.

    Requires the server extra: ``pip install datadoom[server]``.
    """
    try:
        import uvicorn

        from ..api import create_app
        from ..config import load_config
    except ImportError as exc:  # pragma: no cover - only without the server extra
        typer.secho(
            "The web server needs extra deps. Install with: pip install 'datadoom[server]'",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from exc

    cfg = load_config()
    bind_host = host or cfg.host
    bind_port = port or cfg.port
    cfg.ensure_dirs()

    typer.secho(
        f"DataDoom serving on http://{bind_host}:{bind_port}  (data: {cfg.home})",
        fg=typer.colors.GREEN,
    )
    if reload:
        # Reload needs an import string; create_app is the factory.
        uvicorn.run(
            "datadoom.api:create_app", host=bind_host, port=bind_port, reload=True, factory=True
        )
    else:
        uvicorn.run(create_app(cfg), host=bind_host, port=bind_port)


@app.command()
def validate(spec_path: Path = typer.Argument(..., help="Path to a *.datadoom.yaml spec")) -> None:
    """Validate a spec file (shape + cross-field) without generating."""
    try:
        spec = load_spec(str(spec_path))
    except DataDoomError as exc:
        typer.secho(f"INVALID: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.secho(f"OK  spec_hash={spec.spec_hash()}", fg=typer.colors.GREEN)


@app.command()
def run(
    spec_path: Path = typer.Argument(..., help="Path to a *.datadoom.yaml spec"),
    seed: int = typer.Option(None, "--seed", help="Override/resolve the random seed"),
    out: Path = typer.Option(..., "--out", help="Output directory for artifacts"),
) -> None:
    """Generate a dataset from a spec and write CSV + metadata to --out."""
    try:
        spec = load_spec(str(spec_path))
        result = generate(spec, seed=seed, out_dir=out)
    except DataDoomError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    comp = result.compliance
    applicable = sum(1 for f in comp.features if f.applicable)
    na = len(comp.features) - applicable
    suffix = f" ({applicable} KS-assessed" + (f", {na} n/a" if na else "") + ")" if comp.features else ""
    typer.echo(f"spec_hash       {result.spec_hash}")
    typer.echo(f"seed            {result.seed}")
    typer.echo(f"rows            {len(result.frame)}")
    typer.echo(f"compliance      {comp.score:.3f}{suffix}")
    for art in result.artifacts:
        typer.echo(f"artifact        {art.path}  sha256={art.checksum_sha256[:16]}…")
    typer.secho(f"written to {out}", fg=typer.colors.GREEN)


@app.command()
def verify(
    spec_path: Path = typer.Argument(..., help="Path to a *.datadoom.yaml spec"),
    seed: int = typer.Option(..., "--seed", help="Seed to verify reproducibility for"),
    against: Path = typer.Option(
        None,
        "--against",
        help="An existing run dir to compare against; omit to self-check (run twice).",
    ),
) -> None:
    """Prove (spec_hash, seed) -> identical checksum.

    With --against, regenerate and compare to that bundle's recorded checksum.
    Without it, generate twice and assert the two checksums match.
    """
    try:
        spec = load_spec(str(spec_path))
        with tempfile.TemporaryDirectory() as tmp:
            fresh = generate(spec, seed=seed, out_dir=tmp)
            fresh_checksum = sha256_file(Path(tmp) / "data.csv")

            if against is not None:
                expected = _recorded_checksum(against)
                source = str(against)
            else:
                with tempfile.TemporaryDirectory() as tmp2:
                    generate(spec, seed=seed, out_dir=tmp2)
                    expected = sha256_file(Path(tmp2) / "data.csv")
                source = "second run"
    except DataDoomError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if fresh_checksum != expected:
        typer.secho(
            f"MISMATCH\n  this run: {fresh_checksum}\n  {source}: {expected}",
            fg=typer.colors.RED,
            err=True,
        )
        raise ReproducibilityError("checksum mismatch")  # noqa: TRY003
    typer.secho(
        f"OK  reproducible (spec_hash={fresh.spec_hash}, seed={seed})\n"
        f"    sha256={fresh_checksum}",
        fg=typer.colors.GREEN,
    )


def _recorded_checksum(run_dir: Path) -> str:
    meta_path = run_dir / "metadata.json"
    if not meta_path.exists():
        raise DataDoomError(f"no metadata.json in {run_dir}")  # noqa: TRY003
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta["determinism"]["artifact_checksums"]["data.csv"]


if __name__ == "__main__":
    app()
