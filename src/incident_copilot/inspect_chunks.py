from pathlib import Path

from incident_copilot.chunking import chunk_directory


def main() -> None:
    knowledge_directory = Path(__file__).resolve().parents[2] / "knowledge"
    chunks = chunk_directory(knowledge_directory)
    print(f"Created {len(chunks)} semantic chunks:\n")
    for chunk in chunks:
        print(f"[{chunk.chunk_id}] {chunk.title} → {chunk.section}")
        print(f"{chunk.content}\n")


if __name__ == "__main__":
    main()
