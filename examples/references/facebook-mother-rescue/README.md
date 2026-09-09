# Facebook reference example

Reference URL:

```text
https://www.facebook.com/share/r/1GgwfBeYvX/
```

This example was verified against the real public Facebook Reel using the project's URL/video-analysis path.

## What was verified

- the Facebook share URL resolves through `yt-dlp` without login cookies
- the Reel resolves to Facebook video ID `979388545192999`
- duration is about 30 seconds
- the video can be downloaded as a vertical MP4
- eight frames can be sampled with FFmpeg and passed to the reference-analysis LLM stage
- the Reel exposes no subtitles/automatic captions, so visual analysis is much more useful than metadata-only analysis

## Run it

```bash
short-research analyze-reference \
  "https://www.facebook.com/share/r/1GgwfBeYvX/" \
  --visual
```

Or use it while generating a new, unrelated story:

```bash
short-research generate \
  "YOUR NEW STORY IDEA" \
  --reference "https://www.facebook.com/share/r/1GgwfBeYvX/" \
  --reference-visual
```

The reference should influence only high-level mechanics such as danger-first opening, action/reaction pacing, false resolution, second uncertainty, and emotional payoff. It should not copy the original characters, rescue plot, exact shots, poses, or distinctive designs.

See [`reference-analysis.json`](reference-analysis.json) for a manually verified abstraction of the Reel's structure.
