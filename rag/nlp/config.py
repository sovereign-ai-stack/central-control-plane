"""
Persian NLP configuration.

Defaults are deliberately conservative: the layer is **disabled**, so behaviour
is byte-identical to the pre-Phase-5 system until the benchmark justifies
turning it on. Morphology has its own switch beneath that, because normalization
improvements and morphological reduction carry very different risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rag.nlp.errors import NlpConfigurationError
from rag.nlp.morphology import MIN_STEM_LENGTH, MorphologyRules
from rag.nlp.normalizer import NORMALIZATION_VERSION_V2

NLP_PIPELINE_VERSION = "fa-nlp-v1"


@dataclass(frozen=True, slots=True)
class MorphologyConfig:
    enabled: bool = False
    backend: str = "rule_based"
    plural: bool = True
    possessive: bool = True
    comparative: bool = True
    verbs: bool = True
    min_stem_length: int = MIN_STEM_LENGTH

    def to_rules(self) -> MorphologyRules:
        return MorphologyRules(
            plural=self.plural,
            possessive=self.possessive,
            comparative=self.comparative,
            verbs=self.verbs,
            min_stem_length=self.min_stem_length,
        )


@dataclass(frozen=True, slots=True)
class NlpConfig:
    enabled: bool = False
    normalization_version: str = NORMALIZATION_VERSION_V2
    fold_digits: bool = False
    morphology: MorphologyConfig = field(default_factory=MorphologyConfig)

    @property
    def pipeline_version(self) -> str:
        """Version stamp persisted on chunks, so reprocessing is detectable."""
        suffix = "morph" if self.morphology.enabled else "nomorph"
        return f"{NLP_PIPELINE_VERSION}+{self.normalization_version}+{suffix}"


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_nlp_config(path: Path | None = None) -> NlpConfig:
    config_path = path or _repo_root() / "config" / "nlp.yaml"
    if not config_path.exists():
        return NlpConfig()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return NlpConfig()
    block = raw.get("nlp", raw)
    if not isinstance(block, dict):
        return NlpConfig()
    return _from_mapping(block)


def _from_mapping(block: dict[str, Any]) -> NlpConfig:
    morphology_raw = block.get("morphology", {})
    if not isinstance(morphology_raw, dict):
        morphology_raw = {}

    version = str(block.get("normalization_version", NORMALIZATION_VERSION_V2))
    if version != NORMALIZATION_VERSION_V2:
        raise NlpConfigurationError(
            f"unsupported normalization version {version!r}; "
            f"the NLP layer implements {NORMALIZATION_VERSION_V2}"
        )

    morphology = MorphologyConfig(
        enabled=bool(morphology_raw.get("enabled", False)),
        backend=str(morphology_raw.get("backend", "rule_based")),
        plural=bool(morphology_raw.get("plural", True)),
        possessive=bool(morphology_raw.get("possessive", True)),
        comparative=bool(morphology_raw.get("comparative", True)),
        verbs=bool(morphology_raw.get("verbs", True)),
        min_stem_length=int(morphology_raw.get("min_stem_length", MIN_STEM_LENGTH)),
    )
    if morphology.min_stem_length < 1:
        raise NlpConfigurationError("min_stem_length must be at least 1")

    return NlpConfig(
        enabled=bool(block.get("enabled", False)),
        normalization_version=version,
        fold_digits=bool(block.get("fold_digits", False)),
        morphology=morphology,
    )
