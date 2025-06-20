# PurposePath Story Engine

> **Awaken human potential through generative mythic storytelling.**

---

## 📜 Project Overview

A modular, AI‑driven narrative platform that synthesises avatars, stories, and soul‑mapping data in real‑time. Players cross the **ASK • SEEK • KNOCK** threshold, craft a personalised anime‑style hero, and experience an emergent saga shaped by every choice.

---

## 🗺️ High‑Level Architecture

```
┌────────────────────────────────┐
│  Liminal Ritual  (SPR‑TR01)   │
│  intentVector seed            │
└────────────┬───────────────────┘
             │
┌────────────▼──────────────┐    ┌───────────────────────────┐
│  Avatar Creator (SPR‑AV01)│───►│  AvatarSeed & Assets      │
└────────────┬──────────────┘    └───────────────────────────┘
             │
┌────────────▼──────────────┐
│   Soul Map API (SPR‑SM01) │◄─── Player choices + intent
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│ Story Engine (SPR‑ST01)   │→ Scenes, Checkpoints
└───────────────────────────┘
             │
┌────────────▼──────────────┐
│ Codex Orchestrator (SPR‑CO01) │→ Task routing / validation
└───────────────────────────┘
```

---

## 🗂️ Repository Structure

| Path        | Module              | Sprint | Notes                     |
| ----------- | ------------------- | ------ | ------------------------- |
| `/ritual/`  | Liminal sequence    | TR01   | Ritual UI + embeddings    |
| `/avatar/`  | Avatar Creator      | AV01   | Three.js viewer, sliders  |
| `/soulmap/` | Soul Map service    | SM01   | Trait API + visualizer    |
| `/story/`   | Narrative engine    | ST01   | GPT‑4o scene pipeline     |
| `/codex/`   | Orchestration layer | CO01   | Agents, queue, validators |
| `/docs/`    | Specs & diagrams    | —      | Markdown & images         |

---

## 🔗 Data Contract Quick‑Links

* [`intentVector`](docs/contracts/intentVector_v1.md)
* [`AvatarSeed`](docs/contracts/avatarSeed_v1.md)
* [`SoulMapVector`](docs/contracts/soulMap_v1.md)

Contracts are **versioned**; breaking changes require bumping `_vX` suffix and updating integration tests.

---

## 🛠️ Local Development

1. `git clone …`
2. `cp .env.sample .env` → fill DB & S3 creds.
3. `docker-compose up` (spins Postgres, pgvector, minio, inference‑GPU stub).
4. Visit `http://localhost:3000` for the React front‑end scaffold.

> **Note**: Without a GPU you can export `USE_CPU_STUBS=true` to run text‑only mocks.

---

## 🚀 Running Sprint Modules

| Sprint | Start Script                | Primary Service                   |
| ------ | --------------------------- | --------------------------------- |
| TR01   | `pnpm dev --filter ritual`  | Ritual UI @ `localhost:3001`      |
| AV01   | `pnpm dev --filter avatar`  | Avatar Creator @ `localhost:3002` |
| SM01   | `pnpm dev --filter soulmap` | Soul Map API @ `localhost:8000`   |
| ST01   | `pnpm dev --filter story`   | Story Engine @ `localhost:8001`   |
| CO01   | `pnpm dev --filter codex`   | Orchestrator @ `localhost:9000`   |

Codex automatically stubs missing upstream APIs; once a sprint lands, flip the feature flag in `codex/config.yaml`.

### CO01 Orchestrator Quickstart
Run:
```bash
python run_codex.py
```
Visit `http://localhost:9000/tasks` for task status.


---

## 🧪 Tests & CI

* **Unit tests**: `pnpm test` (Vitest)
* **Contract tests**: `pnpm test:contracts` (runs JSON‑schema validation)
* **End‑to‑end**: `pnpm test:e2e` (Playwright, mocked avatar render)
* CI pipeline lives in `.github/workflows/ci.yml` and triggers on PRs to `main`.

---

## 🔄 Sprint Tracking

* Kanban board: `docs/kanban.md` (auto‑generated)
* Task list: `docs/sprint_tasks.md` (mirrors ChatGPT canvas)

Update status by pushing commits with one of:

```
git commit -m "TR01-UI ✅ complete ritual interface"
```

Codex parses commit messages to move tasks between **To Do → In Progress → Done**.

---

## 🤝 Contributing Workflow

1. Create branch: `git checkout -b sprint/<ID>-<your_task>`
2. Code & commit following the task key.
3. Open PR → auto‑tests run.
4. Codex validator comments on schema / asset compliance.
5. Merge after 1 approval + green CI.

---

## 📖 Glossary

| Term             | Definition                                                              |
| ---------------- | ----------------------------------------------------------------------- |
| **intentVector** | 768‑dim embedding of player intent harvested during ASK • SEEK • KNOCK. |
| **AvatarSeed**   | JSON descriptor of player avatar + asset hashes.                        |
| **SoulMap**      | Multidimensional vector of evolving traits & archetypes.                |

---

> *“You do not merely design your hero — you remember them.”*
