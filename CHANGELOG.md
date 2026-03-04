# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Root `.gitignore` for Python, tests, DB, logs, and IDE/OS artifacts.
- `ARCHITECTURE.md` describing data flow, components, and design choices.
- `CHANGELOG.md` (this file).

### Changed

- **Backend**
  - Database sessions use a context manager (`get_db_session`) so sessions are always closed and transactions committed or rolled back.
  - All upload outcomes (including scan and storage errors) are written to the audit log.
  - Upload endpoint returns HTTP 400 for client errors (file too large, unsupported type) and 500 for server errors (scan/storage), with body `{ "detail": { "status", "reason" } }`.
  - Timestamps stored in UTC using `datetime.now(timezone.utc)` (timezone-aware).
  - Dependencies in `requirements.txt` pinned to compatible version ranges.
- **Frontend**
  - Upload handler checks `response.ok` and parses error body from `detail` for 4xx/5xx.
  - Logs table built with `DocumentFragment` and a single append for better performance.
  - Log and result text escaped for HTML to prevent XSS.

### Fixed

- Session leak risk when exceptions occurred during log or query.
- Missing audit log entries for scan and storage failures.
- Deprecation of `datetime.utcnow` by using timezone-aware UTC.

---

## [0.1.0] — Initial

- FastAPI backend with `/upload` and `/logs`.
- DLP detector with regex policies (email, password, phone).
- SQLite audit log and local “cloud” storage.
- Dashboard with upload and log viewer.
