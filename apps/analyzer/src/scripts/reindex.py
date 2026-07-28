"""One-shot script to index embeddings for an already-analyzed project.

Usage (inside container):
  python -m src.scripts.reindex <job_id> <repo_url>
"""
import asyncio
import sys
import logging
from pathlib import Path
from uuid import UUID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(job_id_str: str, repo_url: str):
    from src.adapters.postgres_adapter import PostgresAdapter
    from src.parsing.chunker import ASTChunker
    from src.parsing.tree_sitter_parser import TreeSitterParser
    from src.rag.embeddings import TitanEmbeddingsClient
    from src.rag.indexer import EmbeddingIndexer
    from git import Repo

    job_id = UUID(job_id_str)
    repo_path = Path("/tmp/repos") / job_id_str

    # Clone if needed
    if not repo_path.exists():
        logger.info("Cloning %s ...", repo_url)
        Repo.clone_from(repo_url, str(repo_path), depth=1, single_branch=True)
    else:
        logger.info("Repo already at %s", repo_path)

    # Connect to DB
    postgres = PostgresAdapter()
    await postgres.connect()

    # Ensure DB records exist
    await postgres.execute(
        "INSERT INTO analysis_jobs (id, repo_url, status) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING",
        job_id, repo_url, "completed",
    )
    await postgres.execute(
        "INSERT INTO projects (id, job_id, repo_url, name, language, framework, total_files, total_loc) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (id) DO NOTHING",
        job_id, job_id, repo_url, repo_url.rstrip("/").split("/")[-1], "java", "spring-boot", 50, 5000,
    )

    # Delete old embeddings for this project (if re-running)
    await postgres.execute("DELETE FROM code_embeddings WHERE project_id = $1", job_id)

    # List source files
    import os
    EXCLUDED = {".git", "node_modules", "__pycache__", "target", "build", "dist", ".gradle", ".idea", "venv"}
    source_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED]
        for f in files:
            source_files.append(Path(root) / f)

    logger.info("Found %d total files", len(source_files))

    # Parse
    parser = TreeSitterParser()
    parseable = {".java", ".ts", ".tsx", ".js", ".jsx", ".py"}
    parsed = []
    for fp in source_files:
        if fp.suffix.lower() in parseable:
            r = parser.parse_file(fp)
            if r:
                parsed.append(r)

    logger.info("Parsed %d source files", len(parsed))

    # Chunk
    chunker = ASTChunker()
    chunks = chunker.chunk_parsed_files(parsed)
    logger.info("Generated %d chunks", len(chunks))

    if not chunks:
        logger.error("No chunks generated!")
        await postgres.close()
        return

    # Limit to control costs
    if len(chunks) > 100:
        logger.info("Limiting to 100 chunks")
        chunks = chunks[:100]

    # Embed
    logger.info("Generating embeddings for %d chunks...", len(chunks))
    emb_client = TitanEmbeddingsClient()
    texts = [c.text for c in chunks]
    embeddings = await emb_client.generate_batch(texts)
    logger.info("Got %d embeddings", len(embeddings))

    # Index
    indexer = EmbeddingIndexer(postgres=postgres)
    count = await indexer.index_chunks(job_id, chunks, embeddings)
    logger.info("Indexed %d embeddings. DONE!", count)

    await postgres.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m src.scripts.reindex <job_id> <repo_url>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
