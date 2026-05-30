SELECT extname
FROM pg_extension
WHERE extname = 'vector';

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'chunks'
ORDER BY ordinal_position;

SELECT *
FROM v_chunks_with_book
LIMIT 5;

-- 如果你后面已经写入向量，可以用下面这类查询：
-- SELECT *
-- FROM match_chunks(
--   '[0.1,0.2,0.3]'::vector,
--   5,
--   NULL,
--   NULL,
--   NULL
-- );
