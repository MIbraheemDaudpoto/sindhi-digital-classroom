# Production gate

This repository is not deployed by this project change. A free tier is not a
production hosting commitment. Before enabling real student accounts on a public
host, an operator must verify each item against the chosen host and model provider:

- Persistent storage survives redeploys and restarts; SQLite runs on one app
  instance with a durable mounted volume. Do not use an ephemeral filesystem or
  scale multiple writers against this SQLite database.
- The host permits the required network access and capacity without a payment
  card, and its current quotas, sleep policy, and retention terms are acceptable.
- A hosted AI endpoint performs a successful grounded inference from the running
  application. Capture provider/model and request success without logging student
  text. An installed model file or configured name is insufficient evidence.
- Production secrets are injected outside source control. Set a unique
  `SECRET_KEY` of at least 32 characters, `ENVIRONMENT=production`, and explicit
  allowed browser origins when cross-origin access is needed.
- A scheduled backup uses `scripts/backup_sqlite.py` against the persistent
  database, stores copies outside the application volume, and has a demonstrated
  restore procedure. Run it on an isolated copy before relying on it.
- Health and readiness checks are monitored, logs omit sensitive student text,
  and deployment rollback is documented.

The app's startup seeds curriculum data. Review that behavior before deploying
against an existing production database. No production DB migration or cleanup is
authorized by this readiness work.
