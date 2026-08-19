# Competition Brain DOCX Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修订指定 DOCX 中竞赛大脑相关参数，保持其他平台参数不变，并生成独立更改记录。

**Architecture:** 使用 python-docx 对目标段落进行精确索引替换，沿用目标段落的原有段落格式并将新文字统一设为黄色高亮。修改前保存全部非目标段落和表格文本快照，修改后逐项比对；随后创建更改记录 DOCX，并使用文档技能的标准渲染器逐页检查两个文件。

**Tech Stack:** Bundled Python 3.12、python-docx、LibreOffice、文档技能 render_docx.py。

---

### Task 1: 建立目标段落与保护基线

**Files:**
- Read: `/Users/liuyixing/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_66dv2lxjocg922_6e43/msg/file/2026-07/新一代信息技术数据采集及训练综合实训平台_按评审意见修订高亮版_v2(2).docx`
- Create: `/Users/liuyixing/项目/OREP/outputs/competition-brain-revision/baseline.json`

- [ ] 提取全部正文和表格文本，记录段落索引、样式、黄色高亮和目标关键词。
- [ ] 将允许修改的段落限定为 51、54、55、86、104—120；第45段属于学校现状和建设必要性说明，不纳入产品参数修改；不因普通黄色高亮扩大范围。
- [ ] 保存非目标段落及全部表格文本哈希，作为修改后保护校验基线。

### Task 2: 精确修订竞赛大脑参数

**Files:**
- Create: `/Users/liuyixing/项目/OREP/outputs/competition-brain-revision/revise_competition_brain_docx.py`
- Create: `/Users/liuyixing/项目/OREP/outputs/competition-brain-revision/新一代信息技术数据采集及训练综合实训平台_竞赛大脑参数修订版.docx`

- [ ] 为每个目标段落定义完整的新文本，不使用模糊匹配或全局替换。
- [ ] 删除赛道专区和资源数量承诺；将专用软件训练、正式能力档案、评委排期协调、评分规则配置、会议纪要成果库和跨平台自动关联降级为现有能力可支撑的表述。
- [ ] 保留用户组织、课程、题库考试、错题复习、团队项目任务、在线路演、在线评分、AI评分分析、整改任务、再次评分与历史对比等真实能力。
- [ ] 继承原段落样式，将替换后的正文设置为黄色高亮并保存新文件，绝不覆盖原文件。

### Task 3: 生成独立更改记录

**Files:**
- Create: `/Users/liuyixing/项目/OREP/outputs/competition-brain-revision/竞赛大脑参数更改记录.docx`

- [ ] 建立标题、修订原则、范围说明和更改统计。
- [ ] 逐条记录段落位置、原表述摘要、修改后表述和修改原因。
- [ ] 明确列出未修改范围：其他平台技术参数、硬件、预算和教学实训内容。

### Task 4: 验证范围和内容一致性

**Files:**
- Read: `baseline.json`
- Read: 两个交付 DOCX

- [ ] 比对所有非目标段落和表格文本，预期差异数为 0。
- [ ] 检查修订版不存在“软件版本台账”“软件操作训练任务不少于”“时间排期”“评委协调”“评分维度与权重设置”“会议纪要”“按年度、赛道、团队和项目分类归档”等越界表述。
- [ ] 检查竞赛大脑相关段落前后定位一致，并验证更改记录条数等于实际替换段落数。

### Task 5: 渲染与逐页视觉检查

**Files:**
- Create: `/Users/liuyixing/项目/OREP/outputs/competition-brain-revision/render-revised/`
- Create: `/Users/liuyixing/项目/OREP/outputs/competition-brain-revision/render-log/`

- [ ] 使用 bundled Python 运行 `render_docx.py` 渲染两个 DOCX。
- [ ] 检查全部页面是否存在文字截断、表格溢出、分页异常、字体替换和高亮丢失。
- [ ] 如发现问题，修正文档并重新渲染，直至所有页面通过。
