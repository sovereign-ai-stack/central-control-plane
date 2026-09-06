"""Post-retrieval pipeline errors (spec 005-rag-pipeline)."""


class PipelineError(Exception):
    """Base post-retrieval pipeline error."""


class PipelineValidationError(PipelineError):
    """Invalid pipeline options or inputs."""


class RerankContractViolationError(PipelineError):
    """
    Reranker returned a chunk multiset different from its input (RR-001).

    Treated as a critical security defect: the pipeline fails closed and never
    returns chunks or context produced by a violating reranker.
    """


class UnauthorizedChunkInPipelineError(PipelineError):
    """L4 re-validation found a chunk outside the caller's authorization scope."""
