# Competition Brain Positioning Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, test, and install a Codex skill that extracts the full value system of 启发·竞赛大脑 and turns it into evidence-grounded, student-first Chinese product messaging and Web copy.

**Architecture:** Install one self-contained skill at `~/.codex/skills/competition-brain-positioning`. Keep the orchestration workflow in `SKILL.md`, product facts and writing judgment in four direct references, and deterministic Chinese-copy checks in one Python script. Store evaluation fixtures and RED/GREEN comparison artifacts in the OREP workspace, outside the installed skill.

**Tech Stack:** Agent Skills (`SKILL.md`, `agents/openai.yaml`), Markdown references, Python 3 standard library, `unittest`, Codex subagents for forward evaluation.

**Constraint:** `/Users/liuyixing/项目/OREP` is not a Git repository. Replace commit steps with explicit file snapshots and verification records. Do not initialize Git or publish anything as part of this plan.

---

## File Map

**Create in the workspace:**

- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/rubric.md` - scoring rules shared by RED and GREEN evaluations.
- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-1-full-positioning.md` - full product-value extraction prompt.
- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-2-feature-synthesis.md` - scattered-feature synthesis prompt.
- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-3-copy-rewrite.md` - Chinese AI-copy rewrite prompt.
- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/baseline.md` - raw RED outputs plus scored failure patterns.
- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/green.md` - raw GREEN outputs plus scores and comparison.
- `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py` - deterministic tests for the linter.

**Create in the installed skill:**

- `/Users/liuyixing/.codex/skills/competition-brain-positioning/SKILL.md` - triggerable end-to-end workflow.
- `/Users/liuyixing/.codex/skills/competition-brain-positioning/agents/openai.yaml` - UI metadata and default prompt.
- `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/product-truth.md` - stable, confirmed product facts and claim boundaries.
- `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/value-extraction.md` - fact ledger, student value chain, core proposition stress tests.
- `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/voice-and-quality.md` - Chinese voice, anti-slop rules, editorial review.
- `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/output-contracts.md` - full value-system and Web-copy output contracts.
- `/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py` - JSON/text linter for mechanical copy risks.

---

### Task 1: Create the Evaluation Contract

**Files:**

- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/rubric.md`
- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-1-full-positioning.md`
- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-2-feature-synthesis.md`
- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-3-copy-rewrite.md`

- [ ] **Step 1: Write the scoring rubric**

Create `rubric.md` with seven dimensions, each scored 0-2:

```markdown
# Competition Brain Positioning Evaluation Rubric

Score each dimension 0, 1, or 2. Passing requires at least 12/14, with no zero in Evidence or Student priority.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Evidence | Invents or blurs claims | Some claims are labeled | Every key claim is sourced or labeled |
| Student priority | Leads with procurement or school management | Mentions students among audiences | Every major value ends in student learning or capability |
| Core proposition | Lists features or generic AI benefits | Has a theme but weak differentiation | One defensible proposition governs the whole system |
| Value chain | Stops at feature or convenience | Connects some features to outcomes | Connects product action to behavior, learning, capability, and competition |
| Coverage | Omits major product loop | Covers most modules | Unifies project, training, material, roadshow, feedback, and revalidation |
| Chinese voice | Formulaic, official, or AI-flavored | Readable but generic | Restrained, rhythmic, concrete, and opinionated |
| Actionability | Abstract strategy only | Partial usable copy | Produces an immediately usable value system and Web-copy mother draft |

Record exact phrases that caused each deduction. Do not award points for polish unsupported by facts.
```

- [ ] **Step 2: Write the full-positioning scenario**

Create `scenario-1-full-positioning.md`:

```markdown
# Scenario 1: Full Positioning

Read `/Users/liuyixing/项目/OREP/frontend/user/src/views/Intro.vue` and other directly relevant product files. Extract a complete product value system for 启发·竞赛大脑 and draft the Web homepage messaging structure.

Do not ask the user questions. Label assumptions and unsupported claims. Return the final artifact only.
```

- [ ] **Step 3: Write the scattered-feature scenario**

Create `scenario-2-feature-synthesis.md`:

```markdown
# Scenario 2: Feature Synthesis

A vocational competition platform contains project workspaces, daily training, course learning, exams, PPT and script versioning, online roadshows, uploaded-video scoring, evidence anchors, teacher review, remediation tasks, and next-round revalidation.

Find one core product proposition that unifies these capabilities. Then map each capability to actual student value. Avoid feature-list copy and unsupported claims.
```

- [ ] **Step 4: Write the rewrite scenario**

Create `scenario-3-copy-rewrite.md`:

```markdown
# Scenario 3: Rewrite AI-Flavored Copy

Rewrite the copy below for the 启发·竞赛大脑 homepage. Preserve only claims present in the source. The result should sound like a restrained Chinese product master with an educator's idealism and a champion coach's judgment.

> 在当今数字化与智能化浪潮下，启发·竞赛大脑依托先进 AI 技术，全方位赋能职业院校师生。平台打造集项目管理、训练学习、路演评分、智能复盘于一体的一站式备赛生态，实现从赛前到赛后的全流程闭环，助力学生全面成长，引领职业教育赛事训练新范式。
```

- [ ] **Step 5: Verify the fixture files**

Run:

```bash
rg -n "Passing requires|Scenario 1|Scenario 2|Scenario 3" /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning
```

Expected: one rubric match and three scenario matches.

---

### Task 2: Run RED Baseline Evaluations Without the Skill

**Files:**

- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/baseline.md`

- [ ] **Step 1: Dispatch three independent baseline agents**

Run the scenarios concurrently without mentioning or exposing the planned skill. Give each agent only its scenario file and the OREP workspace path. Use these exact task prompts:

```text
Read /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-1-full-positioning.md and complete the task. Return the artifact in your final response. Do not modify files.
```

```text
Read /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-2-feature-synthesis.md and complete the task. Return the artifact in your final response. Do not modify files.
```

```text
Read /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-3-copy-rewrite.md and complete the task. Return the artifact in your final response. Do not modify files.
```

- [ ] **Step 2: Score and preserve baseline outputs**

Create `baseline.md`. Under `# RED Baseline`, add one `## Scenario N` section per scenario. In each section, paste the agent's final response verbatim, then add a seven-row score table using the exact rubric dimension names and record `Score`, `Evidence`, and `Deduction reason` columns. Finish with `## Failure Patterns the Skill Must Correct` and list only failures directly visible in those responses.

```markdown
# RED Baseline

## Scenario 1
## Scenario 2
## Scenario 3

## Failure Patterns the Skill Must Correct
```

Do not paraphrase raw outputs. The failure-pattern list must be based on observed baseline behavior, not anticipated problems.

- [ ] **Step 3: Confirm RED actually failed**

Run:

```bash
rg -n "Failure Patterns the Skill Must Correct|Score" /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/baseline.md
```

Expected: three score sections and at least one concrete failure pattern. If all scenarios already score 12/14 or higher with no zero, strengthen the scenarios before creating the skill.

---

### Task 3: Write the Linter Tests and Observe Failure

**Files:**

- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py`
- Test target: `/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py`

- [ ] **Step 1: Write the failing tests**

Create `test_lint_copy.py`:

```python
import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path("/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py")


def load_module():
    spec = importlib.util.spec_from_file_location("competition_brain_copy_linter", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LintCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.linter = load_module()

    def test_flags_ai_and_official_cliches(self):
        findings = self.linter.lint_text(
            "在当今数字化浪潮下，平台全方位赋能师生，引领教育新范式。"
        )
        terms = {item["term"] for item in findings}
        self.assertIn("在当今", terms)
        self.assertIn("赋能", terms)
        self.assertIn("引领", terms)

    def test_flags_unverifiable_absolutes(self):
        findings = self.linter.lint_text("这是行业领先、全国第一的备赛平台。")
        categories = {item["category"] for item in findings}
        self.assertIn("unsupported-absolute", categories)

    def test_clean_copy_passes(self):
        findings = self.linter.lint_text(
            "路演结束后，问题回到具体页面和视频时点。学生知道下一轮改什么。"
        )
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails for the missing implementation**

Run:

```bash
python3 /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py -v
```

Expected: `ERROR` caused by missing `/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py`.

---

### Task 4: Initialize the Skill Scaffold

**Files:**

- Create: `/Users/liuyixing/.codex/skills/competition-brain-positioning/`

- [ ] **Step 1: Confirm the destination does not already exist**

Run:

```bash
test ! -e /Users/liuyixing/.codex/skills/competition-brain-positioning
```

Expected: exit code 0. If the directory exists, stop and inspect it; do not overwrite it.

- [ ] **Step 2: Run the official initializer**

Run:

```bash
python3 /Users/liuyixing/.codex/skills/.system/skill-creator/scripts/init_skill.py competition-brain-positioning \
  --path /Users/liuyixing/.codex/skills \
  --resources references,scripts \
  --interface 'display_name=竞赛大脑价值提炼' \
  --interface 'short_description=提炼学生真实成长导向的完整产品价值体系与大师级中文宣传文案' \
  --interface 'default_prompt=Use $competition-brain-positioning to extract the complete value system of 启发·竞赛大脑 and draft its Web messaging mother copy.'
```

Expected: the skill directory, `SKILL.md`, `agents/openai.yaml`, `references/`, and `scripts/` are created.

- [ ] **Step 3: Inspect generated metadata**

Run:

```bash
sed -n '1,120p' /Users/liuyixing/.codex/skills/competition-brain-positioning/agents/openai.yaml
```

Expected: quoted strings, explicit `$competition-brain-positioning` in `default_prompt`, and no undeclared dependencies.

---

### Task 5: Implement the Deterministic Copy Linter

**Files:**

- Modify: `/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py`
- Test: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py`

- [ ] **Step 1: Write the minimal linter implementation**

Implement this public contract:

```python
#!/usr/bin/env python3
import argparse
import json
import pathlib


PATTERNS = {
    "ai-cliche": ["在当今", "值得注意的是", "综上所述", "全方位", "一站式", "赋能"],
    "official-cliche": ["引领", "助力", "新范式", "新引擎", "高质量发展"],
    "unsupported-absolute": ["行业领先", "全国第一", "唯一", "彻底", "完美", "100%"],
}


def lint_text(text):
    findings = []
    for category, terms in PATTERNS.items():
        for term in terms:
            start = 0
            while True:
                index = text.find(term, start)
                if index < 0:
                    break
                findings.append({"category": category, "term": term, "index": index})
                start = index + len(term)
    return sorted(findings, key=lambda item: (item["index"], item["category"], item["term"]))


def main():
    parser = argparse.ArgumentParser(description="Lint Chinese product copy for mechanical risk patterns.")
    parser.add_argument("file", nargs="?", help="UTF-8 text or Markdown file. Reads stdin when omitted.")
    parser.add_argument("--json", action="store_true", help="Emit JSON findings.")
    args = parser.parse_args()

    if args.file:
        text = pathlib.Path(args.file).read_text(encoding="utf-8")
    else:
        import sys
        text = sys.stdin.read()

    findings = lint_text(text)
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f'{item["category"]}\t{item["term"]}\t{item["index"]}')
    raise SystemExit(1 if findings else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the unit tests**

Run:

```bash
python3 /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py -v
```

Expected: 3 tests pass.

- [ ] **Step 3: Smoke-test the CLI exit codes**

Run:

```bash
printf '%s' '把每一次反馈变成下一轮行动。' | python3 /Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py
printf '%s' '全方位赋能，引领新范式。' | python3 /Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py --json
```

Expected: first command exits 0 with no output; second exits 1 and returns JSON findings for `全方位`, `赋能`, `引领`, and `新范式`.

---

### Task 6: Write the Product Truth and Extraction References

**Files:**

- Create: `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/product-truth.md`
- Create: `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/value-extraction.md`

- [ ] **Step 1: Write `product-truth.md`**

Use these exact sections and confirmed facts:

```markdown
# 启发·竞赛大脑产品事实

## 品牌与范围
- 品牌名称：启发·竞赛大脑。
- 服务对象：参加世界职业院校技能大赛的学生团队与指导教师。
- 产品类别：以参赛项目为中心的智能备赛与路演迭代平台。
- 最高价值：以真实成长赢得比赛。

## 价值顺序
1. 参赛学生。
2. 指导教师。
3. 校领导。
4. 学校。

## 已证实的产品机制
- 同一项目空间承载人、任务、材料、路演和反馈。
- 训练、课程和考试围绕当前项目问题展开。
- PPT 和讲稿保留版本，并与项目和评分反馈关联。
- 路演记录保留录像、转写、材料版本、维度评分和证据锚点。
- AI 提供问题识别与建议，教师负责审核、编辑与最终判断。
- 经教师确认的反馈转成负责人、截止时间和复验范围明确的任务。
- 任务完成不等于问题关闭；下一轮路演用来验证是否真正改进。

## 声称边界
- 不编造获奖结果、客户数量、提分比例、学生发展结果或用户证言。
- 不把 AI 描述为教师的替代者或最终裁决者。
- 不把功能存在直接表述为已证明的学习成效。
- 不使用无证据的“行业领先”“全国第一”“金奖保障”等声称。
```

- [ ] **Step 2: Write `value-extraction.md`**

Include these operational rules:

```markdown
# 价值提炼方法

## 事实账本
将每条输入标记为：已证实、可推导、待补证、禁止声称。记录信息来源。

冲突时按以下顺序取信：用户当前明确确认 > 可运行产品行为 > 最新产品文档 > 历史文案。

## 学生价值链
对每项候选能力写出：

> 产品动作 → 学生行为变化 → 学到什么 → 形成什么能力 → 如何帮助比赛

无法走完价值链的功能降级为辅助能力或待验证假设。

## 唯一核心
生成三个候选命题，然后对每个候选检查：
1. 竞争对手能否原样照搬？
2. 产品行为能否证明？
3. 学生能否立即理解？
4. 能否统领项目、训练、材料、路演、反馈和复验？

按真实性、区分度、学生相关性、统领力和中文质感评分。只推荐一个主方向。

## 反向审稿
从学生、指导教师、怀疑者和中文主编四种视角审查。对每句核心文案追问：说的是什么事实？为什么值得学生在意？凭什么相信？

## 来源受限改写
当用户要求“只保留原文已有信息”、改写单段既有文案或给出其他来源边界时，进入来源受限模式：
1. 只为当前源文建立逐句 claim ledger；源文是唯一可写入成稿的事实来源。
2. `product-truth.md`、品牌母命题和通用价值链只用于识别冲突与审稿，不得补入源文没有的声明、因果、效果或价值判断。
3. 可以调整结构、节奏、用词和信息主次；不得把笼统成长绑定到源文未明确的具体环节，也不得添加“持续”“真正”“必然”等效果强度。
4. 如果理想品牌表达需要源文外信息，将其列为“建议补证”，不要写进成稿。
```

- [ ] **Step 3: Verify product facts against the current UI**

Run:

```bash
rg -n "项目在中心|路演不是一次会议|每条反馈|教师最终裁决|任务完成不等于问题关闭" /Users/liuyixing/项目/OREP/frontend/user/src/views/Intro.vue
```

Expected: current UI evidence for the project center, roadshow evidence, teacher review, and revalidation mechanisms. If wording differs, cite the actual UI text in `product-truth.md` rather than inventing a match.

---

### Task 7: Write the Voice, Output Contract, and Main Skill

**Files:**

- Create: `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/voice-and-quality.md`
- Create: `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/output-contracts.md`
- Modify: `/Users/liuyixing/.codex/skills/competition-brain-positioning/SKILL.md`

- [ ] **Step 1: Write `voice-and-quality.md`**

Include the approved voice and concrete prohibitions:

```markdown
# 品牌声音与质量门槛

## 品牌声音
- 教育理想主义的底色：关心学生究竟学会了什么。
- 冠军教练的判断力：直面问题，强调训练、修改和复验。
- 产品大师的克制：不煨情，不堆概念，不用形容词代替事实。

## 写作原则
- 先写事实和变化，再写意义。
- 用真实动作表现成长，不直接宣告“全面成长”。
- 长短句交替，允许一句单独成段，但不连续制造戏剧性短句。
- 一段只推进一个论点；段落顺序必须构成论证，不得任意互换。
- 只有当来源中存在时，才使用第一人称、用户证言、数字和案例。

## 禁用模式
- 禁用：在当今、值得注意的是、综上所述、赋能、引领、全方位、一站式、新范式、新引擎、行业领先。
- 避免“不仅……更……”、“从……到……”、“第一……第二……第三……”的密集使用。
- 不用凭空格言、假故事、虚构学生和未经证明的数字制造人味。

## 终稿检查
同时通过真实、锋利、学生优先、完整、克制、有人味、可落地七项检查。再运行 `scripts/lint-copy.py` 检查机械风险。脚本无警告不等于编辑合格。
```

- [ ] **Step 2: Write `output-contracts.md`**

Define the full output and partial-output rules:

```markdown
# 输出合同

## 完整产品价值母本
1. 一句话产品定位。
2. 核心价值命题与阐释。
3. 学生、指导教师、校领导、学校四层价值。
4. 功能到行为、学习、能力和比赛价值的映射。
5. 典型场景与使用前后变化。
6. 真实替代方案、差异化和证明要求。
7. 品牌宣言与声音规则。
8. Web 首页信息架构。
9. Hero、价值区、功能区、场景区、证明区和 CTA 文案。
10. 事实账本与待补证据。

## Web 首页约束
- Hero 只承载一个核心命题。
- 页面顺序形成论证：为什么需要改变 → 产品如何改变训练行为 → 学生获得什么 → 凭什么相信 → 下一步行动。
- 功能标题先表达变化或结果，功能名称放在说明中。
- 证明不足时输出“待补证据”，不用更大的口号填空。

## 局部请求
用户只要 Hero、功能映射或品牌宣言时，仍执行必要的事实核对和价值链推导，但只交付请求的部分。
```

- [ ] **Step 3: Replace the generated `SKILL.md`**

Use a concise main file with this exact structure and behavior:

```markdown
---
name: competition-brain-positioning
description: Use when positioning 启发·竞赛大脑, extracting its product value, mapping features to student growth, defining brand messaging, or writing and revising its Chinese Web, homepage, brochure, pitch, or promotional copy.
---

# 竞赛大脑价值提炼

## 核心原则
以学生真正学会了什么为价值原点。以真实成长赢得比赛；比赛结果是成长的检验，不是用空洞口号替代学习过程。

## 必读资料
1. 始终读取 `references/product-truth.md` 和 `references/value-extraction.md`。
2. 需要成稿、改稿或定义品牌声音时，读取 `references/voice-and-quality.md`。
3. 需要完整价值母本或任何对外载体时，读取 `references/output-contracts.md`。

## 执行流程
1. 先判断是否为来源受限改写。若是，优先执行 `references/value-extraction.md` 的来源受限规则，当前源文覆盖产品事实库与品牌母命题；不得用后两者向成稿补充声明。
2. 非来源受限任务，先检索用户指定的代码、页面、文档和赛事资料。能从现有资料得到第一版时，不先发出一长串问题。
3. 建立事实账本，分开已证实、可推导、待补证和禁止声称。
4. 对候选功能逐项跑学生价值链。走不完的功能不进入核心宣传。
5. 生成三个核心命题候选，执行竞争可复制性、产品证据、学生理解和全产品统领力测试。
6. 只推荐一个主方向，然后按学生、教师、校领导、学校的真实受益顺序展开。
7. 写作后进行四视角反向审稿，并运行 `python3 scripts/lint-copy.py <draft-file>` 检查机械风险。

## 硬性边界
- 不编造数字、案例、获奖结果、客户证言或产品能力。
- 不把 AI 描述为教师的替代者或最终裁决者。
- 不用功能清单假装价值体系。
- 不用去掉几个 AI 高频词假装已经写出了人话。
- 来源受限改写不得从产品事实库、品牌母命题或常识补入源文外声明。

## 输出
依用户请求使用 `references/output-contracts.md` 中的完整或局部合同。在结尾单独列出待验证假设和待补证据。
```

- [ ] **Step 4: Check size and unresolved placeholders**

Run:

```bash
wc -l -w /Users/liuyixing/.codex/skills/competition-brain-positioning/SKILL.md /Users/liuyixing/.codex/skills/competition-brain-positioning/references/*.md
rg -n "TODO|TBD|\[TODO|\[TBD" /Users/liuyixing/.codex/skills/competition-brain-positioning
```

Expected: `SKILL.md` stays below 500 lines; no placeholder matches.

---

### Task 8: Validate the Skill and Run GREEN Forward Tests

**Files:**

- Create: `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/green.md`
- Validate: `/Users/liuyixing/.codex/skills/competition-brain-positioning/`

- [ ] **Step 1: Run structural validation**

Run:

```bash
python3 /Users/liuyixing/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/liuyixing/.codex/skills/competition-brain-positioning
```

Expected: `Skill is valid!`

- [ ] **Step 2: Re-run deterministic tests**

Run:

```bash
python3 -m unittest /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py -v
```

Expected: 3 tests pass.

- [ ] **Step 3: Dispatch three GREEN agents**

Run the same three scenarios concurrently. This time use these exact prompts:

```text
Use $competition-brain-positioning at /Users/liuyixing/.codex/skills/competition-brain-positioning to complete /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-1-full-positioning.md. Return the artifact in your final response. Do not modify files.
```

```text
Use $competition-brain-positioning at /Users/liuyixing/.codex/skills/competition-brain-positioning to complete /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-2-feature-synthesis.md. Return the artifact in your final response. Do not modify files.
```

```text
Use $competition-brain-positioning at /Users/liuyixing/.codex/skills/competition-brain-positioning to complete /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-3-copy-rewrite.md. Return the artifact in your final response. Do not modify files.
```

- [ ] **Step 4: Score and preserve GREEN outputs**

Create `green.md` using the same raw-output and seven-row scoring structure as `baseline.md`. Follow it with a `## RED vs GREEN Comparison` table whose columns are `Scenario`, `RED`, `GREEN`, and `Material behavior change`, and whose rows are `Full positioning`, `Feature synthesis`, and `Copy rewrite`. Copy each numeric total from the completed score tables and describe one concrete behavior change using an exact phrase or structural difference from the two outputs.

Acceptance: every GREEN scenario scores at least 12/14, Evidence and Student priority are both 2, and each scenario improves materially over its RED baseline.

---

### Task 9: Refactor, Revalidate, and Confirm Installation

**Files:**

- Modify if needed: `/Users/liuyixing/.codex/skills/competition-brain-positioning/SKILL.md`
- Modify if needed: `/Users/liuyixing/.codex/skills/competition-brain-positioning/references/*.md`
- Modify if needed: `/Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py`

- [ ] **Step 1: Convert observed GREEN failures into precise skill changes**

For each rubric deduction, change the narrowest responsible file:

- Research or sequencing failure -> `SKILL.md`.
- Incorrect or missing product fact -> `product-truth.md`.
- Weak core or feature-list behavior -> `value-extraction.md`.
- AI voice or inflated prose -> `voice-and-quality.md` or a deterministic linter pattern.
- Missing deliverable -> `output-contracts.md`.

Do not add rules for hypothetical problems that did not appear in testing.

- [ ] **Step 2: Re-run only failed scenarios, then the full suite**

Expected: revised scenarios meet the 12/14 threshold, then all three scenarios are rerun once to check for regressions.

- [ ] **Step 3: Run final verification**

Run:

```bash
python3 /Users/liuyixing/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/liuyixing/.codex/skills/competition-brain-positioning
python3 /Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/test_lint_copy.py -v
rg -n "TODO|TBD|\[TODO|\[TBD" /Users/liuyixing/.codex/skills/competition-brain-positioning || true
```

Expected: structural validation passes, all unit tests pass, and placeholder scan returns no matches.

- [ ] **Step 4: Confirm discoverability and handoff**

Confirm these files exist and are non-empty:

```bash
test -s /Users/liuyixing/.codex/skills/competition-brain-positioning/SKILL.md
test -s /Users/liuyixing/.codex/skills/competition-brain-positioning/agents/openai.yaml
test -s /Users/liuyixing/.codex/skills/competition-brain-positioning/references/product-truth.md
test -s /Users/liuyixing/.codex/skills/competition-brain-positioning/scripts/lint-copy.py
```

Expected: all commands exit 0. Tell the user the skill is installed at the absolute path and will be available for explicit invocation as `$competition-brain-positioning` on the next turn.
