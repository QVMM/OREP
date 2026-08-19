# Image2 Roadshow Material Brief Design

## Context

OREP roadshow PPT generation currently uses the `image2` renderer by default. The front half creates a lightweight outline, turns that outline into `page_content_cards`, writes `image2_page_descriptions.json`, and then asks image2 to generate each full-slide image.

This path is fast in theory, but it has become unstable and too thin:

- The "素材策划" stage can repeat the same heartbeat and retry messages for several minutes.
- The image2 lightweight outline only carries title, short points, a visual scene, and asset tokens.
- Uploaded screenshots and material images are not sent to image2 as image inputs. They are only mentioned as `[[ASSET:...]]` text.
- The page description layer is weaker than banana-slides, so policy, pain points, evidence, layout intent, and material usage are easy to under-express.

## Goals

1. Add a stable page-description artifact for image2 before rendering.
2. Let image2 consume real uploaded material images when the selected API path supports multimodal chat input.
3. Reduce duplicated retry and progress logs in the lightweight outline stage.
4. Keep the change medium-cost: no database migration and no full rewrite of the PPT pipeline.
5. Preserve current fallbacks so generation still completes when image2 or asset input is unavailable.

## Non-Goals

- Do not rebuild the whole PPT generator around banana-slides.
- Do not introduce a new database table for page descriptions.
- Do not require every page to use uploaded material images.
- Do not remove the existing SVG pipeline.
- Do not block export when a provider only supports text-to-image, but surface that downgrade in debug metadata.

## Proposed Architecture

### 1. New `image2_page_briefs.json`

Create a richer workspace artifact beside the existing `image2_page_descriptions.json`.

Path:

```text
<project_dir>/image2_page_briefs.json
```

Schema:

```json
{
  "schema_version": 1,
  "deck_type": "vocational_roadshow",
  "render_engine": "image2",
  "brief_source": "page_content_cards",
  "briefs": [
    {
      "page": 4,
      "page_type": "content",
      "section": "项目背景",
      "title": "政策引领与产业需求",
      "core_message": "项目符合农业现代化与数字化转型方向",
      "visible_points": "政策导向；温室痛点；市场需求",
      "visual_scene": "政策文件、痛点地图、产业趋势图组成一页背景论证页",
      "layout_intent": "政策/痛点/需求三栏，右侧保留趋势或截图主视觉",
      "evidence_focus": "说明这页要证明立项真实、方向正确、问题值得解决",
      "asset_refs": ["[[ASSET:asset_001]]", "[[ASSET:asset_002]]"],
      "speaker_goal": "让评委先接受项目为什么必须做",
      "image_prompt_notes": "真实政策截图可作为视觉参考，但不要把 asset_id 印到页面上"
    }
  ]
}
```

The brief is deterministic from `PageContentCard`, not another long LLM call. It thickens what already exists by normalizing page purpose, layout intent, evidence focus, and material usage.

### 2. Renderer Reads Briefs First

`image2_renderer.py` should load artifacts in this order:

1. `image2_page_briefs.json`
2. `image2_page_descriptions.json`
3. `page_content_cards.confirmed.json`
4. `page_content_cards.json`

The prompt builder should use richer brief fields:

- visible slide copy from `title`, `core_message`, `visible_points`
- visual intent from `visual_scene`
- layout intent from `layout_intent`
- evidence focus from `evidence_focus`
- material instructions from `asset_refs` and `image_prompt_notes`

### 3. Asset Image Inputs

When a brief references `[[ASSET:asset_id]]`, the renderer resolves the asset via `asset_registry.json`.

Resolution order:

1. `<project_dir>/sources/asset_registry.json`
2. `<project_dir>/sources/images/asset_registry.json`
3. `<project_dir>/asset_registry.json`

For each image asset:

- only include local files that exist;
- cap reference images per page to 3;
- skip non-image assets;
- record skipped/missing assets in debug metadata;
- for the first page, ignore uploaded assets even if accidentally referenced.

Provider behavior:

- `chat/completions`: send text plus image URL parts using local image data URLs.
- `images/generations`: keep current text-only behavior and record `asset_input_mode=text_only_endpoint`.
- `auto`: prefer chat when resolved material images exist; otherwise keep current protocol selection.

### 4. Retry and Progress Stabilization

Current lightweight outline retry can multiply:

- outer validation retry: up to 3
- inner stall retry: up to 3
- heartbeat every 12 seconds

Change for image2 lightweight outline:

- primary request: one call with heartbeat;
- if schema validation fails: one repair call;
- if request stalls: one reconnect attempt;
- then deterministic fallback;
- progress messages should include phase and attempt in a compact way, not repeat the same 12-second sequence across nested retries.

Target behavior:

- no more than two model requests before local fallback;
- no repeated "连接重试第 3 次" loops for the same logical stage;
- debug files still preserve each attempt.

### 5. Fallback Policy

If real image inputs cannot be sent:

- keep asset captions and tokens as text hints in prompt;
- do not pretend real images were used;
- write metadata:

```json
{
  "asset_input_mode": "text_only_endpoint",
  "asset_images_used": [],
  "asset_images_skipped": ["asset_001: endpoint does not support image input"]
}
```

If image2 fails:

- keep current editable placeholder SVG fallback.

## Data Flow

```text
Project ZIP / prepared material package
        ↓
ProjectZipParser
  sources/asset_registry.json
        ↓
roadshow_agent.analyze_materials
  material_diagnosis.json
  page_content_cards.json
  image2_page_descriptions.json
  image2_page_briefs.json
        ↓
image2_renderer.generate_image2_svg_pages
  load brief
  resolve asset images
  build rich image prompt
  call image2 with text + optional image references
        ↓
svg_output/xx_image2.svg
images/image2/page_xx.png
debug/image2/page_xx_attempt_n.json
```

## Acceptance Criteria

- A new roadshow image2 plan writes `image2_page_briefs.json`.
- Image2 prompts contain layout intent and evidence focus, not only title and short points.
- For pages with `[[ASSET:asset_id]]`, debug metadata records whether the actual image was sent or text-only fallback was used.
- Chat-compatible image2 requests include image content parts when local asset images exist.
- The lightweight outline phase uses at most one primary request, one repair request, and one reconnect attempt before deterministic fallback.
- Existing tests/imports still pass for `roadshow_cards.py`, `image2_renderer.py`, and `roadshow_agent.py`.

