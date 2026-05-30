CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS books (
    id BIGSERIAL PRIMARY KEY,
    book_name TEXT NOT NULL UNIQUE,
    source_file TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    db_id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT NOT NULL UNIQUE,
    book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    text_content TEXT NOT NULL,
    chapter TEXT,
    section TEXT,
    subsection TEXT,
    subsub TEXT,
    source_line_start INT,
    source_line_end INT,
    char_count INT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding_model TEXT,
    embedding vector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_source_line_range
        CHECK (
            source_line_start IS NULL
            OR source_line_end IS NULL
            OR source_line_end >= source_line_start
        )
);

CREATE INDEX IF NOT EXISTS idx_books_book_name
    ON books (book_name);

CREATE INDEX IF NOT EXISTS idx_chunks_book_id
    ON chunks (book_id);

CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index
    ON chunks (chunk_index);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_model
    ON chunks (embedding_model);

CREATE INDEX IF NOT EXISTS idx_chunks_chapter_section
    ON chunks (chapter, section);

CREATE INDEX IF NOT EXISTS idx_chunks_metadata_gin
    ON chunks
    USING GIN (metadata);

CREATE OR REPLACE VIEW v_chunks_with_book AS
SELECT
    c.db_id,
    c.chunk_id,
    b.book_name,
    b.source_file,
    c.chunk_index,
    c.text_content,
    c.chapter,
    c.section,
    c.subsection,
    c.subsub,
    c.source_line_start,
    c.source_line_end,
    c.char_count,
    c.metadata,
    c.embedding_model,
    CASE
        WHEN c.embedding IS NULL THEN NULL
        ELSE vector_dims(c.embedding)
    END AS embedding_dim,
    c.created_at
FROM chunks c
JOIN books b
  ON b.id = c.book_id;

CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector,
    match_count INT DEFAULT 5,
    filter_book_name TEXT DEFAULT NULL,
    filter_chapter TEXT DEFAULT NULL,
    filter_embedding_model TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id TEXT,
    book_name TEXT,
    chapter TEXT,
    section TEXT,
    subsection TEXT,
    subsub TEXT,
    source_line_start INT,
    source_line_end INT,
    chunk_index INT,
    char_count INT,
    embedding_model TEXT,
    score DOUBLE PRECISION,
    text_content TEXT
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        c.chunk_id,
        b.book_name,
        c.chapter,
        c.section,
        c.subsection,
        c.subsub,
        c.source_line_start,
        c.source_line_end,
        c.chunk_index,
        c.char_count,
        c.embedding_model,
        1 - (c.embedding <=> query_embedding) AS score,
        c.text_content
    FROM chunks c
    JOIN books b
      ON b.id = c.book_id
    WHERE c.embedding IS NOT NULL
      AND vector_dims(c.embedding) = vector_dims(query_embedding)
      AND (filter_book_name IS NULL OR b.book_name = filter_book_name)
      AND (filter_chapter IS NULL OR c.chapter = filter_chapter)
      AND (
          filter_embedding_model IS NULL
          OR c.embedding_model = filter_embedding_model
      )
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;
