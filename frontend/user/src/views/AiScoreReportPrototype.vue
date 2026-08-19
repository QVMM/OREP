<template>
  <div class="report-prototype">
    <aside class="prototype-rail" aria-label="报告目录">
      <div class="rail-brand">
        <div class="brand-mark">OREP</div>
        <div>
          <strong>竞赛大脑</strong>
          <span>路演成长报告</span>
        </div>
      </div>

      <nav class="rail-menu">
        <a v-for="item in navItems" :key="item.id" :href="`#${item.id}`" :class="{ active: item.active }">
          <small>{{ item.index }}</small>
          <span>{{ item.label }}</span>
        </a>
      </nav>

      <div class="rail-score-card">
        <span>本轮综合评分</span>
        <strong>35</strong>
        <em>风险较高</em>
        <p>优先修复主线、证据和表达节奏。</p>
      </div>
    </aside>

    <main class="prototype-main">
      <header class="report-topbar">
        <div>
          <button class="text-back" type="button">返回</button>
          <h1>AI 路演评分报告</h1>
          <p>会议 #20 · 2026/06/26 14:16 · 智慧农业温室项目</p>
        </div>
        <div class="top-actions">
          <button class="btn ghost" type="button">询问 AI 助手</button>
          <button class="btn primary" type="button">生成改进任务</button>
          <button class="btn light" type="button">下载报告</button>
        </div>
      </header>

      <section id="summary" class="hero-grid">
        <article class="score-hero panel">
          <div class="score-ring" aria-label="综合评分 35 分">
            <span>35</span>
            <small>/100</small>
          </div>
          <div class="score-copy">
            <span class="section-kicker">本轮结论</span>
            <h2>路演还没有形成足够强的说服链</h2>
            <p>评委能听懂项目方向，但还不能确信它值得投、值得支持或值得继续推进。建议先重构演示主线，再补齐关键证据。</p>
            <div class="status-row">
              <span class="risk">风险较高</span>
              <span>预计提分空间 +15 ~ +25</span>
              <span>建议 3 天内完成首轮修改</span>
            </div>
          </div>
        </article>

        <article class="next-step panel">
          <span class="section-kicker">下一步</span>
          <h3>先不要急着美化 PPT</h3>
          <p>当前最大问题不是视觉包装，而是评委无法连续判断“痛点是否真实、方案是否有效、商业是否成立”。</p>
          <button class="btn primary wide" type="button">查看优先修改清单</button>
        </article>
      </section>

      <section class="panel reading-path">
        <div class="panel-title compact">
          <div>
            <span class="section-kicker blue">怎么看这份报告</span>
            <h2>按这个顺序读，3 分钟知道怎么改</h2>
          </div>
        </div>
        <div class="path-steps">
          <div v-for="step in readingSteps" :key="step.title" class="path-step">
            <span>{{ step.no }}</span>
            <strong>{{ step.title }}</strong>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </section>

      <section id="key-issues" class="panel issue-panel">
        <div class="panel-title">
          <div>
            <span class="section-kicker">先看这里</span>
            <h2>本轮最影响得分的 3 个问题</h2>
          </div>
          <span class="panel-note">按提分优先级排序</span>
        </div>

        <div class="issue-list">
          <article v-for="issue in keyIssues" :key="issue.no" class="issue-card">
            <div class="issue-no">{{ issue.no }}</div>
            <div>
              <div class="issue-head">
                <h3>{{ issue.title }}</h3>
                <span>{{ issue.impact }}</span>
              </div>
              <p>{{ issue.desc }}</p>
              <strong>{{ issue.action }}</strong>
            </div>
          </article>
        </div>
      </section>

      <section id="dimensions" class="two-column">
        <article class="panel dimension-panel">
          <div class="panel-title">
            <div>
              <span class="section-kicker">能力体检</span>
              <h2>五维评分</h2>
            </div>
            <span class="panel-note">35 / 100</span>
          </div>

          <div class="dimension-list">
            <div v-for="dim in dimensions" :key="dim.name" class="dimension-item">
              <div class="dimension-meta">
                <strong>{{ dim.name }}</strong>
                <span>{{ dim.score }} / 20</span>
              </div>
              <div class="bar-track"><i :style="{ width: `${dim.score * 5}%` }"></i></div>
              <p>{{ dim.comment }}</p>
            </div>
          </div>
        </article>

        <article id="deductions" class="panel deduction-panel">
          <div class="panel-title">
            <div>
              <span class="section-kicker warning">主要扣分原因</span>
              <h2>为什么不是高分？</h2>
            </div>
          </div>

          <div class="deduction-list">
            <div v-for="item in deductions" :key="item.title" class="deduction-card">
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
            </div>
          </div>

          <div class="rule-note">
            评分说明：当核心能力维度低于基础线时，系统会限制最终总分上限，避免单项亮点掩盖关键短板。
          </div>
        </article>
      </section>

      <section id="evidence" class="panel evidence-panel">
        <div class="panel-title">
          <div>
            <span class="section-kicker blue">AI 根据什么判断？</span>
            <h2>画面抽帧与扣分证据链</h2>
          </div>
          <span class="panel-note">展示用户可见依据，不展示内部规则与 prompt</span>
        </div>

        <div class="frame-section">
          <div class="frame-stage-card">
            <div class="mock-frame">
              <div class="mock-slide">
                <span>智慧农业温室项目</span>
                <strong>远程环境监测 + 自动调控</strong>
                <p>当前画面缺少用户痛点数据、收益测算和商业闭环说明</p>
              </div>
              <div class="frame-time">02:18</div>
            </div>
            <div class="frame-caption">
              <span>当前选中抽帧</span>
              <h3>方案介绍页信息完整度不足</h3>
              <p>AI 在该画面中识别到项目功能描述，但没有看到明确的目标客户、成本收益、定价方式或试点结果，因此影响“商业逻辑完整度”和“证据与数据支撑”。</p>
            </div>
          </div>

          <div class="frame-list" aria-label="抽帧列表">
            <button v-for="frame in extractedFrames" :key="frame.time" type="button" :class="{ active: frame.active }">
              <span>{{ frame.time }}</span>
              <strong>{{ frame.title }}</strong>
              <small>{{ frame.note }}</small>
            </button>
          </div>
        </div>

        <div class="evidence-table">
          <article v-for="item in evidence" :key="item.problem" class="evidence-row">
            <div>
              <span>发现的问题</span>
              <strong>{{ item.problem }}</strong>
            </div>
            <div>
              <span>AI 看到的依据</span>
              <p>{{ item.proof }}</p>
            </div>
            <div>
              <span>影响结果</span>
              <p>{{ item.effect }}</p>
            </div>
            <div>
              <span>修改建议</span>
              <p>{{ item.suggestion }}</p>
            </div>
          </article>
        </div>
      </section>

      <section id="plan" class="panel plan-panel">
        <div class="panel-title">
          <div>
            <span class="section-kicker green">下一轮提分路线</span>
            <h2>把报告变成团队任务</h2>
          </div>
          <button class="btn primary" type="button">一键生成任务</button>
        </div>

        <div class="plan-list">
          <article v-for="task in plan" :key="task.level" class="plan-card">
            <span>{{ task.level }}</span>
            <h3>{{ task.title }}</h3>
            <p>{{ task.desc }}</p>
            <small>{{ task.owner }} · {{ task.time }}</small>
          </article>
        </div>
      </section>

      <section id="memory" class="lower-grid">
        <article class="panel memory-panel">
          <span class="section-kicker">连续评分记忆</span>
          <h2>暂无历史对比</h2>
          <p>完成下一轮评分后，这里会展示上轮问题是否已修复、新增问题、重复扣分和分数变化。</p>
          <div class="memory-stats">
            <span><strong>0</strong> 已修复</span>
            <span><strong>0</strong> 新增问题</span>
            <span><strong>0.00</strong> 重复扣分</span>
          </div>
        </article>

        <article id="jury" class="panel jury-panel">
          <span class="section-kicker blue">AI 评审团复核</span>
          <h2>不同评委会怎么看？</h2>
          <div class="jury-list">
            <div v-for="item in jury" :key="item.role">
              <strong>{{ item.role }}</strong>
              <p>{{ item.view }}</p>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
const navItems = [
  { id: 'summary', index: '01', label: '总览', active: true },
  { id: 'key-issues', index: '02', label: '三大问题' },
  { id: 'dimensions', index: '03', label: '五维评分' },
  { id: 'evidence', index: '04', label: '证据链' },
  { id: 'plan', index: '05', label: '提分路线' },
  { id: 'jury', index: '06', label: '评审团' }
]

const readingSteps = [
  { no: '1', title: '先看结论', desc: '知道本轮分数、风险等级和最核心判断。' },
  { no: '2', title: '再看三大问题', desc: '明确本轮最该先修的短板，不被细节淹没。' },
  { no: '3', title: '对照抽帧证据', desc: '看到 AI 是根据哪段画面、哪类表达和哪项缺失扣分。' },
  { no: '4', title: '生成提分任务', desc: '把报告转成 P0/P1/P2 的团队修改清单。' }
]

const keyIssues = [
  {
    no: '01',
    title: '路演主线不够清晰',
    impact: '影响高',
    desc: '听众难以快速理解你解决什么问题、服务谁、为什么现在值得做。',
    action: '先重写开场 60 秒和项目价值主线。'
  },
  {
    no: '02',
    title: '关键证据不足',
    impact: '影响高',
    desc: '市场规模、用户需求、商业模式和竞争优势缺少可验证数据支撑。',
    action: '补充用户案例、市场数据、竞品对比和转化路径。'
  },
  {
    no: '03',
    title: '表达节奏影响理解',
    impact: '影响中',
    desc: '背景铺垫偏长，核心卖点出现较晚，评委难以形成连续判断。',
    action: '把核心亮点提前，压缩背景说明。'
  }
]

const dimensions = [
  { name: '项目价值表达', score: 8, comment: '方向可理解，但价值判断不够快。' },
  { name: '商业逻辑完整度', score: 7, comment: '收费对象、定价方式和增长路径需要补齐。' },
  { name: '证据与数据支撑', score: 5, comment: '当前最短板，缺少可验证数据与案例。' },
  { name: '现场表达节奏', score: 8, comment: '能完成讲述，但重点出现偏晚。' },
  { name: '评委说服力', score: 7, comment: '还不足以让评委相信项目具备推进价值。' }
]

const deductions = [
  { title: '核心论证链不完整', desc: '没有连续回答“用户痛点、解决方案、为什么你能做、如何增长、如何变现”。' },
  { title: '证据不足', desc: '部分判断缺少数据、案例或现场材料支撑，AI 无法确认结论是否可靠。' },
  { title: '表达重点不集中', desc: '关键信息出现较晚，前半段没有快速建立项目价值。' }
]

const evidence = [
  {
    problem: '商业模式解释不够清楚',
    proof: '路演中提到“后续通过服务费变现”，但没有说明收费对象、方式、价格区间和转化路径。',
    effect: '评委难以判断项目是否具备可持续收入能力。',
    suggestion: '补充一页商业模式说明，明确目标客户、付费理由、定价方式和预计转化率。'
  },
  {
    problem: '用户痛点证据不足',
    proof: '提到了智慧农业温室方向，但缺少真实用户访谈、试点反馈或损失数据。',
    effect: '痛点真实性不足，项目必要性被削弱。',
    suggestion: '加入 2 到 3 个真实场景，说明传统温室当前成本、效率或管理问题。'
  }
]

const extractedFrames = [
  { time: '00:42', title: '开场定位', note: '方向出现，但价值主张不够快', active: false },
  { time: '02:18', title: '方案介绍', note: '功能描述多，商业证据少', active: true },
  { time: '04:06', title: '市场说明', note: '缺少规模来源和目标客户拆分', active: false },
  { time: '06:35', title: '总结收束', note: '亮点重复，但行动请求不明确', active: false }
]

const plan = [
  { level: 'P0', title: '重构路演主线', desc: '让评委在前 1 分钟理解项目价值、目标用户和核心差异。', owner: '负责人：主讲人', time: '建议 1 天内完成' },
  { level: 'P1', title: '补齐关键证据', desc: '补充市场规模、目标用户、竞品对比、试点数据和商业模式。', owner: '负责人：产品/市场', time: '建议 2 天内完成' },
  { level: 'P2', title: '优化表达节奏', desc: '压缩背景介绍，把核心卖点和数据证明提前到前半段。', owner: '负责人：演讲教练', time: '建议 1 天内完成' }
]

const jury = [
  { role: '投资人视角', view: '商业模式还不够清晰，需要证明收入路径。' },
  { role: '用户视角', view: '痛点场景还不够具体，缺少真实使用画面。' },
  { role: '产品视角', view: '解决方案差异化不足，需要说明为什么不是普通监控系统。' },
  { role: '表达教练视角', view: '开场吸引力偏弱，建议把结果和价值前置。' }
]
</script>

<style scoped>
.report-prototype {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 272px 1fr;
  color: #eef7f3;
  background:
    radial-gradient(circle at top left, rgba(50, 220, 150, 0.14), transparent 34rem),
    linear-gradient(135deg, #06100e 0%, #080b0f 45%, #101017 100%);
}

.prototype-rail {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 32px 22px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(2, 8, 7, 0.82);
}

.rail-brand,
.rail-menu a,
.rail-score-card,
.status-row,
.panel-title,
.issue-head,
.dimension-meta,
.memory-stats,
.top-actions,
.path-steps,
.frame-stage-card,
.frame-list {
  display: flex;
}

.rail-brand {
  gap: 14px;
  align-items: center;
  margin-bottom: 34px;
}

.brand-mark {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 900;
  background: #ff6a1a;
  color: white;
}

.rail-brand strong,
.rail-brand span,
.rail-score-card span,
.rail-score-card em,
.section-kicker,
.panel-note,
.evidence-row span,
.plan-card small {
  display: block;
}

.rail-brand strong {
  font-size: 21px;
}

.rail-brand span,
.rail-score-card p,
.panel-note,
.evidence-row span,
.plan-card small,
.prototype-main p {
  color: #9dadab;
}

.rail-menu {
  display: grid;
  gap: 12px;
}

.rail-menu a {
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 16px;
  color: #bac8c6;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.025);
}

.rail-menu a.active,
.rail-menu a:hover {
  border-color: rgba(107, 239, 174, 0.42);
  color: #effff8;
  background: rgba(40, 216, 139, 0.12);
}

.rail-menu small {
  width: 32px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  color: #76f0b0;
  font-weight: 800;
}

.rail-score-card {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 28px;
  flex-direction: column;
  gap: 6px;
  padding: 20px;
  border: 1px solid rgba(107, 239, 174, 0.24);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(107, 239, 174, 0.14), rgba(7, 17, 18, 0.88));
}

.rail-score-card strong {
  font-size: 46px;
  line-height: 1;
}

.rail-score-card em,
.risk {
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  font-style: normal;
  font-weight: 800;
  color: #06130e;
  background: #74f2ad;
}

.prototype-main {
  padding: 32px 40px 56px;
}

.report-topbar {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 28px;
}

.text-back {
  padding: 0;
  border: 0;
  color: #99aaa8;
  background: transparent;
  cursor: pointer;
}

.report-topbar h1 {
  margin: 18px 0 8px;
  font-size: clamp(30px, 4vw, 48px);
  letter-spacing: -0.04em;
}

.top-actions {
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn {
  height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  font-weight: 800;
  color: #effff9;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.btn.primary {
  border-color: #ff7a1a;
  background: #ff761a;
}

.btn.ghost {
  border-color: rgba(67, 214, 206, 0.32);
  background: rgba(21, 154, 146, 0.12);
}

.btn.light {
  color: #1b1b1b;
  background: #f7f4ed;
}

.btn.wide {
  width: 100%;
  margin-top: 12px;
}

.hero-grid,
.two-column,
.lower-grid {
  display: grid;
  gap: 18px;
}

.hero-grid {
  grid-template-columns: minmax(0, 1fr) 340px;
}

.two-column,
.lower-grid {
  grid-template-columns: 1fr 1fr;
}

.panel {
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 22px;
  background: rgba(18, 25, 30, 0.78);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
}

.score-hero {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 28px;
  align-items: center;
  padding: 30px;
}

.score-ring {
  width: 190px;
  height: 190px;
  display: grid;
  place-content: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, #12251d 0 55%, transparent 56%),
    conic-gradient(#75f0a8 0 35%, rgba(255, 255, 255, 0.11) 35% 100%);
}

.score-ring span {
  font-size: 70px;
  font-weight: 900;
  color: #75f0a8;
  line-height: 0.95;
}

.score-ring small {
  text-align: center;
  color: #9dadab;
}

.section-kicker {
  margin-bottom: 10px;
  color: #76f0b0;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.section-kicker.warning {
  color: #ffd28a;
}

.section-kicker.blue {
  color: #7fd3ff;
}

.section-kicker.green {
  color: #8affbd;
}

.score-copy h2,
.panel h2,
.next-step h3,
.issue-card h3,
.deduction-card h3,
.plan-card h3 {
  margin: 0;
}

.score-copy h2 {
  max-width: 720px;
  font-size: clamp(26px, 3vw, 40px);
  letter-spacing: -0.03em;
}

.score-copy p {
  max-width: 760px;
  font-size: 18px;
  line-height: 1.75;
}

.status-row {
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.status-row span:not(.risk) {
  padding: 7px 12px;
  border-radius: 999px;
  color: #dbe9e7;
  background: rgba(255, 255, 255, 0.08);
}

.next-step,
.issue-panel,
.dimension-panel,
.deduction-panel,
.evidence-panel,
.plan-panel,
.memory-panel,
.jury-panel,
.reading-path {
  padding: 24px;
}

.next-step {
  background: linear-gradient(155deg, rgba(255, 128, 37, 0.16), rgba(18, 25, 30, 0.82));
}

.next-step h3 {
  font-size: 26px;
}

.reading-path,
.issue-panel,
.two-column,
.evidence-panel,
.plan-panel,
.lower-grid {
  margin-top: 18px;
}

.panel-title {
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-title.compact {
  margin-bottom: 14px;
}

.panel-title h2,
.memory-panel h2,
.jury-panel h2 {
  margin: 0;
  font-size: 26px;
}

.reading-path {
  border-color: rgba(127, 211, 255, 0.16);
  background: linear-gradient(135deg, rgba(127, 211, 255, 0.08), rgba(18, 25, 30, 0.76));
}

.path-steps {
  gap: 12px;
}

.path-step {
  flex: 1;
  position: relative;
  padding: 18px 16px 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
}

.path-step span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  margin-bottom: 12px;
  border-radius: 50%;
  color: #06130e;
  font-weight: 900;
  background: #7fd3ff;
}

.path-step strong {
  display: block;
  font-size: 17px;
}

.issue-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.issue-card {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
}

.issue-no {
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: #06130e;
  font-weight: 900;
  background: #78efac;
}

.issue-head {
  justify-content: space-between;
  gap: 10px;
}

.issue-head span {
  flex: 0 0 auto;
  color: #ffd38f;
  font-weight: 800;
}

.issue-card strong {
  color: #effff8;
}

.dimension-list,
.deduction-list,
.plan-list,
.jury-list {
  display: grid;
  gap: 14px;
}

.dimension-item,
.deduction-card,
.plan-card,
.jury-list div {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.045);
}

.dimension-meta {
  justify-content: space-between;
  margin-bottom: 10px;
}

.bar-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
}

.bar-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff7a1a, #77f0aa);
}

.dimension-item p,
.deduction-card p,
.evidence-row p,
.plan-card p,
.jury-list p {
  margin-bottom: 0;
  line-height: 1.65;
}

.deduction-panel {
  background: linear-gradient(155deg, rgba(255, 165, 65, 0.1), rgba(18, 25, 30, 0.84));
}

.rule-note {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  color: #ffd89b;
  background: rgba(255, 173, 76, 0.1);
}

.evidence-table {
  display: grid;
  gap: 14px;
}

.frame-section {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) 360px;
  gap: 16px;
  margin-bottom: 18px;
}

.frame-stage-card {
  gap: 18px;
  align-items: stretch;
  padding: 16px;
  border: 1px solid rgba(127, 211, 255, 0.16);
  border-radius: 20px;
  background: rgba(4, 13, 18, 0.58);
}

.mock-frame {
  position: relative;
  flex: 0 0 380px;
  min-height: 230px;
  overflow: hidden;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(17, 37, 51, 0.94), rgba(10, 18, 28, 0.94)),
    repeating-linear-gradient(90deg, transparent 0 34px, rgba(255, 255, 255, 0.05) 34px 35px);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.mock-slide {
  position: absolute;
  inset: 28px;
  display: grid;
  align-content: center;
  gap: 14px;
}

.mock-slide span {
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  color: #06130e;
  font-weight: 900;
  background: #7fd3ff;
}

.mock-slide strong {
  max-width: 280px;
  font-size: 30px;
  line-height: 1.16;
}

.mock-slide p {
  max-width: 300px;
  margin: 0;
}

.frame-time {
  position: absolute;
  right: 14px;
  bottom: 14px;
  padding: 6px 10px;
  border-radius: 999px;
  color: #eaf8ff;
  font-weight: 900;
  background: rgba(0, 0, 0, 0.5);
}

.frame-caption {
  align-self: center;
}

.frame-caption span {
  color: #7fd3ff;
  font-weight: 900;
}

.frame-caption h3 {
  margin: 10px 0;
  font-size: 24px;
}

.frame-list {
  flex-direction: column;
  gap: 10px;
}

.frame-list button {
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 4px 12px;
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  text-align: left;
  color: #eaf7f4;
  background: rgba(255, 255, 255, 0.045);
  cursor: pointer;
}

.frame-list button.active {
  border-color: rgba(127, 211, 255, 0.5);
  background: rgba(127, 211, 255, 0.12);
}

.frame-list span {
  grid-row: span 2;
  color: #7fd3ff;
  font-weight: 900;
}

.frame-list small {
  color: #9dadab;
}

.evidence-row {
  display: grid;
  grid-template-columns: 1fr 1.35fr 1fr 1.25fr;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(127, 211, 255, 0.16);
  border-radius: 18px;
  background: rgba(127, 211, 255, 0.055);
}

.evidence-row strong {
  font-size: 18px;
}

.plan-list {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.plan-card span {
  display: inline-grid;
  place-items: center;
  width: 44px;
  height: 32px;
  margin-bottom: 12px;
  border-radius: 999px;
  color: #06130e;
  font-weight: 900;
  background: #76f0b0;
}

.memory-stats {
  gap: 12px;
  margin-top: 20px;
}

.memory-stats span {
  flex: 1;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.055);
}

.memory-stats strong {
  display: block;
  font-size: 30px;
}

@media (max-width: 1180px) {
  .report-prototype {
    grid-template-columns: 1fr;
  }

  .prototype-rail {
    position: static;
    height: auto;
  }

  .rail-menu {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .rail-score-card {
    position: static;
    margin-top: 18px;
  }

  .hero-grid,
  .two-column,
  .lower-grid,
  .issue-list,
  .plan-list,
  .frame-section {
    grid-template-columns: 1fr;
  }

  .path-steps,
  .frame-stage-card {
    flex-direction: column;
  }

  .mock-frame {
    flex-basis: auto;
  }
}

@media (max-width: 760px) {
  .prototype-main,
  .prototype-rail {
    padding: 20px;
  }

  .report-topbar,
  .score-hero {
    display: block;
  }

  .top-actions {
    justify-content: flex-start;
    margin-top: 16px;
  }

  .rail-menu,
  .evidence-row {
    grid-template-columns: 1fr;
  }

  .score-ring {
    width: 150px;
    height: 150px;
    margin-bottom: 18px;
  }
}
</style>
