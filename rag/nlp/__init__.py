"""
Persian NLP layer.

Reusable by ingestion, query processing, and the benchmark. Disabled by default;
see `config/nlp.yaml`.
"""

from rag.nlp.config import NLP_PIPELINE_VERSION, MorphologyConfig, NlpConfig, load_nlp_config
from rag.nlp.errors import NlpBackendUnavailableError, NlpConfigurationError, NlpError
from rag.nlp.morphology import MorphologyRules, lemmatize_token
from rag.nlp.normalizer import NORMALIZATION_VERSION_V2, normalize_persian_v2
from rag.nlp.pipeline import PersianNlpPipeline
from rag.nlp.sentences import BlockKind, TextBlock, detect_blocks, split_sentences
from rag.nlp.tokenizer import count_tokens, tokenize
from rag.nlp.types import ProcessedText, Sentence, Token

__all__ = [
    "NLP_PIPELINE_VERSION",
    "NORMALIZATION_VERSION_V2",
    "BlockKind",
    "MorphologyConfig",
    "MorphologyRules",
    "NlpBackendUnavailableError",
    "NlpConfig",
    "NlpConfigurationError",
    "NlpError",
    "PersianNlpPipeline",
    "ProcessedText",
    "Sentence",
    "TextBlock",
    "Token",
    "count_tokens",
    "detect_blocks",
    "lemmatize_token",
    "load_nlp_config",
    "normalize_persian_v2",
    "split_sentences",
    "tokenize",
]
