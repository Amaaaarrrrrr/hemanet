# Contributing to HemaNet

## Phase discipline

HemaNet is built incrementally in the numbered phases defined in
[docs/blueprint/13-delivery-plan.md §AE](docs/blueprint/13-delivery-plan.md). Each phase follows:

**plan → implement → test → review → demonstrate → owner approval → commit → stop.**

- Implement only the approved phase. Do not add future functionality early.
- Every meaningful feature ships with tests and documentation updates.
- A phase is committed only after the project owner's explicit `APPROVED — COMMIT`.
- The next phase starts only when explicitly instructed.
- Track progress in [docs/development-status.md](docs/development-status.md).

## Source of truth

- The [blueprint](docs/blueprint/00-README.md) and the [ADRs](docs/adr/README.md) define the
  architecture. Don't introduce technologies that contradict them.
- A significant new decision needs a new ADR (copy `docs/adr/ADR-000-template.md`).
- Clinical rules are versioned configuration (ADR-005), never hardcoded. If a clinical rule is
  uncertain, stop, document the assumption and ask. Don't invent it.

## Git workflow

- Work on `develop`. Never modify `main` without explicit approval.
- One logical commit per completed phase, using
  [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`,
  `docs:`, `test:`…).
- No force pushes, history rewrites, resets of others' work or branch deletion.
- Before a phase: `git status` and `git branch --show-current`.
- At the end of a phase: `git status`, `git diff --stat` and `git diff`.

## Never commit

`.env` files, passwords, API keys, JWT secrets, database credentials, private keys/certificates,
personal tokens, production secrets, or **any real donor or patient data**. Only `.env.example`
(with obvious placeholders) is tracked. CI runs gitleaks on every push.

## Checks

Run `make check` before asking for review: ruff, ruff format, import-linter, mypy (strict),
pytest (against real PostgreSQL; needs `make up`), bandit, pip-audit, eslint, prettier, tsc
(strict), vitest and npm audit. Backend conventions every module must follow are in
[docs/backend-foundation.md](docs/backend-foundation.md).
