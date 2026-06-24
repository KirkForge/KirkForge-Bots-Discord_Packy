# Landing page

Static site for Gargoyle Packy. Pure HTML + CSS, no build step, no JS framework.

## Local preview

```sh
cd landing/
python3 -m http.server 8000
# open http://127.0.0.1:8000
```

## Deploy to GitHub Pages

The site is small and self-contained. Push to a `gh-pages` branch (or use
GitHub Actions with `actions/deploy-pages@v4`) and point `kirkforge.com/packy`
at it via a CNAME record.

## Buy buttons

Each pricing card `<form>` posts to the sales service. Edit the `action`
URLs in `pricing.html` to point at your deployed sales server.

```html
<form action="https://sales.kirkforge.com/packy/checkout/indie" method="POST">
```

The sales server returns a Stripe Checkout redirect URL on success;
the static form action triggers that and Stripe handles the rest.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Marketing page (hero, features, how-it-works, CTA) |
| `pricing.html` | Tier comparison + Stripe Checkout forms |
| `success.html` | Post-purchase landing — pulls `?session_id=...` and links to the portal |
| `style.css` | Dark theme, no framework |
