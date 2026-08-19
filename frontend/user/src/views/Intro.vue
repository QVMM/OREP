<template>
  <div ref="pageRef" class="landing-page" data-landing-page>
    <a class="skip-link" href="#main">跳到主要内容</a>

    <header class="site-header" :class="{ 'is-scrolled': headerScrolled }" data-header>
      <div class="nav-shell">
        <a class="brand" href="#top" aria-label="启发·竞赛大脑首页" @click.prevent="scrollTo('top')">
          <span class="brand-mark">
            <img src="/intro-landing/logo.svg" alt="" />
          </span>
          <span>启发·竞赛大脑</span>
        </a>

        <nav class="desktop-nav" aria-label="主要导航">
          <a
            v-for="item in navItems"
            :key="item.id"
            :href="`#${item.id}`"
            :class="{ 'is-active': activeSection === item.id }"
            @click.prevent="scrollTo(item.id)"
          >{{ item.label }}</a>
        </nav>

        <button class="nav-entry" type="button" @click="goLogin">进入平台</button>

        <button
          class="menu-toggle"
          type="button"
          :aria-label="menuOpen ? '关闭导航' : '打开导航'"
          :aria-expanded="menuOpen ? 'true' : 'false'"
          aria-controls="mobile-menu"
          @click="menuOpen = !menuOpen"
        >
          <span></span>
          <span></span>
        </button>
      </div>

      <nav class="mobile-menu" id="mobile-menu" aria-label="移动端导航" :hidden="!menuOpen">
        <a
          v-for="item in navItems"
          :key="`m-${item.id}`"
          :href="`#${item.id}`"
          @click.prevent="scrollTo(item.id); menuOpen = false"
        >{{ item.label }}</a>
        <button type="button" class="mobile-login" @click="goLogin">进入平台</button>
      </nav>
    </header>

    <main id="main">
      <!-- Hero -->
      <section class="hero" id="top">
        <div class="hero-glow" aria-hidden="true"></div>

        <div class="hero-copy">
          <h1>
            面向世界职业院校技能大赛的<br />
            <span class="hero-accent">智能备赛平台</span>
          </h1>
          <p class="hero-description">
            围绕
            <span class="hero-pill">自主确定项目</span>
            <span class="hero-pill">真问题真场景</span>
            <span class="hero-pill">技能操作与现场讲解同步</span>
            的核心要求，提供从项目定位到项目设计、从技能训练到讲解演练的全流程备赛支持。
          </p>
          <div class="hero-actions-row">
            <button class="primary-cta" type="button" @click="goLogin">
              <span>开始使用</span>
            </button>
            <a class="secondary-cta" href="#product" @click.prevent="scrollTo('product')">查看能力介绍</a>
          </div>
        </div>

        <div class="hero-preview reveal">
          <IntroProductPreview />
        </div>
      </section>

      <section class="closer section-shell" id="product">
        <div class="section-intro centered reveal">
          <p class="section-kicker">产品能力</p>
          <h2>项目在中心，所有工作围着它转</h2>
          <p>同一个项目空间承载人、材料、任务、路演与每一轮反馈；不再在课程、会议和文件工具之间来回寻找上下文。</p>
        </div>

        <div class="closer-tabs reveal" role="tablist" aria-label="产品能力切换">
          <button
            v-for="tab in closerTabs"
            :key="tab.key"
            type="button"
            role="tab"
            :class="{ 'is-active': closerTab === tab.key }"
            :aria-selected="closerTab === tab.key"
            @click="closerTab = tab.key"
          >{{ tab.label }}</button>
        </div>

        <div class="closer-stage reveal">
          <div v-show="closerTab === 'project'" class="closer-panel is-active" role="tabpanel">
            <div class="closer-copy">
              <span class="feature-number">01</span>
              <h3>一眼看到项目现在在哪里</h3>
              <p>项目状态、阶段进度、团队分工、任务队列与下一次路演汇聚在同一工作台。学生知道今天做什么，教师先看到风险与待办。</p>
              <div class="feature-points">
                <span>任务管理与训练日联动</span>
                <span>资源中心沉淀材料版本</span>
                <span>角色权限清晰隔离</span>
              </div>
            </div>
            <div class="closer-visual project-visual" aria-hidden="true">
              <div class="visual-top"><span>项目工作台</span><small>复盘提升阶段</small></div>
              <div class="project-track">
                <span class="is-done"><i>1</i><b>选题策划</b></span>
                <span class="is-done"><i>2</i><b>材料准备</b></span>
                <span class="is-active"><i>3</i><b>路演迭代</b></span>
                <span><i>4</i><b>赛前冲刺</b></span>
              </div>
              <div class="visual-card-row">
                <div><small>团队成员</small><strong>7</strong><span>含队长与指导教师</span></div>
                <div><small>待处理任务</small><strong>2</strong><span>训练营 + 团队自建</span></div>
                <div><small>项目资料</small><strong>32</strong><span>PPT / 讲稿 / 证据</span></div>
              </div>
              <div class="visual-activity">
                <span class="avatar">王</span>
                <p><strong>王同学提交了 PPT V6</strong><small>已进入资源中心 · 8 分钟前</small></p>
                <b>待审核</b>
              </div>
            </div>
          </div>

          <div v-show="closerTab === 'roadshow'" class="closer-panel is-active" role="tabpanel">
            <div class="closer-copy">
              <span class="feature-number">02</span>
              <h3>路演不是一次会议，而是数据采集点</h3>
              <p>支持线上路演与视频上传评分。每次路演固定项目材料版本，并把录像、转写、维度评分和证据锚点留在同一条记录中。</p>
              <div class="feature-points">
                <span>评分定位到视频时间点</span>
                <span>PPT / 讲稿版本可回溯</span>
                <span>多轮数据形成提升趋势</span>
              </div>
            </div>
            <div class="closer-visual roadshow-visual" aria-hidden="true">
              <div class="visual-top"><span>路演评分</span><small>第 5 轮 · 已完成</small></div>
              <div class="roadshow-score">
                <div><strong>86.4</strong><small>本轮综合评分（示意）</small></div>
                <span>较上轮<br /><b>+8.4</b></span>
              </div>
              <div class="roadshow-line">
                <svg viewBox="0 0 520 150" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#e84a1c" stop-opacity=".22" />
                      <stop offset="100%" stop-color="#e84a1c" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <path class="area" d="M0 130 C75 125 85 100 145 105 S230 90 290 82 S380 58 520 20 L520 150 L0 150 Z" />
                  <path class="line" d="M0 130 C75 125 85 100 145 105 S230 90 290 82 S380 58 520 20" />
                </svg>
              </div>
              <div class="visual-legend"><span>项目内容</span><span>PPT 表达</span><span>演讲表现</span><span>答辩协作</span></div>
            </div>
          </div>

          <div v-show="closerTab === 'review'" class="closer-panel is-active" role="tabpanel">
            <div class="closer-copy">
              <span class="feature-number">03</span>
              <h3>每条反馈，都有下一步</h3>
              <p>AI 先识别问题并给出建议，教师再审核、编辑和发布。执行结果回到下一轮路演中验证，直到问题真正关闭。</p>
              <div class="feature-points">
                <span>AI 只提供建议</span>
                <span>教师最终裁决</span>
                <span>任务完成不等于问题关闭</span>
              </div>
            </div>
            <div class="closer-visual review-visual" aria-hidden="true">
              <div class="visual-top"><span>问题与待办</span><small>来自第 5 轮评分报告</small></div>
              <div class="review-flow">
                <div><span>AI 原始建议</span><strong>补充项目成果前后对比</strong><small>依据：PPT 第 6 页、视频 03:18</small></div>
                <i>→</i>
                <div class="review-focus"><span>教师审核版本</span><strong>补充三组试点数据并统一口径</strong><small>负责人：王同学 · 截止周四</small></div>
                <i>→</i>
                <div><span>下轮验证</span><strong>在第 6 轮路演中重新评分</strong><small>验证后决定关闭或继续整改</small></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Feedback machine -->
      <section class="feedback-section" id="feedback">
        <div class="feedback-head section-shell reveal">
          <p class="section-kicker">从反馈到行动</p>
          <h2><span>路演进，</span><span>任务出。</span></h2>
          <p>反馈不是一份看完就结束的报告，而是下一轮项目行动的起点。</p>
        </div>

        <div class="feedback-machine section-shell reveal">
          <div class="input-column">
            <span class="machine-label">一次路演的全部输入</span>
            <article>
              <span class="machine-icon"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M2 3h20M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3M7 21l5-5 5 5" /></svg></span>
              <span><strong>路演录像与转写</strong><small>线上路演 / 上传视频</small></span>
            </article>
            <article>
              <span class="machine-icon"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 5h16v14H4zM8 9h8m-8 4h5" /></svg></span>
              <span><strong>PPT 与讲稿版本</strong><small>固定本轮使用材料</small></span>
            </article>
            <article>
              <span class="machine-icon"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 20h16V4H4v16Zm4-5 2 2 5-6" /></svg></span>
              <span><strong>维度评分与证据</strong><small>时间点 / 页面 / 段落</small></span>
            </article>
            <article>
              <span class="machine-icon"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3 14 8l5 2-5 2-2 5-2-5-5-2 5-2 2-5ZM19 16l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Z" /></svg></span>
              <span><strong>实质核验与任务书</strong><small>套壳 / 先进 / 价值</small></span>
            </article>
          </div>

          <div class="machine-core">
            <span class="core-orbit orbit-one" />
            <span class="core-orbit orbit-two" />
            <div class="core-mark"><img src="/intro-landing/logo.svg" alt="" /></div>
            <strong>评分复盘</strong>
            <small>合并 · 归因 · 去重</small>
          </div>

          <div class="output-column">
            <span class="machine-label">教师确认后的可执行结果</span>
            <article class="output-featured">
              <div class="output-status"><i />高优先级</div>
              <h3>补强项目成果的数据证明</h3>
              <p>补充三组试点前后对比，并同步修改 PPT 第 6 页与讲稿对应段落。</p>
              <div class="output-meta">
                <span><small>负责人</small><b>王同学</b></span>
                <span><small>截止时间</small><b>周四 18:00</b></span>
              </div>
            </article>
            <div class="output-history">
              <span>AI 原始建议</span>
              <i>→</i>
              <span>教师审核版本</span>
              <i>→</i>
              <span>任务管理执行</span>
            </div>
            <p class="restore-note">
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5" /></svg>
              证据链始终可回溯，教师可改写建议，但不能被 AI 自动覆盖
            </p>
          </div>
        </div>
      </section>

      <!-- Cycle -->
      <section class="cycle-section section-shell" id="cycle">
        <div class="cycle-copy reveal">
          <p class="section-kicker">项目迭代</p>
          <h2>不是一条工具线，<br />是一个备赛循环。</h2>
          <p>集训营提供按日训练输入，团队协作推进交付，路演暴露真实问题，评分复盘把问题转成下一轮行动。只要还没到比赛，这个循环就继续。</p>
        </div>

        <div class="cycle-board reveal" data-cycle-board>
          <div class="cycle-center">
            <span>参赛项目</span>
            <strong>持续进化</strong>
            <small>直到正式比赛</small>
          </div>

          <button
            v-for="step in cycleSteps"
            :key="step.key"
            class="cycle-step"
            :class="[step.className, { 'is-active': cycleKey === step.key }]"
            type="button"
            :aria-pressed="cycleKey === step.key"
            @click="cycleKey = step.key"
          >
            <span>{{ step.no }}</span><strong>{{ step.short }}</strong><small>{{ step.hint }}</small>
          </button>

          <svg class="cycle-path" aria-hidden="true" viewBox="0 0 720 520">
            <path d="M183 112 C315 5 510 30 600 160 C680 280 620 430 485 485 C340 545 180 470 118 350 C70 255 88 170 183 112Z" />
          </svg>

          <div class="cycle-detail">
            <span>{{ cycleDetail.label }}</span>
            <strong>{{ cycleDetail.title }}</strong>
            <p>{{ cycleDetail.body }}</p>
          </div>
        </div>
      </section>

      <!-- Creation -->
      <section class="creation-section" id="creation">
        <div class="section-shell">
          <div class="creation-heading reveal">
            <p class="section-kicker">材料工作台</p>
            <h2>项目在变，路演材料也一起长大</h2>
            <p>PPT 与讲稿不是一次性生成文件，而是与项目版本、训练任务和评分反馈共同演进的正式资产。</p>
          </div>

          <div class="creation-grid">
            <article class="creation-card slides-card reveal">
              <div class="creation-card-head">
                <span class="creation-icon">
                  <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m12 3 1.8 4.6L19 9.4l-4 3.1.2 5.2-3.2-2.6-3.2 2.6.2-5.2-4-3.1 5.2-1.8L12 3Z" /></svg>
                </span>
                <div><small>AI 协同创作</small><h3>PPT 制作</h3></div>
                <em>正式版本 V6</em>
              </div>
              <p>从项目资料生成可继续打磨的路演结构，团队编辑后进入历史版本；评分反馈可精确关联页面与交付质量。</p>
              <div class="slide-stack" aria-hidden="true">
                <div class="slide-back" />
                <div class="slide-mid" />
                <div class="slide-front">
                  <span class="slide-no">06 / 28</span>
                  <strong>让数据证明<br />项目价值</strong>
                  <div class="slide-chart"><i /><i /><i /><i /></div>
                  <small>成果验证</small>
                </div>
                <span class="slide-comment">质量检查 · 2</span>
              </div>
              <div class="creation-features"><span>大纲生成</span><span>页面编辑</span><span>历史版本</span><span>下载交付</span></div>
            </article>

            <article class="creation-card script-card reveal">
              <div class="creation-card-head">
                <span class="creation-icon">
                  <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M22 17a2 2 0 0 1-2 2H7l-5 3V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12ZM7 8h10M7 12h7" /></svg>
                </span>
                <div><small>按角色拆分</small><h3>讲稿制作</h3></div>
                <em>总时长 14:30</em>
              </div>
              <p>讲稿可按页面、环节和参演人员拆分；评分反馈落到对应段落，下一版修改有据可查。</p>
              <div class="script-sheet" aria-hidden="true">
                <div class="script-person"><span class="avatar">林</span><strong>林同学 · 开场与项目背景</strong><em>03:20</em></div>
                <p><i>00:00</i>各位评委老师好，今天我们带来的项目，聚焦于……</p>
                <p class="is-highlighted"><i>01:42</i>通过三组试点数据，我们验证了方案在实际场景中的价值。</p>
                <div class="script-comment"><b>改进建议</b>此处与 PPT 第 6 页数据保持一致，并放慢语速。</div>
              </div>
              <div class="creation-features"><span>按成员拆稿</span><span>时长控制</span><span>答辩补充</span><span>版本留痕</span></div>
            </article>
          </div>

          <div class="training-note reveal">
            <div class="training-mark">
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 21V7m4 5 2 2 4-4M22 6V4a1 1 0 0 0-1-1h-5a4 4 0 0 0-4 4 4 4 0 0 0-4-4H3a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h6a3 3 0 0 1 3 3 3 3 0 0 1 3-3h6a1 1 0 0 0 1-1v-1" /></svg>
            </div>
            <div>
              <span>集训营与学习考试跟着项目问题走</span>
              <strong>训练日按日开放，课程、考试与阶段任务服务于当前项目短板，而不是脱离项目单独刷课。</strong>
            </div>
            <a href="#cycle" @click.prevent="scrollTo('cycle')">查看项目循环 <span>→</span></a>
          </div>

          <div class="module-strip reveal" aria-label="平台核心模块">
            <article v-for="mod in modules" :key="mod.title">
              <strong>{{ mod.title }}</strong>
              <p>{{ mod.desc }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- Final CTA -->
      <section class="final-cta" id="start">
        <div class="final-orbit orbit-a" aria-hidden="true" />
        <div class="final-orbit orbit-b" aria-hidden="true" />
        <div class="final-content reveal">
          <div class="final-logo"><img src="/intro-landing/logo.svg" alt="" /></div>
          <p>COMPETITION BRAIN</p>
          <h2>把每一次反馈，<br />变成下一次进步。</h2>
          <span>以项目为中心，从训练、协作、路演到复盘，持续打磨到正式比赛。</span>
          <button type="button" class="final-login" @click="goLogin">进入登录 <b>→</b></button>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div class="footer-inner">
        <a class="brand footer-brand" href="#top" @click.prevent="scrollTo('top')">
          <span class="brand-mark"><img src="/intro-landing/logo.svg" alt="" /></span>
          <span>竞赛大脑</span>
        </a>
        <p>以参赛项目为中心的智能备赛与路演迭代平台</p>
        <div class="footer-links">
          <a v-for="item in navItems" :key="`f-${item.id}`" :href="`#${item.id}`" @click.prevent="scrollTo(item.id)">{{ item.label }}</a>
          <button type="button" @click="goLogin">进入平台</button>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IntroProductPreview from '../components/intro/IntroProductPreview.vue'

import '../styles/intro-landing/style.css'
import '../styles/intro-landing/sections.css'
import '../styles/intro-landing/creation.css'
import '../styles/intro-landing/responsive.css'
import '../styles/intro-landing/intro-local.css'

const router = useRouter()
const pageRef = ref(null)
const menuOpen = ref(false)
const headerScrolled = ref(false)
const activeSection = ref('top')
const previewTab = ref('overview')
const closerTab = ref('project')
const activePreviewNav = ref('home')
const cycleKey = ref('learn')

const navItems = [
  { id: 'product', label: '产品能力' },
  { id: 'feedback', label: '路演反馈' },
  { id: 'cycle', label: '项目循环' },
  { id: 'creation', label: '材料创作' },
]

const previewTabs = [
  { key: 'overview', label: '项目总览' },
  { key: 'feedback', label: '评分反馈' },
  { key: 'tasks', label: '整改任务' },
]

const closerTabs = [
  { key: 'project', label: '项目工作台' },
  { key: 'roadshow', label: '路演评分' },
  { key: 'review', label: '复盘闭环' },
]

const previewNav = [
  { key: 'home', label: '首页' },
  { key: 'tasks', label: '任务管理', count: 2 },
  { key: 'meeting', label: '在线路演' },
  { key: 'ppt', label: 'PPT 制作' },
  { key: 'script', label: '讲稿制作' },
  { key: 'learn', label: '学习中心' },
  { key: 'score', label: '评分报告' },
]

const cycleSteps = [
  { key: 'learn', no: '01', short: '学', hint: '训练输入', className: 'step-learn' },
  { key: 'build', no: '02', short: '练', hint: '项目执行', className: 'step-build' },
  { key: 'show', no: '03', short: '演', hint: '路演验证', className: 'step-show' },
  { key: 'review', no: '04', short: '评', hint: '评分复盘', className: 'step-review' },
  { key: 'improve', no: '05', short: '改', hint: '整改优化', className: 'step-improve' },
]

const cycleContent = {
  learn: {
    label: '当前环节 · 学',
    title: '根据项目短板补充知识与训练',
    body: '集训营按日开放任务，课程与考试服务于当前项目问题，而不是脱离项目单独刷课。',
  },
  build: {
    label: '当前环节 · 练',
    title: '团队把知识转成可交付成果',
    body: '任务管理推进 PPT、讲稿、证据材料与团队协作，形成下一次路演可验证的版本。',
  },
  show: {
    label: '当前环节 · 演',
    title: '用真实路演暴露项目问题',
    body: '线上路演或上传视频评分，完整采集录像、转写和过程数据。',
  },
  review: {
    label: '当前环节 · 评',
    title: 'AI 分析与教师裁决相互补充',
    body: '评分关联具体页面、讲稿段落和视频时间点，让每一条反馈都有清晰依据。',
  },
  improve: {
    label: '当前环节 · 改',
    title: '把反馈变成下一轮执行任务',
    body: '教师审核建议、分配人员并设置验收；完成后回到下一轮路演继续验证。',
  },
}

const modules = [
  { title: '集训营 / 训练日', desc: '按日开放学习与提交，支持教师提前解锁。' },
  { title: '任务管理', desc: '训练营任务、团队自建与评分改进统一处理。' },
  { title: '在线路演', desc: '会议室彩排、录制回放与视频上传评分。' },
  { title: '学习与考试', desc: '课程资料、测评练习与错题复盘同节奏推进。' },
  { title: '路演评分报告', desc: '规则账本、证据与下一场任务书，不是第二官方分。' },
  { title: '奖状与成长', desc: '教师可颁发个人/团队奖状，学生个人中心查看。' },
]

const cycleDetail = computed(() => cycleContent[cycleKey.value])

let revealObserver
let navObserver
let scrollRaf

function goLogin() {
  menuOpen.value = false
  router.push('/login')
}

function scrollTo(sectionId) {
  const scroller = pageRef.value
  if (!scroller) return
  if (sectionId === 'top') {
    animateScroll(scroller, 0)
    activeSection.value = 'top'
    return
  }
  const target = scroller.querySelector(`#${sectionId}`)
  if (!target) return
  const headerHeight = scroller.querySelector('.site-header')?.offsetHeight || 72
  const top = Math.max(target.offsetTop - headerHeight - 8, 0)
  activeSection.value = sectionId
  animateScroll(scroller, top)
}

function animateScroll(scroller, targetTop) {
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
  const startTop = scroller.scrollTop
  const distance = targetTop - startTop
  if (Math.abs(distance) < 2 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    scroller.scrollTop = targetTop
    return
  }
  const duration = Math.min(820, Math.max(420, Math.abs(distance) * 0.3))
  const startTime = performance.now()
  const ease = (p) => 1 - (1 - p) ** 5
  const step = (now) => {
    const p = Math.min((now - startTime) / duration, 1)
    scroller.scrollTop = startTop + distance * ease(p)
    if (p < 1) scrollRaf = requestAnimationFrame(step)
    else scrollRaf = null
  }
  scrollRaf = requestAnimationFrame(step)
}

function onPageScroll() {
  const scroller = pageRef.value
  if (!scroller) return
  headerScrolled.value = scroller.scrollTop > 42
}

watch(menuOpen, (open) => {
  document.body.classList.toggle('menu-open', open)
})

onMounted(() => {
  const scroller = pageRef.value
  if (!scroller) return

  scroller.addEventListener('scroll', onPageScroll, { passive: true })
  onPageScroll()

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const revealItems = scroller.querySelectorAll('.reveal')
  if (reducedMotion || !('IntersectionObserver' in window)) {
    revealItems.forEach((item) => item.classList.add('is-visible'))
  } else {
    revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      })
    }, { threshold: 0.12, root: scroller, rootMargin: '0px 0px -40px' })
    revealItems.forEach((item) => revealObserver.observe(item))
  }

  const sections = Array.from(scroller.querySelectorAll('main section[id]'))
  if ('IntersectionObserver' in window) {
    navObserver = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
      if (!visible) return
      activeSection.value = visible.target.id
    }, {
      root: scroller,
      threshold: [0.18, 0.35, 0.55],
      rootMargin: '-18% 0px -58%',
    })
    sections.forEach((section) => navObserver.observe(section))
  }

  const initial = window.location.hash.replace('#', '')
  if (initial) requestAnimationFrame(() => scrollTo(initial))

  const onKey = (event) => {
    if (event.key === 'Escape') menuOpen.value = false
  }
  const onResize = () => {
    if (window.innerWidth > 860) menuOpen.value = false
  }
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
  pageRef.value._cleanup = () => {
    window.removeEventListener('keydown', onKey)
    window.removeEventListener('resize', onResize)
  }
})

onUnmounted(() => {
  pageRef.value?.removeEventListener('scroll', onPageScroll)
  pageRef.value?._cleanup?.()
  revealObserver?.disconnect()
  navObserver?.disconnect()
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
  document.body.classList.remove('menu-open')
})
</script>

<style scoped>
/* Layout shell only; visual rules live in intro-local.css */
.landing-page {
  height: 100%;
  min-height: 100%;
}
</style>
