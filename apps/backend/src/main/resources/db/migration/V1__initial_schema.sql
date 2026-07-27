-- =============================================================================
-- V1__initial_schema.sql
-- Software Archaeologist MVP - Initial Database Schema
-- 
-- Tables: analysis_jobs, projects, graph_nodes, graph_edges, agent_results,
--         code_embeddings, architecture_reports, kiro_specs
-- Extensions: pgvector (vector similarity search)
-- =============================================================================

-- Enable pgvector extension for embedding storage and similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Analysis Jobs
-- Tracks the lifecycle of a repository analysis request.
-- Status flow: pending → cloning → analyzing → completed | failed
-- =============================================================================
CREATE TABLE analysis_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_url        VARCHAR(500) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    current_agent   VARCHAR(50),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,
    error_message   TEXT,
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'cloning', 'analyzing', 'completed', 'failed', 'cancelled')
    )
);

-- =============================================================================
-- Projects
-- One project record per successful analysis. Links to the originating job.
-- =============================================================================
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES analysis_jobs(id),
    repo_url        VARCHAR(500) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    language        VARCHAR(50),
    framework       VARCHAR(50),
    total_files     INTEGER DEFAULT 0,
    total_loc       INTEGER DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Graph Nodes
-- Represents entities in the dependency graph: files, classes, functions, etc.
-- =============================================================================
CREATE TABLE graph_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_type       VARCHAR(20) NOT NULL,
    name            VARCHAR(500) NOT NULL,
    qualified_name  VARCHAR(1000),
    file_path       VARCHAR(1000),
    loc             INTEGER DEFAULT 0,
    complexity      INTEGER DEFAULT 1,
    last_modified   TIMESTAMP WITH TIME ZONE,
    metadata        JSONB DEFAULT '{}',
    CONSTRAINT valid_node_type CHECK (
        node_type IN ('file', 'class', 'function', 'module', 'package')
    )
);

CREATE INDEX idx_nodes_project ON graph_nodes(project_id);
CREATE INDEX idx_nodes_type ON graph_nodes(project_id, node_type);

-- =============================================================================
-- Graph Edges
-- Represents relationships between graph nodes: imports, inheritance, etc.
-- =============================================================================
CREATE TABLE graph_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_node_id  UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id  UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type       VARCHAR(20) NOT NULL,
    metadata        JSONB DEFAULT '{}',
    CONSTRAINT valid_edge_type CHECK (
        edge_type IN ('import', 'inheritance', 'usage', 'composition')
    )
);

CREATE INDEX idx_edges_project ON graph_edges(project_id);
CREATE INDEX idx_edges_source ON graph_edges(source_node_id);
CREATE INDEX idx_edges_target ON graph_edges(target_node_id);

-- =============================================================================
-- Agent Results
-- Stores the output and status of each agent execution within a pipeline run.
-- =============================================================================
CREATE TABLE agent_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    agent_name      VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    output          JSONB,
    error_message   TEXT,
    started_at      TIMESTAMP WITH TIME ZONE,
    completed_at    TIMESTAMP WITH TIME ZONE,
    execution_order INTEGER NOT NULL,
    CONSTRAINT valid_agent_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'skipped')
    )
);

CREATE INDEX idx_agent_results_job ON agent_results(job_id);

-- =============================================================================
-- Code Embeddings (pgvector)
-- Stores vector embeddings for AST-aware code chunks.
-- Used by RAG retriever for semantic search.
-- Titan Embeddings V2 produces 1024-dimensional vectors.
-- =============================================================================
CREATE TABLE code_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    chunk_text      TEXT NOT NULL,
    chunk_type      VARCHAR(20) NOT NULL,
    file_path       VARCHAR(1000),
    module_name     VARCHAR(200),
    function_name   VARCHAR(200),
    embedding       vector(1024),
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_embeddings_project ON code_embeddings(project_id);
CREATE INDEX idx_embeddings_vector ON code_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- Architecture Reports
-- Stores the structured analysis report generated by the agent pipeline.
-- =============================================================================
CREATE TABLE architecture_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content         JSONB NOT NULL,
    agents_status   JSONB NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Kiro Specs
-- Stores generated Kiro specification markdown documents.
-- is_partial = true when not all agents completed successfully.
-- =============================================================================
CREATE TABLE kiro_specs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    markdown_content TEXT NOT NULL,
    is_partial      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
