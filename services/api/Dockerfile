FROM python:3.12.4-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system vmf && adduser --system --ingroup vmf vmf

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN pip install --no-cache-dir .

USER vmf
EXPOSE 8000

CMD ["uvicorn", "vmf_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
