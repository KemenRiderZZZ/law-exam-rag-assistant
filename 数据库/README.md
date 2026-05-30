# PostgreSQL + pgvector 使用说明

本目录用于管理当前项目的数据库配置、初始化 SQL、导入脚本和向量回填脚本。

当前推荐路线是：

1. Windows 本机安装 PostgreSQL 16
2. 为 PostgreSQL 安装 pgvector 扩展
3. 初始化 `lawqa` 数据库
4. 将 `切块/*.jsonl` 导入 `books/chunks`
5. 使用硅基流动 `BAAI/bge-m3` 回填向量

## 目录约定

- 项目根目录：`D:\桌面\云端法考知识问答项目`
- PostgreSQL 程序目录：`D:\PostgreSQL\16`
- Windows 本机数据目录：`D:\PostgreSQLData\PG16`
- Docker 备用数据目录：`D:\桌面\云端法考知识问答项目\中文数据库数据\docker-pgdata`

## 已有文件

- `数据库\.env.pg`
- `数据库\.env.embedding`
- `数据库\init\01-init-pgvector.sql`
- `数据库\验证与示例查询.sql`
- `数据库\import_chunks_to_pg.py`
- `数据库\embed_and_update.py`
- `数据库\search_chunks.py`

## 数据库连接配置

默认连接参数来自 `数据库\.env.pg`：

```text
POSTGRES_USER=law
POSTGRES_PASSWORD=please-change-this-password
POSTGRES_DB=lawqa
POSTGRES_PORT=5432
```

脚本默认还会使用以下兜底值：

```text
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=lawqa
POSTGRES_USER=law
POSTGRES_PASSWORD=please-change-this-password
```

## embedding 配置

`数据库\.env.embedding` 默认字段：

```text
SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_BATCH_SIZE=32
EMBEDDING_MAX_INPUT_TOKENS=8192
```

其中 `SILICONFLOW_API_KEY` 需要你自行填写。

## Windows 本机安装步骤

### 1. 安装 PostgreSQL 16

- 程序目录设为：`D:\PostgreSQL\16`
- 数据目录设为：`D:\PostgreSQLData\PG16`
- 端口设为：`5432`
- 超级用户密码自行设置并妥善保存

说明：

- EDB 的 Windows 安装器不接受中文数据目录路径
- 因此 PostgreSQL 真正的数据目录需要使用 ASCII 路径
- 项目内仍保留 `中文数据库数据` 目录用于说明和 Docker 备用目录管理

### 2. 创建项目用户和数据库

进入 `psql` 后执行：

```sql
CREATE USER law WITH PASSWORD 'please-change-this-password';
CREATE DATABASE lawqa OWNER law;
GRANT ALL PRIVILEGES ON DATABASE lawqa TO law;
```

### 3. 安装 pgvector

Windows 上 pgvector 通常需要按 PostgreSQL 主版本匹配安装。

如果你的环境是源码编译方式，常见流程是：

```bat
set "PGROOT=D:\PostgreSQL\16"
cd %TEMP%
git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

完成后，连接到 `lawqa` 执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

如果 Codex 无法直接写入 `D:\PostgreSQL\16\lib`，请右键“以管理员身份运行”：

```powershell
powershell -ExecutionPolicy Bypass -File ".\数据库\完成_pgvector_管理员步骤.ps1"
```

### 4. 初始化表结构

```powershell
psql -U law -h 127.0.0.1 -p 5432 -d lawqa -f ".\数据库\init\01-init-pgvector.sql"
```

## Docker 备用启动方式

如果你后面临时想改回 Docker，可在项目根目录执行：

```powershell
docker compose up -d
```

当前 `docker-compose.yml` 已按中文目录修正，数据会写入 `中文数据库数据\docker-pgdata`。

## 导入 JSONL

首批建议导入这两份：

- `切块\柏浪涛真金题_chunks.jsonl`
- `切块\柏浪涛刑法书_chunks.jsonl`

### 示例 1：导入真金题

```powershell
python .\数据库\import_chunks_to_pg.py `
  --jsonl ".\切块\柏浪涛真金题_chunks.jsonl" `
  --source-file ".\OCR原稿\柏浪涛真金题_整理版.md"
```

### 示例 2：导入刑法书

```powershell
python .\数据库\import_chunks_to_pg.py `
  --jsonl ".\切块\柏浪涛刑法书_chunks.jsonl" `
  --source-file ".\OCR原稿\柏浪涛刑法书.md"
```

如果 `metadata.book` 已经存在，脚本会优先使用 JSONL 中的书名；重复导入时会按 `chunk_id` 做更新而不是重复插入。

## 回填 embedding

先在 `数据库\.env.embedding` 中填好硅基流动的 API Key，再执行：

```powershell
python .\数据库\embed_and_update.py --all
```

只处理某一本书时：

```powershell
python .\数据库\embed_and_update.py --book-name "柏浪涛刑法专题讲座精讲卷（2026版）"
```

脚本默认只处理 `embedding IS NULL` 的记录，并将 `embedding_model` 写成 `BAAI/bge-m3`。

## 向量索引

当前已为 `BAAI/bge-m3` 的 `1024` 维向量建立 HNSW 索引：

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw_bge_m3_1024
ON public.chunks
USING hnsw ((embedding::vector(1024)) vector_cosine_ops)
WHERE embedding IS NOT NULL
  AND embedding_model = 'BAAI/bge-m3';
```

## 检索脚本

可以直接输入一个问题，从当前库中取最相似的 chunks：

```powershell
python .\数据库\search_chunks.py --query "故意杀人罪的既遂与未遂怎么区分？" --top-k 5
```

按书名过滤：

```powershell
python .\数据库\search_chunks.py `
  --query "侵犯公民个人信息罪怎么认定？" `
  --book-name "柏浪涛刑法专题讲座真金题卷（2026版）" `
  --top-k 5
```

按 JSON 输出：

```powershell
python .\数据库\search_chunks.py --query "共同犯罪中教唆犯怎么处理？" --json
```

## 验证

连接数据库：

```powershell
psql -U law -h 127.0.0.1 -p 5432 -d lawqa
```

库内验证：

```sql
\dx
\dt
SELECT * FROM pg_extension WHERE extname = 'vector';
SELECT COUNT(*) FROM books;
SELECT COUNT(*) FROM chunks;
SELECT DISTINCT embedding_model FROM chunks;
SELECT vector_dims(embedding) FROM chunks WHERE embedding IS NOT NULL LIMIT 5;
```

也可以直接执行示例 SQL：

```powershell
psql -U law -h 127.0.0.1 -p 5432 -d lawqa -f ".\数据库\验证与示例查询.sql"
```

## 后续建议

- 当 `BAAI/bge-m3` 首批向量回填完成后，先用 `vector_dims(embedding)` 确认实际维度。
- 维度确认后，再决定是否补 HNSW 索引。
- 如果后续书目增多，可以继续复用同一套导入脚本，不需要改表结构。
