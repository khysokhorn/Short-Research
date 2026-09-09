# Short Research

Research-first YouTube Shorts generator that turns a topic into a factual, high-retention **9:16 screenplay** and can push it directly into a self-hosted **ArcReel** project.

The goal is to solve the part that video generators usually do poorly: **finding the strongest angle, building a hook, structuring retention beats, and writing concrete visual direction before expensive video generation starts.**

## MVP pipeline

```text
topic
  ↓
web search + page extraction
  ↓
research brief (facts / surprises / uncertainty)
  ↓
Shorts writer + visual director
  ↓
scene-by-scene package
  ├── short-package.json
  └── arcreel-screenplay.md
             ↓
       optional ArcReel push
```

## What it produces

Each run contains:

- sourced research brief
- 1.5-second hook
- core story angle and payoff
- full voiceover
- timed scene plan
- concrete visual and camera direction
- retention/pattern-interrupt notes
- sound/on-screen-text suggestions
- YouTube title, description and hashtags
- ArcReel-compatible screenplay source (`.md`)

## Setup

```bash
git clone git@github.com:khysokhorn/Short-Research.git
cd Short-Research
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -e .
cp .env.example .env
```

Configure any provider that implements an OpenAI-compatible `/chat/completions` endpoint:

```env
SHORT_RESEARCH_LLM_BASE_URL=https://your-provider.example/v1
SHORT_RESEARCH_LLM_API_KEY=...
SHORT_RESEARCH_LLM_MODEL=your-model-name
```

## Generate a Short

```bash
short-research generate \
  "Why a batch of laboratory-grade cookies could cost $30,000" \
  --duration 45 \
  --style "cinematic science story with escalating absurdity"
```

Output:

```text
output/<story-slug>/short-package.json
output/<story-slug>/arcreel-screenplay.md
```

## Push directly to ArcReel

ArcReel can ingest screenplay source files. Configure your self-hosted server:

```env
ARCREEL_BASE_URL=http://localhost:8000
ARCREEL_TOKEN=
```

Then:

```bash
short-research generate \
  "Why your brain freezes when you eat ice cream too fast" \
  --duration 45 \
  --style "funny microscopic body disaster" \
  --push-arcreel
```

The integration creates a 9:16 `drama` project with `source_kind=screenplay`, then uploads the generated Markdown source.

## Design principles

1. **Research before writing.** The script should inherit facts, not invent them.
2. **Hook before context.** No greetings or slow introductions.
3. **Visual specificity.** Avoid useless instructions like “show relevant B-roll.”
4. **Retention is structural.** Add escalation/pattern interrupts every few seconds rather than relying only on captions.
5. **Cheap thinking before expensive generation.** Approve the story plan before spending Veo/Seedance/Kling credits.
6. **Keep the output portable.** JSON is the canonical package; ArcReel is one renderer/integration.

## Next milestones

- [ ] AI critic that scores hook, pacing, visual novelty and payoff
- [ ] automatically rewrite scenes below a retention threshold
- [ ] multiple competing hooks/angles before choosing one
- [ ] YouTube/reference-video analysis
- [ ] channel style presets
- [ ] cost-aware model routing
- [ ] thumbnail/title variants
- [ ] direct ArcReel generation workflow trigger
- [ ] post-render critique using the finished video

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```
