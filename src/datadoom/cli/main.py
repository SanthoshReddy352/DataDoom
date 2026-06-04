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
from ..plugins import (
    PluginError,
    check_plugin,
    get_registry,
    load_plugins,
    scaffold_plugin,
)
from ..templates import get_template, list_templates, load_template_text
from ..version import __version__

app = typer.Typer(
    add_completion=False,
    help="DataDoom — reproducible synthetic data.",
    no_args_is_help=True,
)

plugin_app = typer.Typer(
    help="Author and inspect DataDoom plugins (distributions, fns, failures, …).",
    no_args_is_help=True,
)
app.add_typer(plugin_app, name="plugin")

template_app = typer.Typer(
    help="Browse and start from built-in domain templates.",
    no_args_is_help=True,
)
app.add_typer(template_app, name="template")


@app.command()
def version() -> None:
    """Print the installed DataDoom version."""
    typer.echo(__version__)


@app.command(name="spec-reference")
def spec_reference(
    out: Path = typer.Option(None, "--out", help="Write to a file instead of stdout"),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Indent the JSON"),
) -> None:
    """Emit the machine-readable spec capabilities manifest (for AI/tooling).

    Lists every distribution, structural function, failure mode, difficulty tier,
    feature type, exporter, and validation rule a spec accepts — built from the
    live registries, so installed plugins are included. Feed it to an LLM/agent so
    it can author a valid ``*.datadoom.yaml`` without guessing.
    """
    load_plugins()  # so plugin-registered capabilities appear in the manifest
    from ..engine.reference import build_capabilities

    payload = json.dumps(build_capabilities(), indent=2 if pretty else None, sort_keys=False)
    if out is not None:
        out.write_text(payload + "\n", encoding="utf-8")
        typer.secho(f"wrote spec reference → {out}", fg=typer.colors.GREEN)
    else:
        typer.echo(payload)


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

    # 0.0.0.0 / :: are bind-all addresses, not browsable URLs — show a link the
    # user can actually click (e.g. inside Docker, where we bind 0.0.0.0).
    browse_host = "localhost" if bind_host in ("0.0.0.0", "::", "[::]") else bind_host
    typer.secho(
        f"DataDoom — open the web Canvas at http://{browse_host}:{bind_port}",
        fg=typer.colors.GREEN,
        bold=True,
    )
    typer.secho(
        f"  (bound to {bind_host}:{bind_port} · data: {cfg.home} · Ctrl+C to stop)",
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
    load_plugins()
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
    load_plugins()
    try:
        spec = load_spec(str(spec_path))
        result = generate(spec, seed=seed, out_dir=out)
    except DataDoomError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    comp = result.compliance
    applicable = sum(1 for f in comp.features if f.applicable)
    na = len(comp.features) - applicable
    suffix = f" ({applicable} assessed" + (f", {na} n/a" if na else "") + ")" if comp.features else ""
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
    load_plugins()
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


@plugin_app.command("list")
def plugin_list() -> None:
    """List every registered capability — core built-ins and discovered plugins."""
    load_plugins()
    records = get_registry().records()
    width = max((len(r.name) for r in records), default=4)
    for r in records:
        tag = "core" if r.builtin else r.source
        ver = f"  v{r.version}" if r.version else ""
        typer.echo(f"{r.kind:<14} {r.name:<{width}}  [{tag}]{ver}")
    typer.secho(f"{len(records)} capabilities", fg=typer.colors.GREEN)


@plugin_app.command("new")
def plugin_new(
    kind: str = typer.Argument(
        ..., help="distribution | structural_fn | failure_mode | exporter | probe_model"
    ),
    name: str = typer.Argument(..., help="Capability name, a lowercase identifier (e.g. weibull)"),
    dir: Path = typer.Option(Path("."), "--dir", help="Where to create the package"),
) -> None:
    """Scaffold a ready-to-publish ``datadoom-plugin-*`` package."""
    try:
        root = scaffold_plugin(kind, name, dir)
    except PluginError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.secho(f"created {root}", fg=typer.colors.GREEN)
    typer.echo("next:  pip install -e .  &&  datadoom plugin check .")


@plugin_app.command("check")
def plugin_check(
    target: Path = typer.Argument(..., help="A plugin .py file, package directory, or module"),
) -> None:
    """Run the plugin contract checks (interface, schema, determinism, RNG hygiene)."""
    try:
        reports = check_plugin(target)
    except PluginError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    ok = True
    for report in reports:
        typer.echo(report.summary())
        ok = ok and report.ok
    if ok:
        typer.secho(f"OK  {len(reports)} plugin(s) pass the contract", fg=typer.colors.GREEN)
    else:
        typer.secho("FAILED  one or more contract checks failed", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@template_app.command("list")
def template_list(
    level: str = typer.Option(
        "all",
        "--level",
        help="Filter by level: all | hackathon | starter.",
    ),
) -> None:
    """List the built-in domain templates."""
    templates = list_templates()
    if level != "all":
        templates = [t for t in templates if t.level == level]
    width = max((len(t.id) for t in templates), default=4)
    for t in templates:
        tag = " [hackathon]" if t.level == "hackathon" else ""
        typer.echo(f"{t.id:<{width}}  {t.domain:<15} {t.name}{tag}")
    typer.secho(f"{len(templates)} templates", fg=typer.colors.GREEN)


@template_app.command("show")
def template_show(
    template_id: str = typer.Argument(..., help="Template id (see `datadoom template list`)"),
) -> None:
    """Print a template's spec YAML to stdout."""
    try:
        typer.echo(load_template_text(template_id))
    except KeyError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@template_app.command("use")
def template_use(
    template_id: str = typer.Argument(..., help="Template id (see `datadoom template list`)"),
    out: Path = typer.Option(..., "--out", help="Where to write the spec (e.g. my.datadoom.yaml)"),
) -> None:
    """Write a template's spec to a file so you can edit and `datadoom run` it."""
    if get_template(template_id) is None:
        typer.secho(f"ERROR: unknown template {template_id!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    out.write_text(load_template_text(template_id), encoding="utf-8")
    typer.secho(f"wrote {out}", fg=typer.colors.GREEN)
    typer.echo(f"next:  datadoom run {out} --seed 1 --out .tmp_run")


def _recorded_checksum(run_dir: Path) -> str:
    meta_path = run_dir / "metadata.json"
    if not meta_path.exists():
        raise DataDoomError(f"no metadata.json in {run_dir}")  # noqa: TRY003
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta["determinism"]["artifact_checksums"]["data.csv"]


if __name__ == "__main__":
    app()
