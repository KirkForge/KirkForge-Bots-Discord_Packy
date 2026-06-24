"""KirkForge Sales service.

A small FastAPI service that:
  1. Creates Stripe Checkout sessions for license purchases
  2. Verifies Stripe webhooks and signs licenses on `checkout.session.completed`
  3. Serves a customer portal where buyers can re-download their license

The private signing key for licenses lives on this server (or in an env
var, or in a secrets manager). It MUST be backed up — loss of this key
makes every issued license unverifiable, locking out all customers.
"""
