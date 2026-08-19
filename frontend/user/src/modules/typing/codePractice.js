/**
 * 打字 · 代码练习
 * - 语言样例与规范提示
 * - 字符级 token 类名（语法高亮），供练习区叠加着色
 */

export const CODE_LANG_OPTIONS = [
  { value: 'javascript', label: 'JavaScript / TS', short: 'JS' },
  { value: 'java', label: 'Java', short: 'Java' },
  { value: 'python', label: 'Python', short: 'Py' },
  { value: 'sql', label: 'SQL', short: 'SQL' },
  { value: 'html', label: 'HTML / Vue', short: 'HTML' },
  { value: 'css', label: 'CSS', short: 'CSS' },
  { value: 'json', label: 'JSON', short: 'JSON' },
  { value: 'plaintext', label: '纯文本', short: 'Text' },
]

/** 按语言约定缩进字符串 */
export function indentUnitForLang(lang) {
  if (lang === 'python' || lang === 'java') return '    '
  if (lang === 'plaintext') return '\t'
  return '  '
}

/** 行数 / 字符数 / 预估时长（秒，按 ~120 CPM 码） */
export function countCodeStats(text) {
  const s = String(text || '')
  const chars = [...s].length
  const lines = s ? s.split('\n').length : 0
  const estSec = chars ? Math.max(30, Math.round((chars / 120) * 60)) : 0
  return { chars, lines, estSec }
}

/** 编码规范提示（轻量，非长文） */
export const CODE_STYLE_TIPS = {
  javascript: [
    '缩进统一 2 空格；字符串优先单引号或模板字符串',
    '标识符用 camelCase；常量 UPPER_SNAKE',
    '语句末尾分号保持全文一致',
  ],
  java: [
    '缩进 4 空格；类名 PascalCase，方法 camelCase',
    '大括号 K&R：) { 同行；一行一句',
    '包名全小写，常量 UPPER_SNAKE',
  ],
  python: [
    '缩进 4 空格（勿混用 Tab）',
    '函数/变量 snake_case；类 PascalCase',
    'import 分组：标准库 → 第三方 → 本地',
  ],
  sql: [
    '关键字大写（SELECT / FROM / WHERE）更易扫读',
    '子句换行对齐；逗号置前或置后保持统一',
    '表别名简短有意义',
  ],
  html: [
    '标签小写；属性双引号',
    '缩进 2 空格；合理换行嵌套',
    'Vue：指令 v- 与 :/@ 绑定保持规范',
  ],
  css: [
    '缩进 2 空格；选择器与 { 同行',
    '属性按布局 → 盒模型 → 外观分组',
    '颜色优先设计 token / 语义色',
  ],
  json: [
    '严格双引号；无尾逗号',
    '2 空格缩进；键名语义化',
  ],
  plaintext: ['保持原文空格与换行，按真实交付格式练习'],
}

const SAMPLES = {
  javascript: [
    {
      title: '评分汇总工具函数',
      level: '入门',
      content: `// 路演评分：汇总五维均分
export function calcOverall(dimensions = []) {
  if (!dimensions.length) return 0
  const sum = dimensions.reduce((acc, d) => acc + Number(d.score || 0), 0)
  return Math.round((sum / dimensions.length) * 10) / 10
}

export async function loadReport(sessionId) {
  const res = await fetch(\`/api/ai-score/report/\${sessionId}\`)
  if (!res.ok) throw new Error('report_load_failed')
  const data = await res.json()
  return {
    overall: calcOverall(data.dimensions),
    todos: data.todos || [],
  }
}
`,
    },
    {
      title: '防抖与表单校验',
      level: '进阶',
      content: `export function debounce(fn, wait = 200) {
  let timer = null
  return function debounced(...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      fn.apply(this, args)
    }, wait)
  }
}

export function validateTeamForm(form) {
  const errors = {}
  if (!form.name?.trim()) errors.name = '请填写项目名称'
  if (!Array.isArray(form.members) || form.members.length < 2) {
    errors.members = '至少 2 名队员'
  }
  return { ok: Object.keys(errors).length === 0, errors }
}
`,
    },
  ],
  java: [
    {
      title: '训练任务实体',
      level: '入门',
      content: `// 训练日任务状态
public class TrainingTask {
    private final Long id;
    private final String title;
    private String status = "PENDING";

    public TrainingTask(Long id, String title) {
        this.id = id;
        this.title = title;
    }

    public void markDone() {
        if (!"PENDING".equals(status) && !"IN_PROGRESS".equals(status)) {
            throw new IllegalStateException("invalid status: " + status);
        }
        this.status = "DONE";
    }

    public Long getId() {
        return id;
    }
}
`,
    },
    {
      title: 'DTO 转换',
      level: '进阶',
      content: `public class TaskMapper {
    public static TaskView toView(TrainingTask task) {
        if (task == null) {
            return null;
        }
        TaskView view = new TaskView();
        view.setId(task.getId());
        view.setTitle(task.getTitle());
        view.setStatus(task.getStatus());
        view.setDone("DONE".equals(task.getStatus()));
        return view;
    }
}
`,
    },
  ],
  python: [
    {
      title: '完成率与下一项',
      level: '入门',
      content: `# 备赛进度：完成率
from typing import List, Dict

def completion_rate(tasks: List[Dict]) -> float:
    if not tasks:
        return 0.0
    done = sum(1 for t in tasks if t.get("status") == "done")
    return round(done / len(tasks) * 100, 1)

def next_focus(tasks: List[Dict]) -> str:
    pending = [t for t in tasks if t.get("status") != "done"]
    if not pending:
        return "今日任务已全部完成"
    return pending[0].get("title") or "下一项待办"
`,
    },
    {
      title: '分组统计',
      level: '进阶',
      content: `from collections import defaultdict
from typing import Dict, List

def group_by_status(tasks: List[Dict]) -> Dict[str, int]:
    counter: Dict[str, int] = defaultdict(int)
    for task in tasks:
        status = str(task.get("status") or "unknown")
        counter[status] += 1
    return dict(sorted(counter.items(), key=lambda x: (-x[1], x[0])))
`,
    },
  ],
  sql: [
    {
      title: '待办任务查询',
      level: '入门',
      content: `SELECT
  t.id,
  t.title,
  t.status,
  u.username AS owner_name
FROM training_task t
JOIN users u ON u.id = t.assignee_id
WHERE t.team_id = :teamId
  AND t.status IN ('PENDING', 'IN_PROGRESS')
ORDER BY t.due_at ASC
LIMIT 20;
`,
    },
  ],
  html: [
    {
      title: '评分卡片模板',
      level: '入门',
      content: `<template>
  <section class="score-card">
    <header>
      <h2>{{ title }}</h2>
      <span class="score">{{ overall }} 分</span>
    </header>
    <ul>
      <li v-for="d in dimensions" :key="d.key">
        {{ d.label }} · {{ d.score }}
      </li>
    </ul>
    <button type="button" @click="openTodos">查看待办</button>
  </section>
</template>
`,
    },
  ],
  css: [
    {
      title: '评分卡片样式',
      level: '入门',
      content: `.score-card {
  display: grid;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
}

.score-card .score {
  font-weight: 700;
  color: #c43a12;
  font-variant-numeric: tabular-nums;
}
`,
    },
  ],
  json: [
    {
      title: '评分摘要 JSON',
      level: '入门',
      content: `{
  "project": "智慧养老",
  "day": 21,
  "overall": 49.5,
  "dimensions": [
    { "key": "professionalism", "score": 3 },
    { "key": "skill", "score": 4 }
  ],
  "nextAction": "完善路演开场 30 秒"
}
`,
    },
  ],
  plaintext: [
    {
      title: '备赛检查清单',
      level: '入门',
      content: `1. 路演开场 30 秒讲清痛点
2. 每张数据页标注来源与日期
3. 演示路径：登录 → 核心流程 → 异常兜底
4. 问答预案：成本、落地、团队分工
`,
    },
  ],
}

export function listCodeSamples(lang) {
  const key = CODE_LANG_OPTIONS.some((o) => o.value === lang) ? lang : 'javascript'
  const list = SAMPLES[key] || SAMPLES.javascript
  return list.map((item, idx) => {
    const content = String(item.content || '').trimEnd() + '\n'
    const stats = countCodeStats(content)
    return {
      id: `${key}-sample-${idx + 1}`,
      lang: key,
      title: item.title || `样例 ${idx + 1}`,
      level: item.level || '入门',
      content,
      chars: stats.chars,
      lines: stats.lines,
    }
  })
}

/** 高亮 HTML（hljs 已转义，可用于预览 v-html） */
export async function highlightCodeHtml(text, lang = 'javascript') {
  const src = String(text || '')
  if (!src || lang === 'plaintext') {
    return escapeHtml(src)
  }
  try {
    const hljs = await loadHighlight()
    if (hljs) {
      const language = normalizeHljsLang(lang)
      try {
        return hljs.highlight(src, { language, ignoreIllegals: true }).value
      } catch {
        return hljs.highlightAuto(src).value
      }
    }
  } catch {
    /* fallthrough */
  }
  return escapeHtml(src)
}

function escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function getStyleTips(lang) {
  return CODE_STYLE_TIPS[lang] || CODE_STYLE_TIPS.plaintext
}

export function detectCodeLanguage(text) {
  const s = String(text || '')
  if (!s.trim()) return 'javascript'
  if (/^\s*\{[\s\S]*\}\s*$/.test(s.trim()) && /"[^"]+"\s*:/.test(s)) return 'json'
  if (/SELECT\s+[\s\S]+FROM\s+/i.test(s) || /INSERT\s+INTO/i.test(s)) return 'sql'
  if (/^\s*(def |from |import |class ).*:/m.test(s) || /print\s*\(/.test(s)) return 'python'
  if (/public\s+class\s+\w+|System\.out\.|@Override/.test(s)) return 'java'
  if (/<\/?[a-zA-Z][\w:-]*[\s>]/.test(s) || /v-(if|for|model)|@click|{{/.test(s)) return 'html'
  if (/^\s*[\.\#@a-zA-Z][\w\-]*\s*\{/m.test(s) && /:\s*[^;]+;/.test(s)) return 'css'
  if (/=>|const |let |function |export |import /.test(s)) return 'javascript'
  return 'javascript'
}

export function looksLikeCode(text) {
  const s = String(text || '')
  if (!s.trim()) return false
  const newlines = (s.match(/\n/g) || []).length
  if (newlines >= 1 && (/\t| {2,}/.test(s) || /[{};()=<>]|=>|::|\/\//.test(s))) return true
  if (newlines >= 2) return true
  if (/^(import |from |package |def |class |function |const |let |var |public |#include|SELECT )/m.test(s)) {
    return true
  }
  return false
}

/**
 * 将代码转为每个字符的 token 类名（hljs-*）
 * 优先 highlight.js；失败则用轻量规则着色
 * @returns {string[]} length === [...text].length
 */
export async function buildCodeTokenClasses(text, lang = 'javascript') {
  const chars = [...String(text || '')]
  const classes = new Array(chars.length).fill('')
  if (!chars.length || lang === 'plaintext') return classes

  try {
    const hljs = await loadHighlight()
    if (hljs) {
      const language = normalizeHljsLang(lang)
      let result
      try {
        result = hljs.highlight(String(text || ''), { language, ignoreIllegals: true })
      } catch {
        result = hljs.highlightAuto(String(text || ''))
      }
      applyHtmlTokensToClasses(result.value, classes)
      return classes
    }
  } catch {
    /* fallback */
  }

  applyLightweightTokens(String(text || ''), lang, classes)
  return classes
}

let hljsPromise = null
async function loadHighlight() {
  if (hljsPromise) return hljsPromise
  hljsPromise = import('highlight.js/lib/core')
    .then(async (mod) => {
      const hljs = mod.default
      const langs = await Promise.all([
        import('highlight.js/lib/languages/javascript'),
        import('highlight.js/lib/languages/typescript'),
        import('highlight.js/lib/languages/java'),
        import('highlight.js/lib/languages/python'),
        import('highlight.js/lib/languages/sql'),
        import('highlight.js/lib/languages/xml'),
        import('highlight.js/lib/languages/css'),
        import('highlight.js/lib/languages/json'),
      ])
      hljs.registerLanguage('javascript', langs[0].default)
      hljs.registerLanguage('typescript', langs[1].default)
      hljs.registerLanguage('java', langs[2].default)
      hljs.registerLanguage('python', langs[3].default)
      hljs.registerLanguage('sql', langs[4].default)
      hljs.registerLanguage('xml', langs[5].default)
      hljs.registerLanguage('html', langs[5].default)
      hljs.registerLanguage('css', langs[6].default)
      hljs.registerLanguage('json', langs[7].default)
      return hljs
    })
    .catch(() => null)
  return hljsPromise
}

function normalizeHljsLang(lang) {
  if (lang === 'html' || lang === 'vue') return 'xml'
  if (lang === 'ts') return 'typescript'
  return lang || 'javascript'
}

/** 解析 hljs HTML，写入每个字符的 class（支持 unicode） */
function applyHtmlTokensToClasses(html, classes) {
  const src = String(html || '')
  let i = 0
  let charIndex = 0
  const stack = ['']

  const pushClass = (cls) => {
    const cur = stack[stack.length - 1]
    stack.push(cur ? `${cur} ${cls}` : cls)
  }

  while (i < src.length && charIndex < classes.length) {
    if (src[i] === '<') {
      const close = src.indexOf('>', i)
      if (close < 0) break
      const tag = src.slice(i + 1, close)
      if (tag.startsWith('/')) {
        stack.pop()
      } else if (tag.startsWith('span')) {
        const m = tag.match(/class="([^"]*)"/)
        pushClass(m ? m[1] : '')
      }
      // ignore other tags
      i = close + 1
      continue
    }
    if (src[i] === '&') {
      const semi = src.indexOf(';', i)
      if (semi > i) {
        const ent = src.slice(i, semi + 1)
        const ch = decodeEntity(ent)
        const units = [...ch]
        for (const u of units) {
          if (charIndex >= classes.length) break
          classes[charIndex] = stack[stack.length - 1] || ''
          charIndex += 1
        }
        i = semi + 1
        continue
      }
    }
    // 普通字符（可能是代理对由 [...html] 不适合，按 code unit 再组？
    // hljs 输出按 UTF-16；与 [...text] 对齐：用 code point
    const cp = src.codePointAt(i)
    const ch = String.fromCodePoint(cp)
    classes[charIndex] = stack[stack.length - 1] || ''
    charIndex += 1
    i += ch.length
  }
}

function decodeEntity(ent) {
  const map = {
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&',
    '&quot;': '"',
    '&#39;': "'",
    '&apos;': "'",
  }
  if (map[ent]) return map[ent]
  const num = ent.match(/^&#(\d+);$/)
  if (num) return String.fromCodePoint(Number(num[1]))
  const hex = ent.match(/^&#x([0-9a-fA-F]+);$/)
  if (hex) return String.fromCodePoint(parseInt(hex[1], 16))
  return ent
}

/** 无 hljs 时的轻量着色 */
function applyLightweightTokens(text, lang, classes) {
  const patterns = lightweightPatterns(lang)
  for (const { re, cls } of patterns) {
    re.lastIndex = 0
    let m
    const flags = re.flags.includes('g') ? re.flags : `${re.flags}g`
    const g = new RegExp(re.source, flags)
    while ((m = g.exec(text)) !== null) {
      const start = [...text.slice(0, m.index)].length
      const len = [...m[0]].length
      for (let k = 0; k < len; k += 1) {
        if (start + k < classes.length && !classes[start + k]) {
          classes[start + k] = cls
        }
      }
      if (m[0].length === 0) g.lastIndex += 1
    }
  }
}

function lightweightPatterns(lang) {
  const common = [
    { re: /\/\/[^\n]*/g, cls: 'hljs-comment' },
    { re: /\/\*[\s\S]*?\*\//g, cls: 'hljs-comment' },
    { re: /#[^\n]*/g, cls: 'hljs-comment' },
    { re: /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`/g, cls: 'hljs-string' },
    { re: /\b\d+(?:\.\d+)?\b/g, cls: 'hljs-number' },
  ]
  if (lang === 'python') {
    return [
      ...common,
      { re: /\b(def|class|return|if|elif|else|for|while|import|from|as|try|except|with|yield|async|await|True|False|None|and|or|not|in|is)\b/g, cls: 'hljs-keyword' },
    ]
  }
  if (lang === 'java') {
    return [
      ...common,
      { re: /\b(public|private|protected|class|interface|return|if|else|for|while|new|static|final|void|int|long|boolean|String|throw|throws|try|catch|import|package)\b/g, cls: 'hljs-keyword' },
    ]
  }
  if (lang === 'sql') {
    return [
      { re: /--[^\n]*/g, cls: 'hljs-comment' },
      { re: /'(?:\\.|[^'\\])*'/g, cls: 'hljs-string' },
      { re: /\b\d+(?:\.\d+)?\b/g, cls: 'hljs-number' },
      { re: /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|ON|AND|OR|IN|AS|ORDER|BY|GROUP|LIMIT|INSERT|INTO|UPDATE|SET|DELETE|VALUES|ASC|DESC)\b/gi, cls: 'hljs-keyword' },
    ]
  }
  if (lang === 'json') {
    return [
      { re: /"(?:\\.|[^"\\])*"(?=\s*:)/g, cls: 'hljs-attr' },
      { re: /"(?:\\.|[^"\\])*"/g, cls: 'hljs-string' },
      { re: /\b\d+(?:\.\d+)?\b/g, cls: 'hljs-number' },
      { re: /\b(true|false|null)\b/g, cls: 'hljs-literal' },
    ]
  }
  // js default
  return [
    ...common,
    { re: /\b(const|let|var|function|return|if|else|for|while|class|export|import|from|async|await|new|try|catch|throw|typeof|instanceof)\b/g, cls: 'hljs-keyword' },
    { re: /\b(true|false|null|undefined)\b/g, cls: 'hljs-literal' },
  ]
}

export function normalizeCodeText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/^\n+/, '')
    .replace(/\n+$/, '')
}
