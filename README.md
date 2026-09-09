# Short Research

Research-first YouTube Shorts generator that turns a topic into a factual, high-retention **9:16 production package**, critiques it before video generation, and can optionally hand the result to **ArcReel**.

The project focuses on the part most text-to-video systems handle poorly: **research, angle selection, hooks, retention structure, concrete visual direction, packaging, and quality control before expensive generation begins.**

## Full pipeline

```text
topic
  ↓
web research + source extraction
  ↓
factual research brief
  ↓
5 competing story angles
  ↓
5 hooks per angle (25 total)
  ↓
scored winner
  ↓
script + timed scene direction
  ↓
AI critic
  ├─ hook
  ├─ pacing
  ├─ visual novelty
  ├─ escalation
  ├─ payoff
  └─ factual discipline
  ↓
automatic targeted rewrite loop
  ↓
title + thumbnail variants
  ↓
ArcReel-ready screenplay
  ↓
OPTIONAL ArcReel push / workflow trigger
  ↓
OPTIONAL finished-video critique
```

## Completed milestones

- [x] AI critic that scores hook, pacing, visual novelty and payoff
- [x] automatically rewrite weak scripts below a configurable retention threshold
- [x] multiple competing hooks/angles before choosing one
- [x] YouTube/reference-video analysis
- [x] channel style presets
- [x] cost-aware model routing
- [x] thumbnail/title variants
- [x] direct ArcReel generation workflow trigger
- [x] post-render critique using the finished video

## Setup

Requirements:

- Python 3.11+
- `ffmpeg` + `ffprobe` for visual reference analysis and post-render critique

```bash
git clone git@github.com:khysokhorn/Short-Research.git
cd Short-Research
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -e .
cp .env.example .env
```

Configure any provider implementing an OpenAI-compatible `/chat/completions` endpoint:

```env
SHORT_RESEARCH_LLM_BASE_URL=https://your-provider.example/v1
SHORT_RESEARCH_LLM_API_KEY=...
SHORT_RESEARCH_LLM_MODEL=your-default-model
```

## Generate a full Short package

```bash
short-research generate \
  "Why your brain freezes when you eat ice cream too fast" \
  --duration 45 \
  --preset micro-disaster
```

No ArcReel request is made unless `--push-arcreel` or `--trigger-arcreel` is explicitly supplied.

Typical output:

```text
output/<story-slug>/
├── research-brief.json
├── angle-competition.json
├── short-package.json
├── short-critique.json
├── packaging-variants.json
├── run-summary.json
├── llm-usage.json
└── arcreel-screenplay.md
```

If a reference video is supplied, `reference-analysis.json` is also written.

## Angle + hook competition

Before the full script is written, the pipeline generates five genuinely different story angles and five hooks per angle. Each hook is scored for:

- curiosity
- clarity
- visual potential
- truthfulness
- overall strength

The selected angle/hook becomes a hard constraint for the script writer rather than being silently replaced later.

## Critic + rewrite loop

The full script is scored for:

- hook strength
- pacing
- visual novelty
- escalation
- payoff
- factual discipline
- scene-level retention/clarity

Default behavior:

```bash
--critic-threshold 78
--rewrite-passes 2
```

If the score is below the threshold, the critic's concrete priorities are passed to a rewrite model. The result is critiqued again until it passes or the rewrite limit is reached.

## Channel presets

Built-ins:

```text
micro-disaster
cinematic-fact
horribly-wrong
luxury-experiment
dark-mystery
```

List them:

```bash
short-research list-presets
```

Use one:

```bash
short-research generate \
  "Why hiccups happen" \
  --preset micro-disaster
```

You can also pass a path to your own JSON preset.

## Reference-video analysis

Analyze a YouTube URL or local video for **abstract** reusable structure: hook mechanics, pacing, visual changes and retention devices. The analyzer is instructed not to copy exact wording, characters or shot sequences.

Transcript/metadata analysis:

```bash
short-research analyze-reference "https://www.youtube.com/shorts/..."
```

Include sampled frames (requires a vision-capable configured model + ffmpeg):

```bash
short-research analyze-reference \
  "https://www.youtube.com/shorts/..." \
  --visual
```

Use a reference directly during generation:

```bash
short-research generate \
  "A $30,000 cookie experiment" \
  --preset luxury-experiment \
  --reference "https://www.youtube.com/shorts/..." \
  --reference-visual
```

## Cost-aware model routing

By default every task uses `SHORT_RESEARCH_LLM_MODEL`. Optionally provide task-specific candidates through `SHORT_RESEARCH_MODEL_ROUTES_JSON`.

The router estimates preflight cost and chooses the highest-quality candidate that fits `SHORT_RESEARCH_MAX_LLM_USD_PER_CALL`. If none fit, it falls back to the cheapest configured candidate.

Tasks include:

```text
research
angle_competition
script
critic
rewrite
packaging
reference_analysis
post_render_critic
```

Each run writes `llm-usage.json` with chosen models and available token usage.

## Title + thumbnail variants

After the final critic pass, the pipeline produces:

- 5 title variants with scores/reasons
- 4 thumbnail concepts
- image-generation prompts
- short mobile-friendly overlay text
- recommended title/thumbnail indices

See `packaging-variants.json`.

## ArcReel integration

Configure your self-hosted ArcReel:

```env
ARCREEL_BASE_URL=http://localhost:8000
ARCREEL_TOKEN=
```

Upload the screenplay only:

```bash
short-research generate \
  "Why your brain freezes" \
  --preset micro-disaster \
  --push-arcreel
```

Upload and start ArcReel's actual `/video-workflow` project assistant:

```bash
short-research generate \
  "Why your brain freezes" \
  --preset micro-disaster \
  --trigger-arcreel
```

The integration creates a `9:16` drama project with `source_kind=screenplay`, uploads the Markdown source, reads ArcReel's authoritative `/workflow-plan`, then starts the project assistant. It does **not** bypass ArcReel blockers or user-choice gates.

## Post-render critique

After ArcReel or another renderer produces the final video:

```bash
short-research critique-render \
  output/brain-freeze-emergency/short-package.json \
  final-short.mp4
```

The tool samples frames and scores:

- first-frame strength
- visual continuity
- readability
- pacing
- match to the planned story

It outputs `post-render-critique.json` including edit recommendations and scene indices worth regenerating.

## Basic/legacy mode

If you only want the original research → script flow:

```bash
short-research generate "topic" --basic
```

## Worked example

See [`examples/brain-freeze`](examples/brain-freeze/) for the original staged example showing research → brief → package → ArcReel screenplay without pushing to ArcReel.

## Design principles

1. **Research before writing.** Scripts inherit facts rather than inventing them.
2. **Compete before committing.** Generate multiple angles/hooks before spending effort on scenes.
3. **Hook before context.** No greetings or slow introductions.
4. **Visual specificity.** Avoid useless instructions such as “show relevant B-roll.”
5. **Retention is structural.** Escalation and pattern interrupts are designed into scenes.
6. **Critique before generation.** Cheap reasoning should catch weak scripts before Veo/Seedance/Kling credits are spent.
7. **Respect uncertainty.** The critic checks factual discipline as well as entertainment value.
8. **Keep output portable.** JSON remains the canonical production package; ArcReel is one renderer/integration.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```
