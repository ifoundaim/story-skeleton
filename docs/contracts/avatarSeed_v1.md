# AvatarSeed v1

A lightweight JSON document describing a generated avatar and its associated assets.

## Fields
- `playerId` — ID of the owning player.
- `prompt` — text prompt used for generation.
- `clipVector` — 768 float values derived from CLIP.
- `hair`, `eyes`, `body`, `outfit`, `accessories` — slider values between 0 and 1.
- `glbUrl` — URL to the avatar model (GLB).
- `pngUrl` — URL to the rendered sprite.
