from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    content: str
    source_path: str


def chunk_markdown(path: Path) -> list[KnowledgeChunk]:
    """Split a Markdown document on level-two headings, retaining document context."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"{path} must begin with a level-one title")

    title = lines[0][2:].strip()
    document_id = path.stem
    chunks: list[KnowledgeChunk] = []
    section: str | None = None
    body: list[str] = []

    def add_chunk() -> None:
        if section is None or not body:
            return
        enriched_content = f"Document: {title}\nSection: {section}\n\n" + "\n".join(body).strip()
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"{document_id}:{len(chunks) + 1}",
                document_id=document_id,
                title=title,
                section=section,
                content=enriched_content,
                source_path=str(path),
            )
        )

    for line in lines[1:]:
        if line.startswith("## "):
            add_chunk()
            section = line[3:].strip()
            body = []
        elif section is not None:
            body.append(line)
    add_chunk()
    return chunks


def chunk_directory(directory: Path) -> list[KnowledgeChunk]:
    return [chunk for path in sorted(directory.rglob("*.md")) for chunk in chunk_markdown(path)]
