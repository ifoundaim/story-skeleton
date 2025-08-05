# SPR-NPC06 – Dynamic NPC Seed Generator & Profile Factory

## Overview

The Dynamic NPC Seed Generator & Profile Factory creates unique, story-specific NPC profiles dynamically at story initialization. NPCs are generated in alignment with the player's intent and archetype to deepen narrative personalization and replayability.

## Implementation Summary

### ✅ Completed Features

1. **LLM-Powered NPC Generation**
   - Uses OpenAI GPT-4o for intelligent NPC creation
   - Generates NPCs based on player archetype and soul map data
   - Includes fallback NPCs when LLM is unavailable

2. **Rich NPC Metadata**
   - Extended NPC model with comprehensive metadata fields
   - Stores roles, archetypes, personality traits, narrative hooks
   - Includes relationship to player, motivation, and secrets

3. **Database Integration**
   - New database migration (npc03_extend_npc_metadata)
   - Persistent storage of generated NPCs
   - Integration with existing NPC and soul map systems

4. **API Endpoints**
   - `POST /npc/generate` - Generate dynamic NPCs
   - `GET /npc/{npc_id}` - Get detailed NPC information
   - `GET /npc/list` - List all NPCs in the system

5. **Comprehensive Testing**
   - Unit tests for all major functionality
   - Demo scripts showcasing different scenarios
   - Fallback mechanisms for reliability

## Architecture

### Core Components

#### 1. DynamicNPCGenerator Class (`backend/npc/dynamic_generator.py`)

```python
class DynamicNPCGenerator:
    """Generates NPC profiles using LLM prompts based on player data."""
    
    async def generate_npc_profiles(
        self,
        player_id: str,
        player_name: str,
        player_archetype: str,
        story_theme: str,
        num_npcs: int = 3,
        db: Session = None
    ) -> List[NPC]:
```

**Key Features:**
- LLM prompt engineering for NPC generation
- Soul map integration for personalized NPCs
- Fallback NPC templates for reliability
- Database persistence of generated NPCs

#### 2. Extended NPC Model (`backend/npc/models.py`)

```python
class NPC(Base):
    __tablename__ = 'npc'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    baseline_trust = Column(Float, nullable=False, default=0.0)
    trust = Column(Float, nullable=False, default=0.0)
    # Extended metadata for dynamic NPC generation
    role = Column(String, nullable=True)  # e.g., 'Mentor', 'Rival', 'Companion'
    archetype = Column(String, nullable=True)  # e.g., 'Sage', 'Warrior', 'Trickster'
    personality_traits = Column(JSON, nullable=True, default=list)
    narrative_hooks = Column(JSON, nullable=True, default=list)
    relationship_to_player = Column(String, nullable=True)
    motivation = Column(String, nullable=True)
    secrets = Column(JSON, nullable=True, default=list)
    generated = Column(String, nullable=True)  # Flag for dynamically generated NPCs
```

#### 3. Database Migration (`backend/migrations/versions/npc03_extend_npc_metadata.py`)

Adds the new metadata columns to the NPC table:
- `role` - NPC's role in the story
- `archetype` - NPC's personality archetype
- `personality_traits` - List of personality characteristics
- `narrative_hooks` - Story hooks for plot development
- `relationship_to_player` - How NPC relates to player
- `motivation` - What drives the NPC
- `secrets` - Hidden information about the NPC
- `generated` - Flag indicating dynamic generation

### API Endpoints

#### Generate NPCs
```http
POST /npc/generate
Content-Type: application/json

{
  "player_id": "player_123",
  "player_name": "Alex",
  "player_archetype": "Hero",
  "story_theme": "Epic Quest",
  "num_npcs": 3
}
```

**Response:**
```json
{
  "success": true,
  "npcs_generated": 3,
  "npc_ids": ["uuid1", "uuid2", "uuid3"],
  "message": "Successfully generated 3 NPCs for Alex"
}
```

#### Get NPC Details
```http
GET /npc/{npc_id}
```

**Response:**
```json
{
  "id": "uuid",
  "full_name": "Elder Thorne",
  "baseline_trust": 0.7,
  "trust": 0.7,
  "role": "Mentor",
  "archetype": "Sage",
  "personality_traits": ["Wise", "Patient", "Mysterious"],
  "narrative_hooks": ["Knows ancient secrets", "Tests the player's worthiness"],
  "relationship_to_player": "Guiding mentor figure",
  "motivation": "To prepare the next generation of heroes",
  "secrets": ["Was once a great warrior", "Knows the player's destiny"],
  "generated": "true"
}
```

#### List All NPCs
```http
GET /npc/list
```

**Response:**
```json
{
  "npcs": [
    {
      "id": "uuid",
      "full_name": "Elder Thorne",
      "role": "Mentor",
      "archetype": "Sage",
      "trust": 0.7,
      "generated": "true"
    }
  ]
}
```

## Usage Examples

### 1. Basic NPC Generation

```python
from npc.dynamic_generator import generate_story_npcs

# Generate NPCs for a player
npcs = await generate_story_npcs(
    player_id="player_123",
    player_name="Alex",
    player_archetype="Hero",
    story_theme="Epic Quest",
    num_npcs=3
)

# Access generated NPC data
for npc in npcs:
    print(f"{npc.full_name} - {npc.role}")
    print(f"Motivation: {npc.motivation}")
    print(f"Secrets: {len(npc.secrets)} hidden")
```

### 2. Integration with Story Engine

```python
# During story initialization
async def initialize_story(player_id: str, player_name: str, archetype: str, theme: str):
    # Generate dynamic NPCs
    npcs = await generate_story_npcs(
        player_id=player_id,
        player_name=player_name,
        player_archetype=archetype,
        story_theme=theme,
        num_npcs=3
    )
    
    # Use NPCs in story generation
    story_context = {
        "npcs": [npc.full_name for npc in npcs],
        "npc_roles": {npc.full_name: npc.role for npc in npcs},
        "npc_hooks": {npc.full_name: npc.narrative_hooks for npc in npcs}
    }
    
    return story_context
```

### 3. Fallback NPC Templates

When LLM is unavailable, the system uses predefined NPC templates:

**Hero Archetype NPCs:**
- Elder Thorne (Mentor/Sage) - Wise mentor figure
- Captain Valen (Rival/Warrior) - Competitive rival

**Sage Archetype NPCs:**
- Luna Bright (Apprentice/Explorer) - Eager student

**Explorer Archetype NPCs:**
- Raven Swift (Companion/Explorer) - Fellow adventurer

## LLM Prompt Engineering

The system uses sophisticated prompts to generate NPCs:

```python
prompt = f"""
You are a master character designer for an interactive story game. Generate {num_npcs} unique NPC profiles that will interact with the player.

PLAYER CONTEXT:
- Name: {player_name}
- Archetype: {player_archetype}
- Story Theme: {story_theme}
- Dominant Soul Traits: {', '.join(dominant_traits)}

NPC GENERATION RULES:
1. Create NPCs that complement or challenge the player's archetype
2. Each NPC must have a clear role in the story
3. Trust baselines should reflect the NPC's initial disposition toward the player
4. Include narrative hooks that can drive story progression
5. Ensure NPCs align with the story theme

REQUIRED OUTPUT FORMAT (JSON):
{{
  "npcs": [
    {{
      "id": "unique_npc_id",
      "full_name": "NPC Full Name",
      "role": "NPC's role in the story",
      "archetype": "NPC's personality archetype",
      "baseline_trust": 0.0-1.0,
      "personality_traits": ["trait1", "trait2", "trait3"],
      "narrative_hooks": ["hook1", "hook2"],
      "relationship_to_player": "How this NPC relates to the player",
      "motivation": "What drives this NPC",
      "secrets": ["secret1", "secret2"]
    }}
  ]
}}
"""
```

## Testing and Validation

### Demo Scripts

1. **`scripts/demo_npc_generation.py`** - Comprehensive demo showing different player archetypes
2. **`scripts/test_npc_api.py`** - API functionality testing

### Unit Tests

- **`backend/tests/test_dynamic_npc_generator.py`** - Comprehensive test suite covering:
  - LLM integration
  - Fallback mechanisms
  - Database operations
  - Prompt engineering
  - Error handling

### Test Scenarios

The system has been tested with various player archetypes:
- **Hero** - Generates mentor and rival NPCs
- **Sage** - Generates apprentice NPCs
- **Explorer** - Generates companion NPCs

## Database Schema

### NPC Table Structure

```sql
CREATE TABLE npc (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR NOT NULL,
    baseline_trust FLOAT NOT NULL DEFAULT 0.0,
    trust FLOAT NOT NULL DEFAULT 0.0,
    role VARCHAR,
    archetype VARCHAR,
    personality_traits JSON DEFAULT '[]',
    narrative_hooks JSON DEFAULT '[]',
    relationship_to_player VARCHAR,
    motivation VARCHAR,
    secrets JSON DEFAULT '[]',
    generated VARCHAR
);
```

### Migration History

1. **npc01_init_npc_state** - Initial NPC state table
2. **npc02_create_npc_table** - Core NPC table
3. **npc03_extend_npc_metadata** - Extended metadata fields
4. **Merge migration** - Combined with soul map migrations

## Integration Points

### 1. Soul Map Integration
- Uses player's soul map traits to influence NPC generation
- Extracts dominant traits for personalized NPC creation
- Maintains consistency with player's psychological profile

### 2. Story Engine Integration
- NPCs can be referenced in story generation
- Narrative hooks drive plot development
- Trust levels affect story outcomes

### 3. Trust System Integration
- Generated NPCs have baseline trust values
- Trust can be modified through player interactions
- Trust affects NPC dialogue and behavior

## Configuration

### Environment Variables

```bash
# Required for LLM generation
OPENAI_API_KEY=your_openai_api_key

# Database connection
POSTGRES_URL=postgresql://postgres:pass@localhost:5432/purposepath
```

### Fallback Configuration

When `OPENAI_API_KEY` is not set, the system automatically falls back to predefined NPC templates, ensuring the system remains functional.

## Performance Considerations

1. **LLM Rate Limiting** - Implemented proper error handling for API limits
2. **Database Efficiency** - Uses UUID-based lookups for fast retrieval
3. **Caching** - NPCs are stored persistently to avoid regeneration
4. **Async Operations** - All LLM calls are asynchronous for better performance

## Future Enhancements

1. **NPC Evolution** - NPCs could evolve based on story progression
2. **Relationship Dynamics** - Complex NPC-to-NPC relationships
3. **Cultural Context** - NPCs could reflect different cultural backgrounds
4. **Memory Integration** - NPCs could remember past interactions
5. **Voice Generation** - Integration with TTS for NPC voices

## Troubleshooting

### Common Issues

1. **Database Connection** - Ensure PostgreSQL is running and accessible
2. **LLM API** - Check OpenAI API key and rate limits
3. **Migration Errors** - Run `alembic upgrade head` to apply migrations
4. **Import Errors** - Ensure all dependencies are installed

### Debug Commands

```bash
# Check database status
docker-compose ps db

# Run migrations
cd backend && alembic upgrade head

# Test NPC generation
python scripts/demo_npc_generation.py

# Check API endpoints
curl -X GET "http://localhost:8000/npc/list"
```

## Conclusion

The Dynamic NPC Seed Generator & Profile Factory successfully implements the requirements for SPR-NPC06:

✅ **LLM-generated NPC profiles** based on strict logic rules (roles, alignment, trust)  
✅ **Stores generated profiles** in the database at ritual initialization  
✅ **Integrates with player archetype** and soul map data  
✅ **Provides fallback mechanisms** for reliability  
✅ **Includes comprehensive testing** and documentation  

The system is ready for production use and provides a solid foundation for dynamic, personalized NPC generation in interactive storytelling applications. 