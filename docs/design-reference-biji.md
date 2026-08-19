# 得到大脑（biji.com）设计参照 · 实测笔记

> 来源：`https://www.biji.com/note` 登录态截图像素抽样 + `fe-static/prod/home/css/home.*.css` 高频色  
> 用途：竞赛大脑用户端视觉对齐；禁止再凭感觉写「纯白无阴影」式伪极简

## 布局气质

- 三栏工作台：左导航浅灰分区 / 主区纯白 / 右 AI 纯白
- 导航激活：白底圆角块 + 轻阴影（在灰侧栏上浮起）
- 主区列表卡：白底、清晰冷灰描边、轻 elevation
- 无页面渐变底、无毛玻璃、无新拟态厚投影

## 实机 CSS（用户从 DevTools 摘录）

```css
.editor-wrapper.mini {
  background: #fff;
  border: 1px solid #e2e4ea;
  border-radius: 14px;
}
.editor-wrapper {
  min-height: 72px;
  padding: 16px 14px 12px;
  background: #fff;
  transition: all 0.2s ease;
}
/* 全局 */
*, ::before, ::after {
  border-color: #e5e7eb;
}
/* 默认无阴影 */
--tw-shadow: 0 0 rgba(0, 0, 0, 0);
/* 滚动条 */
scrollbar-color: hsl(240, 5.9%, 90%) transparent;
```

## 实测 Token

| 角色 | 色值 |
|------|------|
| 主文字 | `#1d2129` |
| 次文字 | `#292d34` |
| 说明 | `#8a8f99` |
| 极次 | `#adb5bd` |
| 主区 | `#ffffff` |
| 侧栏 | `#f5f5f5` |
| 弱底 | `#f5f7fa` / `#f2f2f3` / `#f6f6f7` |
| 内容框描边 | `#e2e4ea`（editor-wrapper） |
| 全局线 | `#e5e7eb` |
| 品牌紫（AI） | `#766af6` / `#8277f5` |
| 行动橙 | 竞赛大脑自有橙；营销站见 `#ff6a41` |

## 阴影与圆角

- **内容卡/编辑器默认：无投影**，只靠 `1px #e2e4ea`
- 圆角：`14px`（editor-wrapper.mini）
- 内边距参考：`16px 14px 12px`
- 浮层（下拉/弹层）才允许轻阴影

## 落到竞赛大脑

见 `frontend/user/src/styles/workspace-tokens.css` 与 `frontend/user/DESIGN.md`。
