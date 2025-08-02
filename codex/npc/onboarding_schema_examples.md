# NPC Onboarding Schema Examples

This document provides examples of NPC onboarding schemas for the story engine.

## Basic Onboarding Choice

```json
{
  "choices": {
    "1": {
      "text": "Welcome Lyra the archer to your companions",
      "next": "scene_lyra_recruited",
      "npc_onboard": "lyra",
      "npc_trust_deltas": {
        "lyra": 0.2
      }
    }
  }
}
```

## Conditional Onboarding

```json
{
  "choices": {
    "1": {
      "text": "Ask Lyra to join your quest",
      "next": "scene_lyra_joins",
      "npc_onboard": "lyra",
      "conditions": {
        "trust": 0.5,
        "emotion": "peace",
        "emotion_value": 0.3,
        "not_companion": true
      },
      "npc_trust_deltas": {
        "lyra": 0.15
      }
    }
  }
}
```

## Multiple NPC Onboarding

```json
{
  "choices": {
    "1": {
      "text": "Invite both Lyra and Orin to join",
      "next": "scene_group_joins",
      "npc_onboard": ["lyra", "orin"],
      "npc_trust_deltas": {
        "lyra": 0.1,
        "orin": 0.1
      }
    }
  }
}
```

## Trust-Based Onboarding

```json
{
  "choices": {
    "1": {
      "text": "Request Lyra's aid in battle",
      "next": "scene_lyra_battle_help",
      "npc_onboard": "lyra",
      "conditions": {
        "trust": 0.7,
        "not_companion": true
      },
      "npc_trust_deltas": {
        "lyra": 0.25
      }
    }
  }
}
``` 