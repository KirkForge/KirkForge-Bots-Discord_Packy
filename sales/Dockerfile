# Sales service Dockerfile.
# Built on the same image as The Specialist itself, because the sales
# service imports from `license` and `sales` packages.

FROM python:3.12-slim

# Run as a non-root user. The sales service only needs:
#   - read access to LICENSE_PRIVATE_KEY_PATH
#   - write access to SALES_DB_PATH and its parent
#   - outbound network to Stripe + SMTP
# It does NOT need root, and it MUST NOT be root.
RUN groupadd --system --gid 1000 sales \
    && useradd  --system --uid 1000 --gid sales --create-home sales

WORKDIR /app

# Install dependencies first so the layer is cached when only code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Now the code.
COPY license/  ./license/
COPY sales/    ./sales/

# Drop privileges.
USER sales

EXPOSE 8766

# Healthcheck hits /healthz. A 5-second probe interval is fine — the
# service is single-purpose and either it works or it doesn't.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request, sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8766/healthz').status == 200 else 1)"

# Bind to all interfaces inside the container; the platform (Fly.io,
# Render, Railway, k8s) terminates TLS upstream.
ENV SALES_BIND=0.0.0.0 \
    SALES_PORT=8766

CMD ["python", "-m", "sales"]
