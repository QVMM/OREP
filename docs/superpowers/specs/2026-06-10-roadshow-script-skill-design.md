# Roadshow Script Skill Design

## Goal

Upgrade OREP roadshow PPT notes from short per-page remarks into a competition-ready presentation script. The first production version targets vocational-skills competition roadshows with a default 60-minute run time and about 8,000 Chinese characters across the full deck.

## Scope

- Applies only to roadshow PPT generation.
- Does not change database schema in the first version.
- Keeps existing `speaker_notes` compatibility so the current editor and PPT export can continue to work.
- Writes a richer script artifact beside the generated PPT project for later UI and data-model upgrades.

## Product Standard

The generated script must feel like a team speaking to judges, not a page analysis note. It should include:

- A full-session story arc: problem, solution, implementation, field proof, results, value, close.
- Per-page speaker assignment, time budget, target character count, stage action, transition, scoring focus, and short version.
- Natural roadshow language with rhythm, emphasis, and judge-facing persuasion.
- Live-demo handoff language on operation, test, code, and device pages.
- Strict removal of internal planning words such as page, layout, proof object, field, visual, placeholder, and prompt labels.

## Architecture

### New Backend Module

Create `roadshow_script_skill.py` under the PPT agent orchestrator package.

Responsibilities:

- Parse slide-structured manuscript pages.
- Extract page fields such as title, visible content, story role, speaker goal, stage mode, time budget, and existing `speaker_notes`.
- Build a session brief with target duration and target character budget.
- Ask the LLM for a structured full-script JSON artifact.
- Validate page count, page indexes, script length, and forbidden meta language.
- Fall back to deterministic script generation if LLM output is invalid.
- Write `roadshow_script_skill.json` and `roadshow_script_quality_report.json`.
- Rewrite each page's `speaker_notes` field in the manuscript.

### Pipeline Integration

Call the skill near the end of `roadshow_agent.analyze_materials`, after manuscript hard-quality repair passes and before writing `roadshow_final_manuscript.md`.

The skill must never change page count, page type, titles, visible content, asset references, or visual contracts. It only replaces `speaker_notes` values and creates side artifacts.

### Frontend Compatibility

For the first version:

- Increase per-page notes editor limit from 1,000 to 4,000 characters.
- Show current character count against the larger limit.
- Keep existing save endpoints.

### Storage Compatibility

No schema migration in V1. Existing persistence already stores per-page notes up to 4,000 characters. The richer artifact is stored in the PPT project directory for debugging and future UI.

## Output Contract

The script artifact shape:

```json
{
  "version": 1,
  "targetDurationSec": 3600,
  "targetWordCount": 8000,
  "actualWordCount": 8120,
  "pages": [
    {
      "pageIndex": 1,
      "title": "项目封面",
      "speaker": "主讲人A",
      "durationSec": 75,
      "targetChars": 170,
      "emotion": "稳重开场",
      "script": "正式可朗读讲稿",
      "transitionOut": "自然转场",
      "stageActions": ["面向评委", "指向屏幕项目名"],
      "scoringPoints": ["项目定位", "应用场景"],
      "shortVersion": "30秒压缩版"
    }
  ],
  "qualityReport": {
    "passed": true,
    "findings": []
  }
}
```

## Quality Gate

A generated page fails quality if:

- It has no readable script.
- It contains internal planning language.
- It is shorter than a safe minimum for non-cover pages.
- It omits handoff language on live demo, test, code, or device pages.
- It repeats the same opening pattern across many consecutive pages.

The full artifact fails quality if:

- Page count differs from the manuscript.
- Total character count is far from the target without a reason.
- Fewer than two speaker roles appear on decks with live-demo pages.
- No stage actions are produced.

## Development Steps

1. Add this design document.
2. Implement `roadshow_script_skill.py` with LLM generation, validation, fallback, artifact writing, and manuscript rewriting.
3. Integrate it into `roadshow_agent.py`.
4. Raise frontend and preview note limits to 4,000 characters.
5. Verify with static compilation and a deterministic sample.
6. Use sample roadshow material for a real-generation smoke test when API credentials and runtime are available.

## Non-Goals

- No new database table in V1.
- No full script overview editor in V1.
- No automatic TTS or rehearsal scoring in V1.
- No changes to visual page rendering contracts beyond improved notes.
