"""Quick test script to verify RAG retrieval works."""
import asyncio
import sys
import numpy as np
from uuid import UUID


async def main():
    from src.adapters.postgres_adapter import PostgresAdapter
    from src.rag.embeddings import TitanEmbeddingsClient

    project_id = UUID(sys.argv[1]) if len(sys.argv) > 1 else UUID("4a55b0c2-6262-4b47-8457-4a5680542da6")
    question = sys.argv[2] if len(sys.argv) > 2 else "que estructura tiene el proyecto"

    print(f"Project: {project_id}")
    print(f"Question: {question}")

    pg = PostgresAdapter()
    await pg.connect()

    # Check if embeddings exist
    count_rows = await pg.fetch(
        "SELECT COUNT(*) as cnt FROM code_embeddings WHERE project_id = $1",
        project_id,
    )
    print(f"Embeddings in DB for this project: {count_rows[0]['cnt']}")

    if count_rows[0]["cnt"] == 0:
        print("ERROR: No embeddings found!")
        await pg.close()
        return

    # Generate query embedding
    print("Generating question embedding...")
    emb = TitanEmbeddingsClient()
    q_vec = await emb.generate_embedding(question)
    print(f"Embedding dim: {len(q_vec)}")

    # Query
    rows = await pg.fetch(
        """
        SELECT chunk_text, file_path, 1 - (embedding <=> $1::vector) AS similarity
        FROM code_embeddings
        WHERE project_id = $2
        ORDER BY embedding <=> $1::vector
        LIMIT 5
        """,
        np.array(q_vec),
        project_id,
    )

    print(f"\nTop {len(rows)} results:")
    for r in rows:
        sim = float(r["similarity"])
        fp = r["file_path"] or "?"
        text_preview = r["chunk_text"][:80].replace("\n", " ")
        print(f"  sim={sim:.4f} | {fp} | {text_preview}...")

    if not rows:
        print("NO ROWS RETURNED — vector query failed")

    await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
