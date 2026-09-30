# Development status

Phases follow [blueprint §AE](blueprint/13-delivery-plan.md). Each phase is committed only after
the project owner's explicit approval.

| Step | Phase | Status |
|---|---|---|
| 1 | **E0**: repository, compose stack, CI skeleton, ADRs | **Awaiting approval** |
| 2 | E1.1–1.7: backend foundation | Not started |
| 3 | E1.8–1.9: frontend shell & design system | Not started |
| 4 | E4.1: audit | Not started |
| 5 | E2.1–2.5, 2.8: authentication | Not started |
| 6–24 | See blueprint §AE | Not started |

## E0: Repository & tooling

**Gate:** the compose stack starts (postgres, api, worker, frontend, mailpit) and CI is green.

Delivered:
- Monorepo layout (`backend/`, `frontend/`, `infra/`, `docs/`), README, CONTRIBUTING,
  `.editorconfig`, `.gitignore`, `.env.example`
- `compose.yaml` for Docker Compose and podman-compose; backend and frontend Dockerfiles; Makefile
- CI workflow (`.github/workflows/ci.yml`): backend and frontend quality gates, security audits,
  gitleaks, container-stack smoke test
- ADR-001 to ADR-018 accepted and recorded individually; ADR-019 (tooling baseline) added

Placeholders to be replaced in E1: `backend/wsgi.py`, `backend/worker.py`, `frontend/src/App.tsx`.
