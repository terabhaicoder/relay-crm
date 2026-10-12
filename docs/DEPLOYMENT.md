# Deploy Relay CRM on one server

This runbook targets a Linux server with Docker Engine and Compose v2, Python 3.11+, a public hostname, and persistent disk. It deploys the real SQLite application. Do not scale the API to multiple replicas or put its database on network storage. Gmail sending/sync remains deferred; support replies are saved drafts.

The repository currently passes local API and static/build checks. Server binding and Docker access are denied in the authoring session, so **container startup, browser journeys and public TLS remain release acceptance requirements**, not claimed results.

## Configure

1. Point a domain's A record (and AAAA only if IPv6 works) to the server. Permit inbound TCP 80/443. Keep SSH access restricted.
2. Copy `deploy/production.env.example` to `deploy/production.env`, set `DOMAIN` to the bare hostname and `TLS_EMAIL` to your certificate administrator. Keep `SIGNUP_ENABLED=false`.
3. Validate and start the standalone definition; do not combine it with development Compose:

```sh
docker compose --env-file deploy/production.env -f docker-compose.production.yml config --quiet
docker compose --env-file deploy/production.env -f docker-compose.production.yml up -d --build --wait
```

Caddy terminates HTTPS and redirects HTTP; the frontend and API have no published ports. The API uses production secure cookies and accepts the configured HTTPS origin only. Named volumes retain the database/uploads and certificate state. Both application images run as unprivileged users. Container logs rotate. API throttling uses a bounded process-local cache: defaults are 300 auth requests/minute per connection peer and 10/minute per account identity (`AUTH_IP_RATE_LIMIT`, `AUTH_IDENTITY_RATE_LIMIT`). The proxy peer cap is intentionally aggregate; no untrusted forwarded IP is accepted. `SESSION_DAYS` defaults to 14 and accepts 1–90. Distributed rate limiting is outside this single-instance profile.

Provision the first owner without opening public registration:

```sh
docker compose --env-file deploy/production.env -f docker-compose.production.yml exec api python -m app.bootstrap_owner --name "Workspace Owner" --email "owner@example.com" --company "Your Company"
```

Replace the example owner details; the command privately prompts for the password. Do not put the password in shell history. Log in at `https://YOUR_DOMAIN`. Invite team members through Settings; copy the invitation link and deliver it yourself through your chosen channel. The app does not claim to have emailed invitations. Unused invitations expire; used tokens cannot be reused.

## Account recovery

Email password reset is not connected. An authorized server operator can recover an account without exposing a password in command arguments:

```sh
docker compose --env-file deploy/production.env -f docker-compose.production.yml exec api python -m app.reset_password --email "owner@example.com"
```

The CLI privately prompts for a new password, records an operator audit event and revokes all existing sessions. It does not reactivate a deactivated account. Keep server access limited to trusted operators.

## Release acceptance

Before exposing real customer data:

- Check `docker compose ... ps`: application health checks must pass.
- Open the HTTPS site, sign in, create and convert a lead, advance/win a deal, complete a task and resolve a support ticket. Verify the records remain after a container restart.
- Check invitation acceptance, read-only permissions, sales representative visibility and cross-workspace isolation. Verify secure cookies and HTTPS redirection in the browser.
- Exercise upload/download, filtered exports and invalid-row imports; check downloads retain their content.
- Run Playwright against an isolated staging installation: `PLAYWRIGHT_BASE_URL=https://YOUR_STAGING_DOMAIN npm run test:e2e` from `frontend`. Public signup must be enabled only on this disposable staging installation for the tests, which create isolated workspaces.
- Take a backup and perform the restore drill below. Monitor `/api/v1/health/ready` through the frontend proxy, disk usage, failed logins and error logs.

Run dependency advisory checks in a connected environment (`npm audit --omit=dev --audit-level=high` for the frontend, and your Python vulnerability scanner against the locked runtime snapshot). The local npm advisory request was blocked by registry DNS failure; no clean vulnerability result is claimed.

Do not label a deployment verified solely because Compose parsed successfully. Credentials, DNS and a real host are still required to run these checks.

## Back up database and attachments

Stop API writers for a short maintenance window. Copy the complete data directory while stopped, restart service, then create a validated snapshot from that copy. Use a new snapshot path every time. These commands run from the project root:

```sh
mkdir -p backups
chmod 700 backups
task_staging=$(mktemp -d)
docker compose --env-file deploy/production.env -f docker-compose.production.yml stop api
docker compose --env-file deploy/production.env -f docker-compose.production.yml cp api:/data/. "$task_staging"
docker compose --env-file deploy/production.env -f docker-compose.production.yml start api
python3 scripts/backup.py create --database "$task_staging/relay.db" --uploads "$task_staging/uploads" --output "backups/$(date -u +%Y%m%dT%H%M%SZ)" --writers-stopped
```

If copying fails, restart the API and retry the backup; never report a backup successful from an incomplete copy. Delete the temporary copy after verifying the snapshot. `--writers-stopped` confirms the source was copied while writers were stopped; it does not stop services itself.

The tool uses SQLite's backup API, verifies integrity/foreign keys, copies only referenced attachments, and checks their sizes and SHA-256 digests. It refuses existing destinations and does not leave a partial snapshot on failure. Keep daily snapshots and a pre-upgrade snapshot; choose retention to meet your business obligations. Encrypt off-host copies, restrict access, and test recovery regularly. The manifest detects corruption, not malicious replacement; protect backup authenticity through storage access controls.

## Restore drill and rollback

```sh
python3 scripts/backup.py verify --source backups/YOUR_SNAPSHOT
python3 scripts/backup.py restore --source backups/YOUR_SNAPSHOT --output restore-staging/YOUR_NEW_DIRECTORY
```

The destination must not exist. A successful restore produces `relay.db` plus `uploads/`, with private permissions. First use that directory in an **isolated staging instance** with the same application version that wrote the backup. Run database checks and the release journey before any production switch.

To replace production after a verified drill, stop application containers and preserve the original data volume. Provision a new volume, copy the restored directory into it, set ownership to UID/GID 10001, and point the API volume at it. Start one API instance and check readiness, then start the frontend. Never restore over a running database or discard the old volume until validation succeeds. Restoring an older snapshot loses changes after that snapshot; confirm the intended recovery point before switching.

For upgrades, retain the previous source/image release and make a snapshot before starting new code. Startup applies new numbered migrations and checks checksums of applied migrations. Do not edit applied migrations. If an upgrade fails, restore the old snapshot to a new volume and run the old release; rolling back code alone cannot safely reverse schema changes.

## References

The TLS configuration follows [Caddy HTTPS guidance](https://caddyserver.com/docs/quick-starts/https) and [reverse proxy documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy). Snapshot creation uses the [SQLite backup API](https://www.sqlite.org/backup.html). These references describe mechanisms; they are not evidence this deployment has been exercised.
