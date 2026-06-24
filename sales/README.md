# KirkForge Sales service (Gargoyle Packy)

The small backend that turns Stripe payments into signed `license.json` files
for [Gargoyle Packy](../README.md).

```
landing/index.html       ─┐
landing/pricing.html     ─┤
                         ▼
                POST /checkout/{tier}      (creates Stripe Checkout session)
                         │                        ▲
                         │                        │
              Stripe-hosted checkout              │
                         │                        │
                         ▼                        │
              POST /webhook/stripe                │
                         │                        │  (browser redirect)
                         │                        │
        ┌────────────────┴─────────────┐          │
        │   sign license, write DB,    │          │
        │   email license.json to buyer│          │
        └────────────────┬─────────────┘          │
                         │                        │
                         ▼                        │
              GET  /portal (login) ──────────────┘
              GET  /portal/{id}/download
```

## Local dev

```sh
cd gargoyle-packy/
pip install -r requirements.txt

# 1) Generate a license-signing key (one-time, keep it safe)
python -m tools.keygen init
# Note the path it prints.

# 2) Configure env
cp sales/.env.example sales/.env
$EDITOR sales/.env
# Fill in STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_*, SMTP_*,
# LICENSE_PRIVATE_KEY_PATH, SALES_DB_PATH.

# 3) Run
set -a; source sales/.env; set +a
python -m sales
# → http://127.0.0.1:8766

# 4) Test the webhook locally with the Stripe CLI
stripe login
stripe listen --forward-to 127.0.0.1:8766/webhook/stripe
# Copy the whsec_... it prints into STRIPE_WEBHOOK_SECRET and restart.
```

## Production deploy

The service is a single FastAPI process. It's a good fit for any
container platform. Below is the recommended shape for a few common
hosts; pick one.

### Fly.io (cheapest, recommended for <1000 customers)

```toml
# fly.toml
app = "kirkforge-sales-packy"
primary_region = "ams"  # Amsterdam — EU residency

[build]
  dockerfile = "Dockerfile"

[env]
  SALES_BIND = "0.0.0.0"
  SALES_PORT = "8766"

[[services]]
  internal_port = 8766
  protocol = "tcp"
  [[services.ports]]
    handlers = ["http"]
    port = 80
    force_https = true
  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

[mounts]
  source = "sales_packy_data"
  destination = "/var/lib/sales-packy"

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

Secrets via `fly secrets set`:
```sh
fly secrets set \
  STRIPE_SECRET_KEY=sk_live_... \
  STRIPE_WEBHOOK_SECRET=whsec_... \
  STRIPE_PRICE_INDIE=price_... \
  STRIPE_PRICE_PRO=price_... \
  STRIPE_PRICE_ENTERPRISE=price_... \
  SMTP_HOST=smtp.postmarkapp.com \
  SMTP_USER=... \
  SMTP_PASSWORD=... \
  SMTP_FROM=licenses-packy@kirkforge.com
```

Then `fly deploy` and `fly ssh console` to upload the private signing key:
```sh
mkdir -p /var/lib/sales-packy
# scp the key in
chmod 600 /var/lib/sales-packy/private_key.pem
```

### Render

A `render.yaml` blueprint:

```yaml
services:
  - type: web
    name: kirkforge-sales-packy
    runtime: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: SALES_BIND
        value: 0.0.0.0
      - key: STRIPE_SECRET_KEY
        sync: false   # set in dashboard
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      # ... etc, see .env.example
    disk:
      name: sales-packy-data
      mountPath: /var/lib/sales-packy
      sizeGB: 1
```

### Railway / a plain VPS

Same Dockerfile, mount a persistent volume at `/var/lib/sales-packy`,
put nginx or caddy in front for TLS, set the env vars. The
service has no opinion on what fronts it.

## Stripe webhook setup

1. In the Stripe dashboard, go to **Developers → Webhooks → Add endpoint**
2. URL: `https://sales.kirkforge.com/packy/webhook/stripe`
3. Listen for: `checkout.session.completed`
4. Copy the **Signing secret** it gives you into `STRIPE_WEBHOOK_SECRET`

The webhook handler:
- Verifies the `Stripe-Signature` HMAC (no exceptions)
- Idempotent on `stripe_session_id` (Stripe retries, we don't double-sign)
- Acks any other event types so Stripe stops retrying
- Signs the license, persists to DB, emails the customer

## Customer portal

`GET /portal` is a public HTML form. The customer enters their
`license_id` (sent in the purchase email) and the email they used
at Stripe checkout. We look up the row and constant-time compare
the email — if it matches, they can re-download the license.

Rate-limited: 5 attempts per IP per 15 minutes. Good enough for a
single-tenant portal.

For higher security (magic-link email login, OAuth, etc.) the
portal routes are one file (`sales/routes/portal.py`) — swap the
auth strategy without touching the rest of the system.

## Testing

```sh
pytest tests/test_sales.py -v
```

The test suite is hermetic:
- In-memory SQLite (`tmp_path` for the file)
- `FakeEmailer` captures messages so you can assert on subject/body
- `fake_checkout_factory` returns predictable session IDs
- Real Stripe SDK for HMAC signature verification (with manually-
  computed signatures that the SDK accepts)

The end-to-end test (`test_signed_license_verifies_with_product_public_key`)
patches the customer-side embedded public key to match the sales-side
signer key and verifies the resulting license against it. Catches
drift between the two halves of the system.

## File map

| File | Purpose |
|------|---------|
| `app.py` | FastAPI factory, dependency wiring |
| `__main__.py` | `python -m sales` entrypoint |
| `config.py` | Env-driven config, fail-closed on missing secrets |
| `db.py` | SQLite wrapper for license records |
| `emailer.py` | SMTP delivery + `FakeEmailer` for tests |
| `license_signer.py` | Loads the private key, signs LicenseClaims |
| `routes/checkout.py` | POST /checkout/{tier} |
| `routes/webhook.py` | POST /webhook/stripe (signature-verified) |
| `routes/portal.py` | GET/POST /portal, GET /portal/{id}/download |
| `templates/portal_*.html` | Jinja2 templates for the portal |
| `Dockerfile` | Production image |
| `.env.example` | Every env var the service reads |
