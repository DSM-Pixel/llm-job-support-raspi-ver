FROM python:3.11-slim

WORKDIR /app

# curl 은 HEALTHCHECK 용. 대부분의 의존성은 arm64/amd64 휠이 있어 빌드도구 불필요.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY pyproject.toml README.md .env.example ./
COPY backend/ ./backend/
COPY web/ ./web/
COPY prototypes/ ./prototypes/
COPY docs/ ./docs/


# RUN pip install -e ".[web,rag]"
# 각 스펙을 따옴표로 감싸야 함: 안 그러면 쉘이 '>=' 를 리다이렉션으로 해석해 버전 핀이 무시됨.
RUN pip install \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "python-multipart>=0.0.9" \
    "google-genai>=0.3.0" \
    "anthropic>=0.40.0" \
    "python-dotenv>=1.0.0" \
    "requests>=2.32.0" \
    "pillow>=10.0.0" \
    "numpy>=1.26" \
    "rank-bm25>=0.2.2" \
    && rm -rf /root/.cache/pip

EXPOSE 80

HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["uvicorn", "backend.app:app", \
     "--host", "0.0.0.0", \
     "--port", "80", \
     "--workers", "1"]
