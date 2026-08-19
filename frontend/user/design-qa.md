# 首页视觉还原 QA

- source visual truth path: `/var/folders/gh/b2f_yv7j1y3dx23jh8835rb80000gn/T/codex-clipboard-b82a812d-6603-440a-a45a-f5e13e1c6157.png`
- source implementation reference: `http://127.0.0.1:8765/user/index.html`
- implementation URL: `http://localhost:5174/`
- implementation screenshot path: `/Users/liuyixing/项目/OREP/frontend/user/.design-qa/home-implementation-final.png`
- normalized comparison path: `/Users/liuyixing/项目/OREP/frontend/user/.design-qa/home-comparison.png`
- viewport: desktop; implementation capture `1910 × 1075`; source crop normalized to the same content aspect ratio for full-view comparison
- state: light theme, authenticated student, current training day with real database data

## Full-view comparison evidence

The final desktop composition follows the prototype's measured CSS geometry: `40px` page margin, `16px` section gap, `156px` hero, `308px / 310px` content rows, `320px` right rail, `18px` card radius, `18px 20px` card padding, and the prototype's `2px 4px 12px rgba(0,0,0,.08)` card shadow. The right rail starts beside the hero and the first two content cards, matching the source hierarchy instead of appearing as a third column below a full-width hero.

## Focused region comparison evidence

The hero, progress card, today card, and right rail were checked with browser-rendered bounding boxes and computed styles. A separate crop was not needed because these regions are fully readable in the full-view comparison and contain no photographic or raster assets requiring pixel-level crop inspection.

## Required fidelity surfaces

- Fonts and typography: PingFang/HarmonyOS/system Chinese stack preserved; hero set to `27px`, card headings to `15px`, and small supporting text uses the same hierarchy as the reference. No unintended wrapping in the tested desktop state.
- Spacing and layout rhythm: prototype grid tracks, row heights, gaps, padding, radii, and elevation reproduced. Browser checks report no horizontal overflow and no card content overflow.
- Colors and visual tokens: solid white cards, light gray inner surfaces, dark primary text, readable muted text, theme orange action color, and semantic status colors remain token-driven.
- Image quality and asset fidelity: the homepage has no photographic assets. Existing icon-library components are retained; no placeholder or custom-drawn replacement assets were introduced.
- Copy and content: real application data is preserved. Differences from the source screenshot, such as `admin` and current project/task values, are dynamic data rather than visual drift.
- Interaction states: existing links, buttons, routes, loading state, and data requests were not changed. Visible homepage links retain their original destinations.

## Comparison history

### Pass 1

- [P1] Overall layout hierarchy differed: the implementation hero spanned all three columns and pushed the right rail below it.
- [P2] Card density and vertical rhythm were looser than the source; the first row grew beyond the reference proportions.
- Fixes: converted the homepage's existing DOM to the source grid using CSS only; applied source row heights, right-rail span, gaps, card padding, radius, shadow, type scale, and compact inner surfaces.
- Post-fix evidence: `.home-hero` is `156px`, main cards are `308px / 310px`, `.rhythm-card` is `480px`, and the right rail is `320px` wide in the desktop browser render.

### Pass 2

- [P2] The progress card exceeded its visible height by `3px`, and the today card by `11px`.
- Fixes: reduced only internal vertical spacing and matched the prototype's `34px` compact action buttons; no content was removed.
- Post-fix evidence: all six `.home-card` elements report `scrollHeight === clientHeight`; page horizontal overflow is false.

## Findings

- No actionable P0/P1/P2 visual mismatch remains for the requested desktop homepage state.
- P3: dynamic data density can vary when future task titles are substantially longer; the existing responsive and truncation rules handle the current real-data state.

## Implementation checklist

- [x] Preserve homepage functionality, data, routes, and DOM content.
- [x] Match prototype grid and right-rail hierarchy.
- [x] Match card padding, radius, shadow, type hierarchy, contrast, and inner surfaces.
- [x] Remove card and page overflow in the tested desktop state.
- [x] Build successfully and check browser console errors.

final result: passed
