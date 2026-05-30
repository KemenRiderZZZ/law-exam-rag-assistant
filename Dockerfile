FROM docker.m.daocloud.io/library/python:3.12-slim AS app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY 数据库/requirements.deploy.txt /tmp/requirements.deploy.txt
RUN pip install --no-cache-dir -r /tmp/requirements.deploy.txt

COPY 数据库/search_web_server.py /app/数据库/search_web_server.py
COPY 数据库/search_chunks.py /app/数据库/search_chunks.py
COPY 数据库/init/01-init-pgvector.sql /app/数据库/init/01-init-pgvector.sql
COPY 法考对话前端2.0/dist /app/法考对话前端2.0/dist

EXPOSE 8765

CMD ["python", "-u", "/app/数据库/search_web_server.py", "--host", "0.0.0.0", "--port", "8765"]
