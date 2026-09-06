"""
Generate the Persian retrieval benchmark with document-grounded query labels.

`fa-retrieval-v1` is frozen for historical comparability. `fa-retrieval-v2` adds
morphology-sensitive categories (plural forms, verb inflection, spelling
variants) so the Phase 5 NLP layer can be measured before and after.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

_ARABIC_YEH = "\u064a"
_PERSIAN_YEH = "\u06cc"
_ARABIC_KAF = "\u0643"
_PERSIAN_KAF = "\u06a9"
_ZWNJ = "\u200c"


def _stable_uuid(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return str(UUID(bytes=digest[:16]))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _to_arabic_chars(text: str) -> str:
    return text.replace(_PERSIAN_YEH, _ARABIC_YEH).replace(_PERSIAN_KAF, _ARABIC_KAF)


def _without_zwnj(text: str) -> str:
    return text.replace(_ZWNJ, " ")


def _with_zwnj_compound(text: str, compound: str, zwnj_form: str) -> str:
    return text.replace(compound, zwnj_form)


def _extract_number(text: str) -> str | None:
    match = re.search(r"\d+", text)
    return match.group(0) if match else None


_MORPHOLOGY_NOUNS = {
    ("hr", 0): ("مرخصی", "مرخصی‌ها", "مرخصیها"),
    ("hr", 1): ("درخواست", "درخواست‌ها", "درخواستها"),
    ("hr", 2): ("بیمه", "بیمه‌ها", "بیمه‌های"),
    ("legal", 0): ("قرارداد", "قرارداد‌ها", "قراردادهای"),
    ("legal", 1): ("کاربر", "کاربران", "کاربرها"),
    ("legal", 2): ("گزارش", "گزارش‌ها", "گزارشهای"),
    ("technical", 0): ("پورت", "پورت‌ها", "پورتهای"),
    ("technical", 1): ("پشتیبان", "پشتیبان‌گیری", "پشتیبانگیری"),
    ("technical", 2): ("نسخه", "نسخه‌ها", "نسخههای"),
    ("general", 0): ("ساعت", "ساعت‌ها", "ساعتهای"),
    ("general", 1): ("تیکت", "تیکت‌ها", "تیکتهای"),
    ("general", 2): ("راهنما", "راهنماها", "راهنماهای"),
}

_MORPHOLOGY_CATEGORIES = (
    "morphology",
    "plural_forms",
    "verb_forms",
    "spelling_variants",
)


def _morphology_specs(domain: str, template_index: int, n: int) -> dict[str, list[str]]:
    """
    Morphology-sensitive query families for fa-retrieval-v2.

    Every query keeps the document number so the grounding validator still
    holds; only the *word forms* vary, which is exactly what the NLP layer is
    supposed to neutralise.
    """
    entry = _MORPHOLOGY_NOUNS.get((domain, template_index))
    if entry is None:
        return {}
    singular, plural_zwnj, plural_joined = entry
    return {
        # ZWNJ-joined plural vs the singular in the document
        "morphology": [f"{plural_zwnj} و شرایط آن ({n})"],
        # same plural written without ZWNJ
        "plural_forms": [f"{plural_joined} ({n})"],
        # verb written joined ("میشود") where the document uses "می‌شود"
        "verb_forms": [f"{singular} چگونه ثبت میشود؟ ({n})"],
        # mixed Arabic/Persian letters plus dropped ZWNJ. The distinct "شرایط"
        # prefix keeps this unique even when the word has no ی/ک to convert.
        "spelling_variants": [f"شرایط {_to_arabic_chars(plural_joined)} ({n})"],
    }


def _query_specs_for_document(domain: str, template_index: int, text: str, n: int) -> dict[str, list[str]]:
    """Build category-specific queries grounded in the target document text."""
    specs: dict[str, list[str]] = {
        "semantic": [],
        "paraphrase": [],
        "mixed_language": [],
        "technical": [],
        "short_query": [],
        "long_query": [],
        "zwnj": [],
        "arabic_char_variants": [],
    }

    if domain == "hr":
        if template_index == 0:
            specs["semantic"] = [f"مرخصی سالانه کارکنان تمام وقت چند روز است؟ ({n})"]
            specs["paraphrase"] = [f"تعداد روزهای مرخصی سالانه برای کارکنان تمام‌وقت چقدر است؟ ({n})"]
            specs["short_query"] = [f"مرخصی سالانه؟ ({n})"]
            specs["long_query"] = [
                (
                    "لطفاً توضیح دهید سیاست مرخصی سالانه برای کارکنان تمام‌وقت "
                    f"چند روز در نظر گرفته شده است ({n})"
                )
            ]
            specs["zwnj"] = [f"سیاست مرخصی برای کارکنان تمام{'‌' if n % 2 else ''}وقت ({n})"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"سياست مرخصي سالانه ({n})")]
        elif template_index == 1:
            specs["semantic"] = [f"درخواست مرخصی باید چند روز قبل ثبت شود؟ ({n})"]
            specs["paraphrase"] = [f"حداقل چند روز قبل از مرخصی باید درخواست ثبت شود؟ ({n})"]
            specs["short_query"] = [f"مهلت ثبت مرخصی؟ ({n})"]
            specs["long_query"] = [
                f"فرآیند ثبت درخواست مرخصی و مهلت {n} روزه قبل از شروع مرخصی را توضیح دهید"
            ]
            specs["zwnj"] = [f"درخواست مرخصی حداقل {n} روز قبل ثبت شود ({n})"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"درخواست مرخصي ({n})")]
        else:
            specs["semantic"] = [f"کارکنان جدید پس از چند ماه بیمه تکمیلی می‌شوند؟ ({n})"]
            specs["paraphrase"] = [f"بیمه تکمیلی برای کارکنان تازه‌وارد بعد از {n} ماه فعال می‌شود؟ ({n})"]
            specs["short_query"] = [f"بیمه تکمیلی؟ ({n})"]
            specs["long_query"] = [f"شرایط دریافت بیمه تکمیلی برای کارکنان جدید پس از {n} ماه ({n})"]
            specs["zwnj"] = [f"کارکنان جدید پس از {n} ماه مشمول بیمه{'‌' if n % 2 else ''}تکمیلی ({n})"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"بيمه تکميلي ({n})")]
    elif domain == "legal":
        if template_index == 0:
            specs["semantic"] = [f"ماده {n} قانون کار درباره چه قراردادهایی است؟"]
            specs["paraphrase"] = [f"کدام نوع قرارداد در ماده {n} قانون کار آمده است؟"]
            specs["short_query"] = [f"ماده {n}؟"]
            specs["long_query"] = [f"توضیح ماده {n} قانون کار درباره قراردادهای موقت و شرایط آن"]
            specs["zwnj"] = [f"ماده {n} قانون کار و قراردادهای{'‌' if n % 2 else ''}موقت"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"ماده {n} قانون کار")]
        elif template_index == 1:
            specs["semantic"] = [f"حفظ حریم خصوصی کاربران طبق بند {n} چگونه است؟"]
            specs["paraphrase"] = [f"الزامات حریم خصوصی در بند {n} چیست؟"]
            specs["short_query"] = [f"حریم خصوصی؟ ({n})"]
            specs["long_query"] = [f"سیاست حفظ حریم خصوصی کاربران مطابق بند {n} را شرح دهید"]
            specs["zwnj"] = [f"حفظ حریم{'‌' if n % 2 else ''}خصوصی طبق بند {n}"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"حريم خصوصي بند {n}")]
        else:
            specs["semantic"] = [f"گزارش تخلف باید ظرف {n} روز کاری بررسی شود؟"]
            specs["paraphrase"] = [f"مهلت بررسی گزارش تخلف {n} روز کاری است؟"]
            specs["short_query"] = [f"گزارش تخلف؟ ({n})"]
            specs["long_query"] = [f"فرآیند بررسی گزارش تخلف و مهلت {n} روز کاری مربوطه"]
            specs["zwnj"] = [f"گزارش تخلف ظرف {n} روز{'‌' if n % 2 else ''}کاری"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"گزارش تخلف {n}")]
    elif domain == "technical":
        if template_index == 0:
            specs["semantic"] = [f"برای اتصال VPN از چه پورت {n} استفاده می‌شود؟"]
            specs["paraphrase"] = [f"پورت {n} و احراز هویت دو مرحله‌ای برای VPN چیست؟"]
            specs["technical"] = [f"تنظیمات VPN پورت {n} و MFA"]
            specs["mixed_language"] = [f"How to connect VPN on port {n} با احراز هویت دو مرحله‌ای؟"]
            specs["short_query"] = [f"VPN پورت {n}؟"]
            specs["long_query"] = [
                f"راهنمای اتصال VPN با پورت {n} و فعال‌سازی احراز هویت دو مرحله‌ای"
            ]
            specs["zwnj"] = [f"اتصال VPN از پورت {n} و احراز{'‌' if n % 2 else ''}هویت"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"اتصال VPN پورت {n}")]
        elif template_index == 1:
            specs["semantic"] = [f"پشتیبان‌گیری پایگاه داده هر {n} ساعت انجام می‌شود؟"]
            specs["paraphrase"] = [f"بک‌آپ پایگاه داده هر {n} ساعت یکبار است؟"]
            specs["technical"] = [f"Database backup interval {n} hours"]
            specs["mixed_language"] = [f"Database backup schedule every {n} hours در سیستم"]
            specs["short_query"] = [f"بک‌آپ DB؟ ({n})"]
            specs["long_query"] = [f"سیاست پشتیبان‌گیری پایگاه داده با بازه {n} ساعته"]
            specs["zwnj"] = [f"پشتیبان{'‌' if n % 2 else ''}گیری پایگاه داده هر {n} ساعت"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"پشتيبان گيري {n}")]
        else:
            specs["semantic"] = [f"API داخلی نسخه {n} از OAuth2 پشتیبانی می‌کند؟"]
            specs["paraphrase"] = [f"OAuth2 در API نسخه {n} پشتیبانی می‌شود؟"]
            specs["technical"] = [f"Internal API v{n} OAuth2 support"]
            specs["mixed_language"] = [f"API token OAuth2 version {n} در سامانه داخلی"]
            specs["short_query"] = [f"OAuth2 v{n}؟"]
            specs["long_query"] = [f"مستندات API داخلی نسخه {n} و پشتیبانی OAuth2"]
            specs["zwnj"] = [f"API نسخه {n} و OAuth{'‌' if n % 2 else ''}2"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"API نسخه {n}")]
    else:  # general
        if template_index == 0:
            specs["semantic"] = [f"ساعات پاسخگویی پشتیبانی از {n} تا {n} است؟"]
            specs["paraphrase"] = [f"پشتیبانی در چه ساعاتی از {n} تا {n} فعال است؟"]
            specs["short_query"] = [f"ساعات پشتیبانی؟ ({n})"]
            specs["long_query"] = [f"ساعات پاسخگویی تیم پشتیبانی از {n} تا {n} را توضیح دهید"]
            specs["zwnj"] = [f"ساعات پاسخ{'‌' if n % 2 else ''}گویی پشتیبانی ({n})"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"ساعات پشتيباني {n}")]
        elif template_index == 1:
            specs["semantic"] = [f"برای ثبت تیکت چه اطلاعاتی لازم است؟ ({n})"]
            specs["paraphrase"] = [f"ثبت تیکت پشتیبانی به چه داده‌ای نیاز دارد؟ ({n})"]
            specs["short_query"] = [f"ثبت تیکت؟ ({n})"]
            specs["long_query"] = [f"مراحل ثبت تیکت و وارد کردن شماره پرسنلی ({n})"]
            specs["zwnj"] = [f"ثبت تیکت و شماره{'‌' if n % 2 else ''}پرسنلی ({n})"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"ثبت تيكت {n}")]
        else:
            specs["semantic"] = [f"راهنمای کاربری سامانه کجا موجود است؟ ({n})"]
            specs["paraphrase"] = [f"مستند راهنمای سامانه در کدام پورتال است؟ ({n})"]
            specs["short_query"] = [f"راهنما؟ ({n})"]
            specs["long_query"] = [f"دسترسی به راهنمای کاربری سامانه در پورتال داخلی ({n})"]
            specs["zwnj"] = [f"راهنمای کاربری در پورتال{'‌' if n % 2 else ''}داخلی ({n})"]
            specs["arabic_char_variants"] = [_to_arabic_chars(f"راهنما {n}")]

    _ = text  # document text available for future template-driven generation
    return specs



_LONG_FORM_SECTIONS = (
    (
        "ماده {n} شرایط مرخصی",
        (
            "شرایط استفاده از مرخصی سالانه طبق ماده {n} قانون کار تعیین می‌شود. "
            "کارکنان تمام‌وقت پس از یک سال خدمت پیوسته مشمول این ماده هستند. "
            "درخواست مرخصی باید حداقل ده روز کاری پیش از تاریخ شروع ثبت شود."
        ),
    ),
    (
        "بخش {n} فرآیند تأیید",
        (
            "مدیر مستقیم موظف است ظرف سه روز کاری به درخواست پاسخ دهد. "
            "در صورت عدم پاسخ، درخواست به مدیر ارشد ارجاع داده می‌شود. "
            "تأیید نهایی در سامانه منابع انسانی ثبت و بایگانی می‌گردد."
        ),
    ),
    (
        "بند {n} موارد استثنا",
        (
            "مرخصی اضطراری از سقف سالانه کسر نمی‌شود مشروط بر ارائه مستندات. "
            "مرخصی بدون حقوق تنها با تأیید کمیته منابع انسانی امکان‌پذیر است."
        ),
    ),
)

_LONG_FORM_LIST = (
    "- ثبت درخواست در سامانه داخلی",
    "- پیوست کردن مستندات لازم",
    "- دریافت تأیید مدیر مستقیم",
)


def _long_form_document(n: int) -> str:
    """
    A multi-paragraph document with headings and a list.

    The single-sentence corpus documents cannot exercise chunking at all, so the
    chunk-level harness (benchmarks/persian/chunk_benchmark.py) needs documents
    long enough to be split more than one way.
    """
    parts: list[str] = []
    for heading, body in _LONG_FORM_SECTIONS:
        parts.append(heading.format(n=n))
        parts.append("")
        parts.append(body.format(n=n))
        parts.append("")
    parts.append(f"فهرست مراحل اجرایی ({n})")
    parts.append("")
    parts.extend(_LONG_FORM_LIST)
    return "\n".join(parts).strip()


def generate_dataset(
    output_dir: Path,
    *,
    dataset_version: str = "fa-retrieval-v1",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with_morphology = dataset_version == "fa-retrieval-v2"

    domains = ["hr", "legal", "technical", "general"]
    corpus: list[dict] = []
    queries: list[dict] = []
    validation_ids: list[str] = []
    test_ids: list[str] = []

    templates = {
        "hr": [
            "سیاست مرخصی سالانه برای کارکنان تمام‌وقت {n} روز است.",
            "درخواست مرخصی باید حداقل {n} روز قبل ثبت شود.",
            "کارکنان جدید پس از {n} ماه مشمول بیمه تکمیلی می‌شوند.",
        ],
        "legal": [
            "ماده {n} قانون کار به قراردادهای موقت اشاره دارد.",
            "حفظ حریم خصوصی کاربران طبق بند {n} الزام است.",
            "گزارش تخلف باید ظرف {n} روز کاری بررسی شود.",
        ],
        "technical": [
            "برای اتصال VPN از پورت {n} و احراز هویت دو مرحله‌ای استفاده کنید.",
            "پشتیبان‌گیری پایگاه داده هر {n} ساعت یکبار انجام می‌شود.",
            "API داخلی نسخه {n} از OAuth2 پشتیبانی می‌کند.",
        ],
        "general": [
            "ساعات پاسخگویی پشتیبانی از {n} تا {n} است.",
            "برای ثبت تیکت شماره پرسنلی خود را وارد کنید.",
            "راهنمای کاربری سامانه در پورتال داخلی موجود است.",
        ],
    }

    category_defaults = {
        "semantic": ("easy", "medium", "standard", "fa"),
        "paraphrase": ("medium", "medium", "standard", "fa"),
        "mixed_language": ("medium", "medium", "standard", "mixed"),
        "technical": ("easy", "medium", "standard", "fa"),
        "short_query": ("easy", "short", "standard", "fa"),
        "long_query": ("hard", "long", "standard", "fa"),
        "zwnj": ("medium", "medium", "zwnj", "fa"),
        "arabic_char_variants": ("medium", "medium", "arabic_chars", "fa"),
        "morphology": ("hard", "medium", "morphology", "fa"),
        "plural_forms": ("hard", "short", "morphology", "fa"),
        "verb_forms": ("hard", "medium", "morphology", "fa"),
        "spelling_variants": ("hard", "short", "spelling", "fa"),
    }

    def add_query(
        *,
        text: str,
        domain: str,
        relevant_doc_ids: list[str],
        difficulty: str,
        query_length: str,
        normalization: str,
        category: str,
        language: str = "fa",
        split: str,
    ) -> None:
        query_id = _stable_uuid(f"query-{len(queries)}-{text}")
        queries.append(
            {
                "query_id": query_id,
                "text": text,
                "domain": domain,
                "language": language,
                "relevant_doc_ids": relevant_doc_ids,
                "difficulty": difficulty,
                "query_length": query_length,
                "normalization": normalization,
                "category": category,
            }
        )
        if split == "val":
            validation_ids.append(query_id)
        else:
            test_ids.append(query_id)

    doc_index = 0
    for domain in domains:
        for template_index, template in enumerate(templates[domain]):
            for n in range(1, 14):
                doc_id = _stable_uuid(f"doc-{domain}-{doc_index}")
                text = template.format(n=n)
                corpus.append(
                    {
                        "doc_id": doc_id,
                        "text": text,
                        "domain": domain,
                        "language": "fa",
                        "metadata": {
                            "source": "synthetic-benchmark",
                            "title": f"{domain}-{doc_index}",
                            "template_index": template_index,
                            "n": n,
                        },
                    }
                )

                specs = _query_specs_for_document(domain, template_index, text, n)
                if with_morphology:
                    specs.update(_morphology_specs(domain, template_index, n))
                for category, query_texts in specs.items():
                    if not query_texts:
                        continue
                    difficulty, query_length, normalization, language = category_defaults[
                        category
                    ]
                    for query_text in query_texts:
                        add_query(
                            text=query_text,
                            domain=domain,
                            relevant_doc_ids=[doc_id],
                            difficulty=difficulty,
                            query_length=query_length,
                            normalization=normalization,
                            category=category,
                            language=language,
                            split="val",
                        )
                doc_index += 1

    if with_morphology:
        for long_index in range(12):
            n = 100 + long_index
            doc_id = _stable_uuid(f"doc-longform-{long_index}")
            corpus.append(
                {
                    "doc_id": doc_id,
                    "text": _long_form_document(n),
                    "domain": "hr",
                    "language": "fa",
                    "metadata": {
                        "source": "synthetic-benchmark",
                        "title": f"longform-{long_index}",
                        "long_form": True,
                        "n": n,
                    },
                }
            )
            add_query(
                text=f"فرآیند تأیید درخواست مرخصی طبق ماده {n} چگونه است؟",
                domain="hr",
                relevant_doc_ids=[doc_id],
                difficulty="medium",
                query_length="long",
                normalization="standard",
                category="long_query",
                split="val",
            )
            add_query(
                text=f"موارد استثنا در بند {n} کدام است؟",
                domain="hr",
                relevant_doc_ids=[doc_id],
                difficulty="medium",
                query_length="medium",
                normalization="standard",
                category="semantic",
                split="val",
            )
            doc_index += 1

    while len(corpus) < 220:
        domain = domains[doc_index % len(domains)]
        doc_id = _stable_uuid(f"doc-extra-{doc_index}")
        text = f"سند مرجع {doc_index} در حوزه {domain} برای ارزیابی بازیابی معنایی."
        corpus.append(
            {
                "doc_id": doc_id,
                "text": text,
                "domain": domain,
                "language": "fa",
                "metadata": {"source": "synthetic-benchmark", "title": f"{domain}-{doc_index}"},
            }
        )
        add_query(
            text=f"سند مرجع {doc_index} در حوزه {domain} چیست؟",
            domain=domain,
            relevant_doc_ids=[doc_id],
            difficulty="easy",
            query_length="medium",
            normalization="standard",
            category="semantic",
            split="val",
        )
        doc_index += 1

    # Test split — document-grounded queries
    for index in range(55):
        domain = domains[index % len(domains)]
        doc = corpus[index % len(corpus)]
        add_query(
            text=f"محتوای سند {doc['metadata'].get('title', domain)} چیست؟",
            domain=domain,
            relevant_doc_ids=[doc["doc_id"]],
            difficulty="easy",
            query_length="medium",
            normalization="standard",
            category="semantic",
            split="test",
        )

    _write_jsonl(output_dir / "corpus.jsonl", corpus)
    _write_jsonl(output_dir / "queries.jsonl", queries)
    splits = {
        "dataset_version": dataset_version,
        "validation_query_ids": validation_ids,
        "test_query_ids": test_ids,
        "created_at": datetime.now(UTC).isoformat(),
        "annotator_guidelines_version": "1.0",
    }
    with (output_dir / "splits.json").open("w", encoding="utf-8") as handle:
        json.dump(splits, handle, ensure_ascii=False, indent=2)

    schema = {
        "corpus_fields": ["doc_id", "text", "domain", "language", "metadata"],
        "query_fields": [
            "query_id",
            "text",
            "domain",
            "language",
            "relevant_doc_ids",
            "difficulty",
            "query_length",
            "normalization",
            "category",
        ],
    }
    with (output_dir / "schema.json").open("w", encoding="utf-8") as handle:
        json.dump(schema, handle, ensure_ascii=False, indent=2)

    readme = (
        "# fa-retrieval-v1\n\n"
        "Synthetic Persian retrieval benchmark with document-grounded query labels.\n"
        "Each validation query is generated from the content of its labeled relevant document.\n"
    )
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    checksums: list[str] = []
    for name in ("corpus.jsonl", "queries.jsonl", "splits.json", "schema.json"):
        digest = hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
        checksums.append(f"{digest}  {name}\n")
    (output_dir / "checksums.sha256").write_text("".join(checksums), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate the Persian benchmark dataset")
    parser.add_argument(
        "--version",
        default="fa-retrieval-v1",
        choices=("fa-retrieval-v1", "fa-retrieval-v2"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    output = args.output or Path(__file__).resolve().parent / "data" / args.version
    generate_dataset(output, dataset_version=args.version)
    print(f"Generated {args.version} at {output}")


if __name__ == "__main__":
    main()
