# Silent rescue story mode

Use the `silent-rescue` preset for dialogue-free animated rescue stories where visual cause-and-effect and continuity matter more than narration.

```bash
short-research generate \
  "A mother hen must lead three distinct chicks through one connected orchard route while wildfire closes in" \
  --duration 30 \
  --preset silent-rescue
```

The generated `ShortPackage` includes a continuity bible plus per-scene story state:

- `start_state -> obstacle -> decision -> action -> consequence -> end_state`
- exact `characters_present`
- character positions
- location
- screen direction
- stable global `location_map`
- global `continuity_rules`

The critic applies a **WHY-NEXT** test between adjacent scenes: the next beat must happen because of the previous beat. It also scores causality, character consistency, spatial continuity, silent readability, and emotional payoff.

For silent rescue mode, narration and on-screen text are forced empty after generation and rewrite. The final ArcReel screenplay exports the continuity bible and all scene-state fields so downstream image/video generation has explicit continuity constraints.
