from pathlib import Path
from typing import Any

from .models import DocumentMetadata, Passage


class KnowledgeBaseLoader:
    def __init__(self, knowledge_base_dir: str | Path):
        self.knowledge_base_dir = Path(knowledge_base_dir)

    def load_documents(self) -> list[Passage]:
        passages: list[Passage] = []

        for path in sorted(self.knowledge_base_dir.glob("*.md")):
            passages.extend(self._load_file(path))

        return passages

    def _load_file(self, path: Path) -> list[Passage]:
        content = path.read_text(encoding="utf-8")

        metadata, body = self._parse_front_matter(content)

        sections = self._split_into_sections(body)

        results = []

        for index, (heading, text) in enumerate(sections):
            if not text.strip():
                continue

            passage_id = f"{metadata.document_id}:{index}"

            results.append(
                Passage(
                    passage_id=passage_id,
                    document_id=metadata.document_id,
                    filename=path.name,
                    heading=heading,
                    text=text.strip(),
                    metadata=metadata,
                )
            )

        return results

    def _parse_front_matter(
        self,
        content: str,
    ) -> tuple[DocumentMetadata, str]:

        lines = content.splitlines()

        if not lines or lines[0].strip() != "---":
            raise ValueError("Markdown file is missing front matter")

        end_index = None

        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end_index = index
                break

        if end_index is None:
            raise ValueError("Unterminated front matter")

        metadata_lines = lines[1:end_index]
        metadata_dict: dict[str, Any] = {}

        for line in metadata_lines:
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            metadata_dict[key.strip()] = self._parse_value(value.strip())

        metadata = DocumentMetadata(
            document_id=metadata_dict["document_id"],
            title=metadata_dict["title"],
            status=metadata_dict["status"],
            effective_date=metadata_dict.get("effective_date"),
            last_reviewed=metadata_dict.get("last_reviewed"),
            audience=metadata_dict.get("audience"),
            policy_authority=metadata_dict.get("policy_authority"),
            supersedes=metadata_dict.get("supersedes"),
            superseded_by=metadata_dict.get("superseded_by"),
            superseded_date=metadata_dict.get("superseded_date"),
            customer_answering=metadata_dict.get("customer_answering"),
        )

        body = "\n".join(lines[end_index + 1:])

        return metadata, body

    @staticmethod
    def _parse_value(value: str) -> Any:
        if value.lower() == "true":
            return True

        if value.lower() == "false":
            return False

        if value.lower() == "null":
            return None

        # Important:
        # "none" is a legitimate metadata value in this assignment.
        return value

    @staticmethod
    def _split_into_sections(body: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []

        current_heading = "Document"
        current_lines: list[str] = []

        for line in body.splitlines():

            if line.startswith("#"):
                if current_lines:
                    sections.append(
                        (
                            current_heading,
                            "\n".join(current_lines).strip(),
                        )
                    )

                current_heading = line.lstrip("#").strip()
                current_lines = []

            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                (
                    current_heading,
                    "\n".join(current_lines).strip(),
                )
            )

        return sections