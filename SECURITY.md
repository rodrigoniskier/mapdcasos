# Security Policy

Security fixes are applied to the current `main` branch.

## Student and academic data

MAPD Casos can contain student identifiers, progress and assessment results. Real datasets, database backups and exported analytics with identifiable students must not be committed to the public repository.

## Secrets

Gemini/API credentials, Django secret keys, database credentials and deployment tokens belong only in environment variables or approved secret stores.

## Application safeguards

- Preserve server-side authorization checks; UI visibility is not an authorization boundary.
- Keep CSRF/session protections and rate limits enabled in production.
- Keep AI request limits, circuit breakers and kill switches active.
- Use anonymized identifiers in technical logs.
- Validate backup files before restoration and restrict access to production backups.
- Use synthetic data for screenshots, demos and tests.

Report vulnerabilities privately through GitHub Security Advisories / Private Vulnerability Reporting when available.
