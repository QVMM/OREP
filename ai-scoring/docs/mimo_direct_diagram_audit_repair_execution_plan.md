# MiMo Direct Page + AI Diagram Pass + Multimodal Visual Audit + Targeted Repair

## Product Position

This plan replaces the stopped schema-driven local renderer branch.

The product goal is not to make the system draw the PPT body with local templates. The goal is to let MiMo design the page body while the system prevents the common failures that make AI-generated PPT HTML unusable:

- diagram overlap;
- SVG overflow;
- text too small;
- chart/diagram hierarchy unclear;
- page crop/cut-off;
- nested canvas or web-component feel;
- excessive blank space;
- fake screenshots;
- poor evidence placeholders;
- repeated page layouts.

## Core Principle

MiMo owns design. The system owns constraints, inspection, and repair routing.

The system should not generate the final body as a fixed renderer. It should:

- define safe canvas boundaries;
- ask MiMo to separate complex diagram tasks;
- review diagram screenshots and page screenshots;
- return precise repair reasons;
- reject bad pages before preview is finalized.

## New Pipeline

### 1. Page Design Intent Pass

Input:

- full outline;
- current page content;
- previous and next page roles;
- deck palette and typography;
- shell body canvas size;
- competition context;
- scoring/evidence requirements.

MiMo outputs:

- page role;
- body composition intent;
- professional expression type;
- text blocks;
- diagram tasks if needed;
- evidence/photo placeholders if needed;
- risk notes for density or image requirements.

Important boundary:

- MiMo may choose layout freely.
- MiMo must not output a fixed local template ID.
- MiMo must declare which regions are diagram-heavy and require separate diagram generation.

### 2. AI Diagram Pass

Complex visual regions are generated separately before final page assembly.

Diagram candidates:

- architecture diagram;
- process flow;
- timeline;
- Gantt-like plan;
- comparison matrix;
- data dashboard;
- risk radar;
- route map;
- evidence chain;
- system/data screenshot explanation.

Each diagram task includes:

- diagram type;
- body region size;
- minimum font size;
- maximum node count;
- node hierarchy;
- relationships and arrow directions;
- required labels;
- optional callouts;
- color palette;
- visual style constraints;
- forbidden patterns.

MiMo generates the diagram as SVG/HTML fragment for that exact region.

Critical rule:

- If a diagram contains many nodes, MiMo must simplify, group, or split the diagram. It must not shrink text below readability or allow overlap.

### 3. Diagram Screenshot Audit

Each generated diagram is rendered alone and audited before entering the page.

Audit checks:

- SVG/HTML does not overflow its region;
- no node overlap;
- no arrow-label collisions;
- text is readable;
- hierarchy is clear;
- main visual object is large enough;
- diagram is not decorative filler;
- diagram does not look like a generic web icon/card set;
- diagram fits the intended professional expression type.

Audit implementation:

- deterministic DOM/SVG checks for obvious geometry problems;
- screenshot artifact capture;
- multimodal AI review for visual clarity and professional quality.

If failed:

- only the diagram is repaired;
- the whole page is not regenerated unless the page composition itself is the cause.

### 4. Page Assembly Pass

After diagram-level acceptance, MiMo assembles the full body region:

- title/subtitle/footer shell remains system-owned;
- body region is MiMo-owned;
- accepted diagram fragments can be placed into the body;
- text blocks and evidence placeholders are arranged around the diagram.

MiMo must obey:

- body canvas bounds;
- minimum font sizes;
- no repeated page title inside body;
- no full-body white board or nested canvas;
- no upload/dropzone controls;
- no fake real-world photo;
- no evidence placeholder that looks like a web form;
- no bottom crop/cut-off.

### 5. Full Page Multimodal Visual Audit

The final page is screenshot and audited as a PPT page.

Audit checks:

- does it look like a formal competition PPT page;
- visual focus is clear;
- body region has breathing room;
- diagram and text do not fight each other;
- no overflow/crop/cut-off;
- no nested canvas;
- no major blank area unless intentional;
- image/evidence placeholders are appropriate;
- professional diagram type is fulfilled;
- page does not look like a template clone of nearby pages.

Audit result categories:

- `pass`: can enter preview;
- `repair_diagram`: diagram failed but page layout is acceptable;
- `repair_layout`: composition failed;
- `repair_copy`: text content or duplication failed;
- `repair_evidence`: placeholder/evidence area failed;
- `manual_review`: uncertain or high-risk.

### 6. Targeted Repair Pass

Repair prompts must be specific and visual:

- "The architecture diagram overflows the lower boundary; keep the same concept but reduce node count and group database/storage nodes."
- "The SVG arrows overlap labels; reroute arrows around node groups."
- "The page has a nested canvas: remove the inner large white board and use the shell body directly."
- "The data chart is too small; make it the primary visual and reduce text cards."
- "The bottom explanation is cropped; reflow body vertically and keep 56px safe bottom margin."

No repair may route to a fixed local fallback template.

## Prompt Changes Required

### Page Prompt

Add:

- You own only the body area, not the shell title/footer.
- You may freely compose the body, but must declare complex diagram tasks.
- Do not create a full-body panel, giant white board, or nested canvas.
- Do not repeat the page title inside the body.
- Do not fake real-world photos or screenshots.
- If real-world material is needed, create a PPT evidence placeholder with material type, recommended ratio, crop purpose, and scoring purpose.

### Diagram Prompt

Add:

- Generate only the diagram region.
- Fit within the exact region size.
- No overflow.
- No overlap.
- Minimum readable font size.
- Use grouping if node count is high.
- Prefer professional PPT diagram language over cartoon icons.
- Return self-check notes explaining how overlap and overflow were avoided.

### Repair Prompt

Add:

- Keep successful parts unchanged.
- Fix only the named failure.
- Do not switch to a different generic layout.
- Do not introduce a local-template-like structure.
- Explain what changed and why it resolves the failure.

## Code Modules To Build

### P0: Stop Template Drift

- Mark schema renderer branch as stopped.
- Ensure it is not called by production/preview paths.
- Keep existing isolated artifacts only as negative learning and audit examples.

### P1: Diagram Task Extraction

Create a module that identifies when a page needs a separate diagram task.

Suggested file:

- `app/services/ppt/v5/ai_diagram_task_planner.py`

Inputs:

- page blueprint;
- enriched content;
- body canvas;
- deck theme;
- professional expression type.

Output:

- zero or more diagram tasks;
- reason for each task;
- risk level.

### P2: Diagram Prompt Builder

Suggested file:

- `app/services/ppt/v5/ai_diagram_prompt_builder.py`

Responsibilities:

- build prompt for a single diagram region;
- include dimensions and safety rules;
- include professional style requirements;
- include competition/evidence context;
- require self-check metadata.

### P3: Diagram Artifact Runner

Suggested file:

- `app/services/ppt/v5/ai_diagram_runner.py`

Responsibilities:

- call MiMo for diagram fragment;
- write diagram raw output;
- parse and sanitize fragment;
- render standalone screenshot;
- track retries and timeouts.

### P4: Diagram Visual Auditor

Suggested files:

- `app/services/ppt/v5/diagram_dom_auditor.py`
- `app/services/ppt/v5/diagram_multimodal_auditor.py`

Responsibilities:

- deterministic overflow/overlap/readability checks;
- screenshot-based multimodal review;
- return targeted repair reason.

### P5: Page Visual Auditor

Extend existing audit modules instead of replacing MiMo body design.

Suggested files:

- `app/services/ppt/v5/ppt_page_visual_auditor.py`
- `app/services/ppt/v5/multimodal_page_reviewer.py`

Checks:

- crop/cut-off;
- nested canvas;
- blank ratio;
- visual focus;
- evidence placeholder quality;
- diagram clarity;
- page-level PPT quality.

### P6: Targeted Repair Orchestrator

Suggested file:

- `app/services/ppt/v5/targeted_visual_repair.py`

Responsibilities:

- route failures to diagram repair or page repair;
- cap repair attempts;
- preserve successful fragments;
- never use fixed fallback template;
- record failure and timeout state honestly.

## Validation Strategy

### Isolated Diagram Tests

Use hand-authored pages that stress diagrams:

- dense architecture page;
- flow with many arrows;
- long timeline;
- evidence page with system screenshot + data table;
- chart-heavy results page.

### Real Questionnaire Regression

Run at least:

- wisdom agriculture questionnaire;
- one non-agriculture vocational project;
- one evidence-heavy practical operation project.

Success is measured by screenshots, not only structure.

### Human Review Gate

Before product promotion:

- contact sheet review;
- page-by-page notes;
- compare MiMo direct without diagram pass vs new pipeline;
- confirm the new pipeline improves diagram safety without making pages templated.

## Acceptance Criteria

The new path is only valid if:

- MiMo remains the primary body designer;
- diagram regions no longer commonly overlap/overflow;
- pages remain visually diverse;
- screenshots look closer to final PPT than local renderer prototypes;
- failed diagrams/pages are repaired by targeted MiMo prompts;
- no fixed local fallback template is introduced.

## Immediate Next Steps

1. Freeze schema renderer branch and do not continue v11 repairs.
2. Update production planning to use MiMo Direct + AI Diagram Pass.
3. Implement only an isolated diagram task planner/prompt builder first.
4. Test with 3 to 5 diagram-heavy pages before touching the full PPT chain.
5. Add multimodal visual audit before any preview is considered acceptable.

