from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from rank_bm25 import BM25Okapi

from .kb_loader import KnowledgeBaseLoader
from .models import Passage, RetrievalResponse, RetrievalResult


class KnowledgeBaseIndex:
    """
    BM25-based knowledge-base index.

    Retrieval and authority are intentionally separate:
    - BM25 determines textual relevance.
    - authority/precedence determines which sources are safe to use.
    """

    def __init__(self, knowledge_base_dir: str | Path):
        loader = KnowledgeBaseLoader(knowledge_base_dir)

        self.passages = loader.load_documents()

        if not self.passages:
            raise ValueError("Knowledge base contains no passages")

        self._tokens = [
        self._tokenize(
        f"{passage.heading} {passage.text}"
        )
        for passage in self.passages
        ]

        self._bm25 = BM25Okapi(self._tokens)

        self._documents = {
            passage.document_id: passage.metadata
            for passage in self.passages
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> RetrievalResponse:
        """
        Retrieve relevant passages.

        BM25 ranking is performed first. Authority is then used as a
        secondary ranking signal.
        """

        if not query.strip():
            return RetrievalResponse()

        query_tokens = self._tokenize(query)

        if not query_tokens:
            return RetrievalResponse()

        scores = self._bm25.get_scores(query_tokens)

        candidates = []

        for index, score in enumerate(scores):
            if score <= 0:
                continue

            passage = self.passages[index]

            candidates.append(
                RetrievalResult(
                    passage=passage,
                    score=float(score),
                    authority_score=self.authority_score(passage),
                )
            )

        candidates.sort(
            key=lambda result: (
                result.authority_score,
                result.score,
            ),
            reverse=True,
        )

        candidates = self._expand_related_passages(
            candidates,
            top_k=top_k,
        )

        conflicts = self.detect_conflicts(candidates)

        return RetrievalResponse(
            results=candidates,
            conflicts=conflicts,
        )
    def _expand_related_passages(
        self,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """
        Expand retrieval with closely related passages from the
        same authoritative document.

        This is useful for policies where related facts are split
        across multiple sections, such as:
        - supported destinations
        - delivery estimates
        - duties and taxes

        The expansion is limited so unrelated documents do not
        flood the context.
        """

        if not candidates:
            return []

        selected = candidates[:top_k]

        selected_ids = {
            result.passage.passage_id
            for result in selected
        }

        authoritative_documents = {
            result.passage.document_id
            for result in selected
            if self.is_customer_authoritative(
                result.passage
            )
        }

        if not authoritative_documents:
            return selected

        for passage in self.passages:
            if (
                passage.document_id
                not in authoritative_documents
            ):
                continue

            if passage.passage_id in selected_ids:
                continue

            # Related passages receive a small deterministic
            # score so their original BM25 relevance remains
            # visible but they can still be included.
            selected.append(
                RetrievalResult(
                    passage=passage,
                    score=0.0,
                    authority_score=self.authority_score(
                        passage
                    ),
                )
            )

            selected_ids.add(passage.passage_id)

        return selected
    def authority_score(self, passage: Passage) -> float:
        """
        Return a deterministic authority score.

        Higher is better.

        This is NOT a truth score. It only represents how appropriate
        the document is as a customer-facing source.
        """

        metadata = passage.metadata

        score = 0.0

        # Customer-facing content is preferred.
        if metadata.audience == "customer":
            score += 30

        # Official policies are preferred.
        if metadata.policy_authority == "official":
            score += 40

        # Active content is preferred.
        if metadata.status == "active":
            score += 30

        # Explicitly non-authoritative content should never outrank
        # legitimate customer policies.
        if metadata.policy_authority == "none":
            score -= 100

        # Draft content is not customer-answering authority.
        if metadata.status == "draft":
            score -= 100

        if metadata.customer_answering is False:
            score -= 100

        # Superseded documents should be strongly deprioritized.
        if metadata.status == "superseded":
            score -= 80

        return score

    def is_customer_authoritative(self, passage: Passage) -> bool:
        """
        Determine whether a passage is an appropriate authoritative
        source for a normal customer-facing answer.
        """

        metadata = passage.metadata

        return (
            metadata.status == "active"
            and metadata.audience == "customer"
            and metadata.policy_authority == "official"
            and metadata.customer_answering is not False
        )

    def detect_conflicts(
        self,
        results: list[RetrievalResult],
    ) -> list[list[Passage]]:
        """
        Detect potential conflicts between active official sources.

        We intentionally do not attempt to solve semantic contradiction
        here. The agent can inspect the retrieved passages and decide
        whether the conflict is genuine.
        """

        groups: dict[str, list[Passage]] = defaultdict(list)

        for result in results:
            passage = result.passage
            metadata = passage.metadata

            if not self.is_customer_authoritative(passage):
                continue

            topic = self._conflict_topic(passage)

            if topic:
                groups[topic].append(passage)

        return [
            passages
            for passages in groups.values()
            if len({p.document_id for p in passages}) > 1
        ]

    @staticmethod
    def _conflict_topic(passage: Passage) -> str | None:
        """
        Assign a lightweight topic key.

        This is deliberately conservative. A later agent/evaluation
        layer can perform more precise semantic conflict detection.
        """

        text = passage.text.lower()
        filename = passage.filename.lower()

        if (
            "breeze" in text
            or "breeze" in filename
        ):
            return "breeze-tumbler"

        return None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        Simple deterministic tokenizer suitable for BM25.
        """

        return re.findall(
            r"[a-z0-9]+(?:[-'][a-z0-9]+)*",
            text.lower(),
        )