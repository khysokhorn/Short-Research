# Brain Freeze — Complete Pipeline Example

This folder materializes one full `short-research` run so you can inspect every stage **without pushing anything to ArcReel**.

## Input

```bash
short-research generate \
  "Why your brain freezes when you eat ice cream too fast" \
  --duration 45 \
  --style "funny microscopic body disaster"
```

`--push-arcreel` is intentionally omitted.

## Stage map

```text
00-input.md
   │
   ▼
01-research-sources.md        WebResearcher.search()
   │
   ▼
02-research-brief.json        _build_research_brief()
   │
   ▼
03-short-package.json         _build_short_package()
   │
   ├──────────────► canonical structured output
   │
   ▼
04-arcreel-screenplay.md      export_package() / to_arcreel_screenplay()
   │
   X  STOP HERE

No ArcReel project is created and no source file is uploaded.
```

## What to inspect

### 1. `00-input.md`
The exact creative request and runtime constraints.

### 2. `01-research-sources.md`
The search/research stage. This is intentionally summarized rather than copying full source articles.

### 3. `02-research-brief.json`
The research editor turns the sources into:

- core angle
- verified facts
- surprising facts
- stakes/tension
- uncertainties

The important part is `uncertainties`: brain freeze has a leading explanation, but the exact mechanism is still debated, so the writer must not turn the leading theory into absolute fact.

### 4. `03-short-package.json`
The writer/director converts the research into the actual 45-second Short:

- hook
- payoff
- full narration
- characters
- scene timing
- visual direction
- camera direction
- captions
- sound design
- transitions
- retention devices
- YouTube metadata

This JSON is the canonical portable output.

### 5. `04-arcreel-screenplay.md`
The same package converted into a human-readable screenplay format ArcReel can accept later.

## Expected behavior

This example demonstrates the design rule of the project:

> research facts first → write for retention second → generate expensive video last.

The final script can dramatize the mechanism visually, but the narration still says the mechanism is the **leading explanation**, not proven certainty.
