#!/usr/bin/env python3
"""Derive NEON_JDBC_URL from NEON_DATABASE_URL in .env (idempotent).

pgjdbc does not support user:password@ in the URL authority, so the Neon
libpq-style URL must be rewritten with credentials in query params:
  postgresql://user:pass@host/db?sslmode=require
  -> jdbc:postgresql://host:5432/db?user=...&password=...&sslmode=require
Secrets are never printed.
"""
import pathlib
import urllib.parse

ENV = pathlib.Path(__file__).resolve().parents[1] / ".env"

raw = ENV.read_text(encoding="utf-8")
env = {}
for line in raw.splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

src = env.get("NEON_DATABASE_URL", "")
if not src:
    raise SystemExit("NEON_DATABASE_URL missing in .env")

u = urllib.parse.urlsplit(src)
q = dict(urllib.parse.parse_qsl(u.query))
q.setdefault("user", u.username or "")
q.setdefault("password", u.password or "")
q.setdefault("sslmode", "require")

jdbc = "jdbc:postgresql://{}:{}{}?{}".format(
    u.hostname,
    u.port or 5432,
    u.path or "/postgres",
    urllib.parse.urlencode(q, quote_via=urllib.parse.quote),
)

new_raw = raw
marker = "NEON_JDBC_URL="
if marker in new_raw:
    import re
    new_raw = re.sub(rf"^{marker}.*$", marker + jdbc, new_raw, flags=re.M)
else:
    new_raw = new_raw.rstrip("\n") + "\n# Derived JDBC URL (pgjdbc needs credentials in query params)\n" + marker + jdbc + "\n"

ENV.write_text(new_raw, encoding="utf-8")
print("NEON_JDBC_URL written:",
      f"host={u.hostname} port={u.port or 5432} db={u.path} sslmode={q['sslmode']} "
      f"len={len(jdbc)}")
