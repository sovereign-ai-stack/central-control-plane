"""
Rule-based Persian morphological normalization.

Purpose: make `کتاب‌ها`, `کتابهای`, and `کتاب` land on a comparable form so
semantic retrieval matches across inflections. It is a *retrieval aid*, not a
linguistic analyser, and it never replaces the stored text.

Over-stemming is the real risk in Persian light stemming — strip too eagerly and
distinct words collide (`مانی` -> `مان`, `کاری` -> `کار`). Three guards:

1. A minimum stem length, so short words are left alone.
2. A protected-word list for common words that merely look suffixed.
3. Per-rule toggles, so plural handling can ship without verb handling.

Every rule is deterministic and the result is idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag.nlp.normalizer import ZWNJ, strip_zwnj

MIN_STEM_LENGTH = 3

# Longest-first: "هایی" must be tried before "ها".
PLURAL_SUFFIXES = ("هایی", "های", "ها", "ات", "ان")
POSSESSIVE_SUFFIXES = ("مان", "تان", "شان", "ام", "ات", "اش")
COMPARATIVE_SUFFIXES = ("ترین", "تر")
VERB_PREFIXES = ("نمی", "می", "بر", "ب")
VERB_PERSON_SUFFIXES = ("یم", "ید", "ند", "م", "ی", "د", "ست", "ه")

# Words that end in suffix-looking letters but must never be stripped.
PROTECTED_WORDS = frozenset(
    {
        "تهران",
        "زبان",
        "جهان",
        "زمان",
        "مکان",
        "انسان",
        "سازمان",
        "خیابان",
        "استان",
        "درمان",
        "ایران",
        "مان",
        "شان",
        "همان",
        "چنان",
        "آنان",
        "امکان",
        "بیمار",
        "کارمند",
        "قانون",
        "بهتر",
        "دفتر",
        "دختر",
        "پدر",
        "مادر",
        "برادر",
        "خواهر",
        "کشور",
        "بند",
        "چند",
        "مانند",
        "هستند",
        "خرید",
        "امید",
        "کلید",
        "سفید",
        "شدید",
        "مفید",
        "جدید",
        "بازدید",
        "ماده",
        "پرونده",
        "نماینده",
        "آینده",
        "برنده",
        "راننده",
        "خوانده",
        "ساده",
        "استفاده",
        "اداره",
        "شماره",
        "درباره",
        "دوره",
        "نمره",
        "بیمه",
        "هزینه",
        "زمینه",
        "گزینه",
        "روزنامه",
        "نامه",
        "برنامه",
        "کارخانه",
        "خانه",
        "نمونه",
        "گونه",
        "همه",
        "کلمه",
        "جمله",
        "مرحله",
        "مسئله",
        "مقاله",
        "سالانه",
        "ماهانه",
        "روزانه",
        "محرمانه",
    }
)

# Present stem -> infinitive, for the irregular verbs that dominate Persian text.
PRESENT_STEM_INFINITIVE = {
    "رو": "رفتن",
    "کن": "کردن",
    "گو": "گفتن",
    "بین": "دیدن",
    "دار": "داشتن",
    "دان": "دانستن",
    "توان": "توانستن",
    "خواه": "خواستن",
    "آی": "آمدن",
    "شو": "شدن",
    "گیر": "گرفتن",
    "ده": "دادن",
    "زن": "زدن",
    "خور": "خوردن",
    "بر": "بردن",
    "آور": "آوردن",
    "یاب": "یافتن",
    "نویس": "نوشتن",
    "خوان": "خواندن",
    "باش": "بودن",
    "هست": "بودن",
    "است": "بودن",
}


@dataclass(frozen=True, slots=True)
class MorphologyRules:
    plural: bool = True
    possessive: bool = True
    comparative: bool = True
    verbs: bool = True
    min_stem_length: int = MIN_STEM_LENGTH


def _strip_suffix(token: str, suffixes: tuple[str, ...], min_stem: int) -> str | None:
    for suffix in suffixes:
        if not token.endswith(suffix):
            continue
        stem = token[: -len(suffix)]
        stem = stem.rstrip(ZWNJ)
        if len(stem) >= min_stem:
            return stem
    return None


def lemmatize_token(token: str, rules: MorphologyRules | None = None) -> str:
    """
    Reduce one token toward a comparable root form.

    Returns the token unchanged when no rule applies or a guard blocks it.
    """
    config = rules or MorphologyRules()
    if not token:
        return token

    joined = strip_zwnj(token)
    if joined in PROTECTED_WORDS or len(joined) <= config.min_stem_length:
        return joined

    if config.verbs:
        verb = _lemmatize_verb(joined, config)
        if verb is not None:
            return verb

    # Persian stacks suffixes stem + comparative + plural + possessive, so they
    # must be peeled outermost-first. Stripping plural first would consume the
    # "ان" of possessive "مان" and leave a bogus stem.
    current = joined
    if config.possessive:
        stem = _strip_suffix(current, POSSESSIVE_SUFFIXES, config.min_stem_length)
        if stem is not None and stem not in PROTECTED_WORDS:
            current = stem

    if config.plural:
        stem = _strip_suffix(current, PLURAL_SUFFIXES, config.min_stem_length)
        if stem is not None and stem not in PROTECTED_WORDS:
            current = stem

    if config.comparative:
        stem = _strip_suffix(current, COMPARATIVE_SUFFIXES, config.min_stem_length)
        if stem is not None and stem not in PROTECTED_WORDS:
            current = stem

    # A trailing ezafe/indefinite yeh survives plural stripping ("کتابهای" -> "کتابی").
    if config.plural and len(current) > config.min_stem_length and current.endswith("ی"):
        candidate = current[:-1]
        if len(candidate) >= config.min_stem_length and candidate not in PROTECTED_WORDS:
            current = candidate

    return current


def _lemmatize_verb(token: str, config: MorphologyRules) -> str | None:
    """Map an inflected verb to its infinitive when the stem is recognised."""
    if token in PRESENT_STEM_INFINITIVE:
        return PRESENT_STEM_INFINITIVE[token]

    for prefix in VERB_PREFIXES:
        if not token.startswith(prefix):
            continue
        body = token[len(prefix) :]
        if not body:
            continue
        if body in PRESENT_STEM_INFINITIVE:
            return PRESENT_STEM_INFINITIVE[body]
        for suffix in VERB_PERSON_SUFFIXES:
            if not body.endswith(suffix):
                continue
            stem = body[: -len(suffix)]
            if stem in PRESENT_STEM_INFINITIVE:
                return PRESENT_STEM_INFINITIVE[stem]
    for suffix in VERB_PERSON_SUFFIXES:
        if not token.endswith(suffix):
            continue
        stem = token[: -len(suffix)]
        if stem in PRESENT_STEM_INFINITIVE:
            return PRESENT_STEM_INFINITIVE[stem]
    return None


def lemmatize_tokens(
    tokens: list[str],
    rules: MorphologyRules | None = None,
) -> list[str]:
    config = rules or MorphologyRules()
    return [lemmatize_token(token, config) for token in tokens]
