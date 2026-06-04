"""Built-in domain templates (task 18.2).

Every shipped template must parse, validate, and generate — a broken starter is
worse than none. Also covers catalog integrity and the raw-text loader.
"""

from __future__ import annotations

import tempfile

import pytest

from datadoom.engine import generate, parse_spec
from datadoom.templates import (
    list_templates,
    load_template_body,
    load_template_text,
)


def test_catalog_ids_unique_and_nonempty() -> None:
    templates = list_templates()
    assert len(templates) >= 3
    ids = [t.id for t in templates]
    assert len(ids) == len(set(ids))
    for t in templates:
        assert t.id and t.name and t.domain and t.description


@pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.id)
def test_template_parses_validates_and_generates(template) -> None:
    body = load_template_body(template.id)
    spec = parse_spec(body)  # raises on invalid shape / cross-field
    with tempfile.TemporaryDirectory() as tmp:
        result = generate(spec, seed=1, out_dir=tmp)
    assert len(result.frame) == spec.rows
    # A latent (emit: false) feature must not appear in the shipped frame.
    for name, feat in spec.features.items():
        if getattr(feat, "emit", None) is False:
            assert name not in result.frame.columns


def test_load_template_text_is_raw_yaml() -> None:
    text = load_template_text("fraud-detection")
    assert "datadoom_version" in text and "causal" in text


def test_unknown_template_raises() -> None:
    with pytest.raises(KeyError):
        load_template_body("does-not-exist")
