# PurposePath Story Engine

> **Awaken human potential through generative mythic storytelling.**

## 🎯 Recent Sprint Completions

### ✅ Story Tree Validator & Auto-Healing System (SPR-VALID01) - COMPLETED
**Automated Story Tree Validation & Auto-Healing System**
- **Status:** ✅ **COMPLETED** 
- **Date:** January 2025
- **Key Features:**
  - Automated story tree validation with comprehensive issue detection
  - Auto-healing system that fixes common story tree problems
  - Integration into story generation pipeline with logging
  - Development-only validation endpoint for testing
  - Comprehensive unit tests for validation and healing logic
  - CI integration with GitHub Actions validation workflow

**Technical Implementation:**
- **Core Validator:** `codex/validate/story_validator.py` - `validate()` and `auto_heal()` functions
- **Generator Integration:** `purpose_agents/generate_story.py` - Validation hook after story generation
- **API Endpoint:** `backend/main.py` - `/validate` endpoint for development testing
- **Testing:** `backend/tests/test_story_validation.py` - Comprehensive test suite
- **CI Integration:** `.github/workflows/validate-story.yml` - GitHub Actions validation workflow
- **Module Structure:** `codex/validate/__init__.py` - Clean module exports

**Validation Features:**
- **Issue Detection:** Duplicate tags, missing text/choices, undefined targets, orphaned scenes
- **Auto-Healing:** Placeholder text insertion, missing node creation, choice relinking
- **Aggressive Pruning:** Optional removal of unreachable nodes
- **Performance:** Sub-100ms runtime on typical 200-node trees
- **Safety:** Only heals at generation time, never mutates in-play trees
- **Logging:** Comprehensive warning and error logging for debugging

**Validation Checks:**
- **Structural Integrity:** Missing intro_001, duplicate tags, invalid node structures
- **Content Completeness:** Missing text, placeholder text detection
- **Choice Validity:** Missing choice text, undefined next targets
- **Reachability:** Orphaned scenes not reachable from intro_001
- **Data Consistency:** Required fields presence and type validation

---

### ✅ Soul Map v2 Sprint (SM02) - COMPLETED
**Unify on 64-Dimensional Vector System**
- **Status:** ✅ **COMPLETED** 
- **Date:** January 2025
- **Key Features:**
  - Canonical 64-trait enum with organized trait categories
  - Unified 64-dimensional vector system replacing fragmented approaches
  - Database model with pgvector integration and proper indexing
  - Service layer with CRUD operations and delta clipping
  - FastAPI router with RESTful endpoints
  - Main app integration and story engine updates
  - Comprehensive test suite with numpy float precision handling
  - Legacy high-level soulmap service deprecation

**Technical Implementation:**
- **Core Mapping:** `backend/soulmap/mapping.py` - 64-trait enum and vector utilities
- **Database Model:** `backend/soulmap/db.py` - SoulMap model with pgvector column
- **Service Layer:** `backend/soulmap/service.py` - Business logic with delta clipping
- **API Router:** `backend/soulmap/router.py` - REST endpoints for soulmap operations
- **Main Integration:** `backend/main.py` - Soulmap delta processing in choice system
- **Story Engine:** `story/engine.py` - Updated HTTP calls to new endpoints
- **Migration:** `backend/migrations/versions/sm02_update_soulmap_table.py` - Database schema
- **Testing:** `backend/tests/test_soulmap_v2.py` - Comprehensive integration tests
- **Legacy Cleanup:** Removed `soulmap/main.py` and old utility files

**64 Trait Categories:**
- **Core Virtues** (0-7): COURAGE, COMPASSION, WISDOM, CREATIVITY, JUSTICE, TEMPERANCE, RESILIENCE, EMPATHY
- **Shadow Traits** (8-15): FEAR, PRIDE, APATHY, SHADOW_BLEND_1-5
- **Motivations** (16-23): SELFACTUALIZATION, EXTERNALVALIDATION, COLLECTIVE, MOTIVATION_BLEND_1-5
- **Archetypes** (24-31): HERO, REBEL, SAGE, CAREGIVER, MAGICIAN, LOVER, SOVEREIGN, EXPLORER
- **Archetype Blends** (32-39): ARCHETYPE_BLEND_1-8
- **Cognitive Functions** (40-47): INTROVERTED/EXTRAVERTED variants of THINKING, FEELING, SENSING, INTUITING
- **Attachment Styles** (48-51): SECURE, ANXIOUS, AVOIDANT, DISORGANIZED
- **Psychological Needs** (52-59): AUTONOMY, COMPETENCE, RELATEDNESS, SELFCONTROL, MINDFULNESS, GRIT, CURIOSITY, PLAYFULNESS
- **Social Traits** (60-63): OPTIMISM, VIGILANCE, SOCIALDOMINANCE, HUMILITY

**API Endpoints:**
- `GET /v1/soulmap/player/{player_id}` - Retrieve soulmap as trait dictionary
- `PATCH /v1/soulmap/update` - Apply delta with `{player_id, delta:{trait:float}}`
- `GET /v1/soulmap/health` - Health check endpoint

---

### ✅ Fallback NPC Bundle & ENV Switch Sprint (NPC07) - COMPLETED
**Zero-Cost Development Mode with Deterministic NPC Profiles**
- **Status:** ✅ **COMPLETED** 
- **Date:** January 2025
- **Key Features:**
  - Environment flag `USE_FALLBACK_NPCS` for zero-cost development mode
  - Deterministic fallback bundle with 8 pre-defined NPC profiles
  - Factory pattern `get_seed_npcs()` with environment-driven behavior
  - Idempotent NPC seeding (no duplicates on multiple runs)
  - Comprehensive unit tests for fallback functionality
  - Integration with existing NPC profile system

**Technical Implementation:**
- **Fallback Bundle:** `dev_assets/fallback_npcs.json` - 8 deterministic NPC profiles
- **Settings:** `backend/settings.py` - Pydantic BaseSettings with environment loading
- **Factory:** `backend/npc/profile_seed.py` - `get_seed_npcs()` and `seed_fallback_npcs()`
- **Integration:** `backend/main.py` - Fallback seeding in `/start` endpoint
- **Testing:** `backend/tests/test_fallback_seed.py` - Comprehensive test suite
- **Documentation:** `env.example` - Environment variable documentation

**Fallback NPC Profiles:**
- **Lyra Orinova** (Explorer) - Resourceful sky-sailor who trades secrets for starlight maps
- **Orin Kael** (Guardian) - Veteran guardian driven by an oath to protect the innocent
- **Mira Sagewind** (Healer) - Wandering herbalist whose calm presence hides a quick wit
- **Dante Firn** (Artificer) - Technomancer tinkering with relic machines of a lost age
- **Selene Waveborn** (Mystic) - Runaway noble mastering tide-binding water rites
- **Thorne Ironsoul** (Redeemer) - Stoic warrior seeking redemption for past misdeeds
- **Caelis Skydancer** (Courier) - Free-spirited courier racing lightning across cloud-rails
- **Auri Nightsong** (Minstrel) - Shadow bard weaving truths into forbidden lullabies

**Environment Configuration:**
- **Flag:** `USE_FALLBACK_NPCS=true` - Enables fallback mode (default: false)
- **Behavior:** When enabled, skips LLM calls and uses deterministic NPC bundle
- **Idempotency:** Running multiple times creates no duplicate NPC rows
- **Integration:** Works seamlessly with existing NPC trust and dialogue systems

---

### ✅ NPC Profile Helper Sprint (NPC02) - COMPLETED
**Backend Safeguard for NPC Profile Creation**
- **Status:** ✅ **COMPLETED** 
- **Date:** July 2025
- **Key Features:**
  - Automatic NPC profile creation for all NPCs referenced in scenes
  - Support for both explicit `npc_profile` blocks and `npcs_present` fallback
  - Integration in `/start` endpoint and `_choose_py` function
  - Generator instruction for consistent NPC profile blocks
  - Comprehensive unit tests for profile creation logic
  - Idempotent operation (safe to call multiple times)

**Technical Implementation:**
- **Core Helper:** `backend/npc/profile_seed.py` - `ensure_npc_profile()` function
- **Integration:** `backend/main.py` - Helper calls in story endpoints
- **Generator Rules:** `purpose_agents/agent_backend.py` - NPC profile instruction
- **Testing:** `backend/tests/test_profile_seed.py` - Comprehensive test suite
- **Database:** Uses existing NPC service functions for profile creation
- **Backward Compatibility:** Works with existing `npcs_present` arrays

**Profile Helper Features:**
- **Automatic Detection:** Scans scenes for NPC references in multiple formats
- **Profile Creation:** Creates minimal NPC profiles with default values
- **Metadata Support:** Handles recruitable flags and default trust values
- **Error Handling:** Graceful handling of invalid data and database errors
- **Generator Integration:** Ensures consistent NPC profile blocks in new stories

---

### ✅ Soulmap Integration Sprint (SM01) - COMPLETED
**Player Choice Data Capture & Real-time Soulmap Updates**
- **Status:** ✅ **COMPLETED** 
- **Date:** July 2025
- **Key Features:**
  - Player choices now generate `soulmap_delta` values (64-element vectors)
  - Real-time soulmap updates in database when choices are made
  - Soulmap widget displays actual data instead of placeholder text
  - Comprehensive debug logging for integration tracking
  - Story generation includes soulmap delta fields for new stories

**Technical Implementation:**
- Backend: `backend/main.py` - `_choose_py` function with soulmap integration
- Story Generation: `purpose_agents/generate_story.py` - Added soulmap_delta fields
- Database: Soulmap vectors updated via PostgreSQL with pgvector
- Frontend: SoulMapWidget now shows real-time soulmap data

---

### ✅ Memory Recap System Sprint (MEM01) - COMPLETED
**Short-Term Memory Recap System for Codex**
- **Status:** ✅ **COMPLETED** 
- **Date:** July 2025
- **Key Features:**
  - Enhanced memory recap builder in `codex/memory/recap_builder.py`
  - Emotion vector trend analysis and inclusion in recaps
  - NPC name extraction and interaction tracking
  - Choice pattern detection and narrative integration
  - Memory persistence with JSON storage and timestamp tracking
  - API endpoint `/memory/{player_id}` for memory retrieval
  - Frontend memory widget with "🧠 View Memory" button

**Technical Implementation:**
- **Core Module:** `codex/memory/recap_builder.py` - Enhanced narrative recap generation
- **Memory Storage:** `codex/memory/memory_state.json` - Persistent memory with timestamps
- **API Integration:** `backend/main.py` - Memory endpoint using enhanced codex memory system
- **Frontend:** `frontend/src/scenes/SceneView.tsx` - Memory widget with toggle functionality
- **Testing:** `tests/backend/test_memory.py` - Comprehensive test suite for memory functionality
- **Agent Integration:** `codex/agents.py` - MEM01 agent for sprint tracking

**Memory Features:**
- **Narrative Generation:** Creates ~300-word 3rd-person narrative recaps
- **Emotion Analysis:** Extracts and includes emotion trends from scene history
- **NPC Tracking:** Identifies and mentions key NPC interactions
- **Choice Patterns:** Detects and describes player choice approaches
- **Word Limiting:** Intelligent truncation respecting sentence boundaries
- **Persistence:** Automatic saving and retrieval of memory state

---

### ✅ NPC Trust System Sprint (NPC01) - COMPLETED
**Dynamic NPC Trust Tracking & Relationship Management**
- **Status:** ✅ **COMPLETED** 
- **Date:** July 2025
- **Key Features:**
  - Database-driven NPC trust system with PostgreSQL storage
  - Real-time trust updates based on player choices
  - Trust clamping (0.0 to 1.0 range) with automatic bounds checking
  - NPC state persistence with metadata and last-seen tracking
  - Frontend trust meter visualization in dialogue components
  - Comprehensive API for trust management and retrieval

**Technical Implementation:**
- **Database:** `npc_state` table with migration (`npc01_init_npc_state.py`)
- **Models:** `NPCState` model with trust, name, and metadata fields
- **API Endpoints:** `GET /npc/{player_id}`, `POST /npc/update`
- **Service Layer:** `apply_trust()` function with automatic clamping
- **Integration:** Trust updates integrated into story choice system
- **Frontend:** `Dialogue.tsx` component with trust meter visualization
- **Testing:** Comprehensive test suite in `tests/backend/test_npc.py`
- **Agent Integration:** `codex/agents.py` - NPC01 agent for sprint tracking

**Trust System Features:**
- **Dynamic Updates:** Trust changes based on choice `trust_delta` values
- **Automatic Clamping:** Trust values automatically bounded between 0.0 and 1.0
- **NPC Persistence:** Individual NPC states stored per player
- **Metadata Support:** Flexible JSON metadata for future NPC features
- **Real-time Integration:** Seamless integration with story choice system

---

### ✅ Emotion Engine Sprint (EMO01) - COMPLETED
**8-Dimensional Emotion Vector System & Real-time Tracking**
- **Status:** ✅ **COMPLETED** 
- **Date:** July 2025
- **Key Features:**
  - 8-dimensional emotion vector (joy, grief, awe, fear, desire, disgust, peace, rage)
  - Real-time emotion updates based on player choices
  - Emotion vector clamping and normalization
  - Emotion state persistence with change logging
  - Frontend radar chart visualization of emotional state
  - Comprehensive emotion delta integration

**Technical Implementation:**
- **Core Models:** `EmotionState` with 8-dimensional vector and change log
- **API Endpoints:** `GET /emotion/{player_id}` - Retrieve emotion state
- **Integration:** Emotion deltas applied during story choices
- **Frontend:** `EmotionGraph.tsx` with radar chart visualization
- **Persistence:** JSON-based emotion state storage with change history
- **Testing:** Test suite in `tests/backend/test_emotion.py`
- **Agent Integration:** `codex/agents.py` - EMO01 agent for sprint tracking

**Emotion System Features:**
- **Multi-dimensional Tracking:** 8 distinct emotion dimensions
- **Change History:** Log of emotion changes with scene context
- **Visual Analytics:** Radar chart visualization of current emotional state
- **Automatic Clamping:** Emotion values normalized to [-1.0, 1.0] range
- **Choice Integration:** Emotion deltas applied based on story choices

---

## 📜 Project Overview

A modular, AI‑driven narrative platform that synthesises avatars, stories, and soul‑mapping data in real‑time. Players cross the **ASK • SEEK • KNOCK** threshold, craft a personalised anime‑style hero, and experience an emergent saga shaped by every choice.

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
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│ Narrative Media (SPR‑MEDIA01) │→ Images, Audio, S3
└────────────┬──────────────┘
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
| `/media/`   | Media generation    | MEDIA01| Images, audio, S3 storage |
| `/codex/`   | Orchestration layer | CO01   | Agents, queue, validators |
| `/codex/memory/` | Memory system    | MEM01  | Recap builder + persistence |
| `/backend/npc/` | NPC Trust system  | NPC01  | Trust tracking + API      |
| `/backend/npc/profile_seed.py` | NPC Profile Helper | NPC02  | Automatic profile creation |
| `/backend/emotion/` | Emotion engine | EMO01  | 8D emotion vectors        |
| `/docs/`    | Specs & diagrams    | —      | Markdown & images         |

### Soul Map API

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/v1/soulmap/player/{player_id}` | Retrieve trait dictionary |
| PATCH | `/v1/soulmap/update` | Apply delta with trait dictionary |
| GET | `/v1/soulmap/health` | Health check endpoint |

---

## 🔗 Data Contract Quick‑Links

* [`intentVector`](docs/contracts/intentVector_v1.md)
* [`AvatarSeed`](docs/contracts/avatarSeed_v1.md)
* [`SoulMapVector`](docs/contracts/soulMap_v1.md)
* [`SceneMedia`](docs/contracts/sceneMedia_v1.md)

Contracts are **versioned**; breaking changes require bumping `_vX` suffix and updating integration tests.

---

## 🛠️ Local Development

1. `git clone …`
2. `cp .env.sample .env` → fill DB & S3 creds.
3. `docker-compose up` (spins Postgres, pgvector, minio, inference‑GPU stub).
4. Visit `http://localhost:3000` for the React front‑end scaffold.

> **Note**: Without a GPU you can export `USE_CPU_STUBS=true` to run text‑only mocks.

---

## 🚀 Running Sprint Modules

| Sprint | Start Script                | Primary Service                   |
| ------ | --------------------------- | --------------------------------- |
| TR01   | `pnpm dev --filter ritual`  | Ritual UI @ `localhost:3001`      |
| AV01   | `pnpm dev --filter avatar`  | Avatar Creator @ `localhost:3002` |
| SM01   | `pnpm dev --filter soulmap` | Soul Map API @ `localhost:8000`   |
| SM02   | `python -m backend.main`    | Soul Map v2 API @ `localhost:8000`   |
| ST01   | `pnpm dev --filter story`   | Story Engine @ `localhost:8001`   |
| MEDIA01| `pnpm dev --filter media`   | Media Generator @ `localhost:8002`|
| CO01   | `pnpm dev --filter codex`   | Orchestrator @ `localhost:9000`   |
| MEM01  | `python run_codex.py`       | Memory System (integrated)        |
| NPC01  | `python -m backend.main`    | NPC Trust API (integrated)        |
| EMO01  | `python -m backend.main`    | Emotion Engine (integrated)       |

Codex automatically stubs missing upstream APIs; once a sprint lands, flip the feature flag in `codex/config.yaml`.

### CO01 Orchestrator Quickstart
Run:
```bash
python run_codex.py
```
Visit `http://localhost:9000/tasks` for task status.


---

## 🧪 Tests & CI

* **Unit tests**: `TESTING=1 pytest` (Backend) / `npm test` (Vitest)
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

Codex parses commit messages to move tasks between **To Do → In Progress → Done**.

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
| **SceneMedia**   | Media assets (images, audio) associated with story scenes.              |

---

## Soul Map System v1 (SM01) ✅ **COMPLETED**

### Backend
- **Table:** `soul_map` (id UUID PK, player_id TEXT, vector pgvector(64), updated_at TIMESTAMP)
- **API:**
  - `GET /soulmap/{player_id}` → returns current vector (list[float]) or zero-vector
  - `POST /soulmap/update` with `{player_id, delta: list[float]}` → adds delta, clips [-1,1], saves row
- **Vector math:** See `backend/soulmap/vector_utils.py`
- **Migration:**
  - Run `alembic upgrade head` in `backend/` to create the table (requires pgvector extension)
- **Player Choice Integration:**
  - Story choices now include `soulmap_delta` fields (64-element float vectors)
  - Automatic soulmap updates when players make choices via `_choose_py` function
  - Real-time soulmap vector updates with clipping and vector math operations

### Frontend
- **SoulMapWidget:**
  - Located in `frontend/src/scenes/SoulMapWidget.tsx`
  - Fetches `/soulmap/{playerId}` and displays a radar chart of the first 8 vector traits using [recharts](https://recharts.org/)
  - Mounted in the sidebar of `SceneView`
  - **Now displays actual soulmap data** instead of "No soul map data yet"

### Story Generation Integration
- **Choice Deltas:** Story choices in `purpose_agents/generate_story.py` now include `soulmap_delta` values
- **Real-time Updates:** Player choices immediately update the soulmap vector in the database
- **Debug Logging:** Comprehensive logging tracks soulmap integration process

### Tests
- See `backend/tests/test_soulmap.py` for vector math and API endpoint tests

### Dev Notes
- Ensure Postgres is running and accessible at the connection string in `backend/alembic.ini`
- If you change the vector size, update both backend and frontend accordingly
- **Sprint Status:** ✅ **COMPLETED** - Player choice data capture and real-time soulmap updates are fully functional

---

## Narrative Media Layer v1 (MEDIA01)

### Backend
- **Package:** `backend/media/` - Media generation and S3 management
- **Generator:** `backend/media/generator.py` - OpenAI Image API + Suno audio generation
- **S3 Utils:** `backend/utils/s3.py` - Asset upload/download with minio support
- **Codex Router:** `purpose_agents/codex_router.py` - Media task enqueuing and processing
- **API Endpoints:**
  - `GET /media/status/{task_id}` → returns task status
  - `GET /media/result/{task_id}` → returns generated media URLs
- **Scene Integration:** All scene responses now include `media` field with `images[]` and `audio[]` arrays

### Frontend
- **SceneView Updates:**
  - Lazy-loads first scene image with loading states
  - Audio playback controls with play/pause functionality
  - Graceful fallback when media fails to load
- **Media Handling:**
  - Images: Automatic loading with error handling
  - Audio: HTML5 Audio API with loop support
  - Responsive design for different screen sizes

### Configuration
- **Environment Variables:**
  - `USE_CPU_STUBS=true` - Bypass real APIs for development
  - `S3_BUCKET_NAME` - S3 bucket for media storage
  - `S3_ENDPOINT_URL` - Minio endpoint for local development
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - S3 credentials

### Constraints
- **File Size Limits:** Images ≤5MB JPG, Audio ≤10MB MP3
- **Graceful Degradation:** Scenes render text-only if media generation fails
- **Async Processing:** Media generation happens in background via Codex router

### Tests
- **Backend:** `backend/tests/test_media.py` - Generator, router, and integration tests
- **Frontend:** `frontend/src/scenes/__tests__/SceneView.test.tsx` - Media UI tests
- **Coverage:** Media generation, S3 uploads, error handling, and UI interactions

### Dev Notes
- Media generation is queued automatically when scenes are created/advanced
- Use `USE_CPU_STUBS=true` for development without API costs
- S3/minio integration supports both local development and production

---

> *"You do not merely design your hero — you remember them."*
