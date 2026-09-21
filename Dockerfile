FROM python:3.12.11-slim-bookworm
WORKDIR /app
ENV VECLIB_MAXIMUM_THREADS=1 UV_NO_PROGRESS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg
RUN python -m pip install --no-cache-dir uv==0.8.22
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev
COPY configs ./configs
COPY examples ./examples
ENTRYPOINT ["/app/.venv/bin/capprune"]
CMD ["demo"]
