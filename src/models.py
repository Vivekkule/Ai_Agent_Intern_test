from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DocumentMetadata:
    document_id: str
    title: str
    status: str
    effective_date: Optional[str] = None
    last_reviewed: Optional[str] = None
    audience: Optional[str] = None
    policy_authority: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    superseded_date: Optional[str] = None
    customer_answering: Optional[bool] = None


@dataclass
class Passage:
    passage_id: str
    document_id: str
    filename: str
    heading: str
    text: str
    metadata: DocumentMetadata


@dataclass
class RetrievalResult:
    passage: Passage
    score: float
    authority_score: float = 0.0
    conflict_group: Optional[str] = None


@dataclass
class RetrievalResponse:
    results: list[RetrievalResult] = field(default_factory=list)
    conflicts: list[list[Passage]] = field(default_factory=list)