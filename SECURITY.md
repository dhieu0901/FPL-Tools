# Security policy

## Reporting

Do not publish personal data, credentials, FPL sessions, database dumps or
vulnerability details. Report them directly to a VMF administrator.

## Production requirements

- Replace every sample secret and password before deploying.
- Administrators must use strong passwords; two-factor support is the first
  hardening step after the MVP.
- Phone numbers and Facebook URLs appear only in authenticated admin APIs.
- Never write access tokens, session cookies or raw personal data to logs.
- PostgreSQL backups must be encrypted and their restore path tested.
- Every score override, disciplinary action and Gameweek reopen must be
  audited.
