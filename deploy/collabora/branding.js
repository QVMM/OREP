/* 启发 Office branding.js
 * 1) 产品名
 * 2) 强制展开 notebookbar 工具行（修复「开始」下空白）
 *
 * 根因：UIManager 在 prefs text.ShowToolbar===false 时会
 *   $("#toolbar-row").css("display","none") + tabs-collapsed
 * 页签还在、工具区整块空白。父页面同源补救不可靠，必须在 iframe 内修。
 */
(function () {
  'use strict';

  try {
    window.brandProductName = '启发 Office';
    window.brandProductURL = '';
    window.brandProductFAQURL = '';
  } catch (e) { /* ignore */ }

  function injectCss() {
    if (document.getElementById('orep-toolbar-force-css')) return;
    var el = document.createElement('style');
    el.id = 'orep-toolbar-force-css';
    el.textContent = [
      'body #toolbar-row,.hasnotebookbar>#toolbar-row{',
      'display:block!important;visibility:visible!important;opacity:1!important;',
      'height:82px!important;max-height:none!important;overflow:visible!important}',
      '.notebookbar-scroll-wrapper,.notebookbar#NotebookBar{',
      'min-height:72px!important;height:82px!important;visibility:visible!important;opacity:1!important}',
      '.root-container.notebookbar,#toolbar-wrapper.hasnotebookbar{',
      'visibility:visible!important;opacity:1!important}',
      /* 隐藏「帮助」页签 */
      '#Help-tab-label,button#Help-tab-label,[id="Help-tab-label"]{',
      'display:none!important;width:0!important;max-width:0!important;',
      'visibility:hidden!important;pointer-events:none!important;overflow:hidden!important}',
    ].join('');
    (document.head || document.documentElement).appendChild(el);
  }

  /** 通过 UIManager 隐藏 Help 页签（比纯 CSS 更稳，防重新渲染冒出） */
  function hideHelpTab() {
    try {
      // 部分 CODE 版本 showNotebookTab 会抛
      // notebookbar.refreshContextTabsVisibility is not a function — 仅用 CSS/DOM 隐藏更稳
      var el = document.getElementById('Help-tab-label');
      if (el) {
        el.style.setProperty('display', 'none', 'important');
        el.setAttribute('hidden', 'true');
        el.setAttribute('aria-hidden', 'true');
      }
    } catch (e) { /* ignore */ }
  }

  /**
   * PPT/Impress：↑↓ / PageUp/Down 切换幻灯片。
   *
   * 根因：
   * 1) Collabora 只在 preview.partsFocused 时让方向键切页
   * 2) 编辑态焦点常在隐藏的 clipboard textarea 上——若当成「正在输入」会误拦截
   * 3) 点底部上一页/下一页后焦点离开 clipboard，键位才“突然可用”
   *
   * 策略：演示文档中，非对话框真实输入时，↑↓ 始终切页；
   * 仅当明确在编辑文本形状（selectionType===text）时不抢方向键。
   */
  function setupImpressSlideKeys() {
    if (window.__orepImpressKeys) return;
    window.__orepImpressKeys = true;

    function getMap() {
      try {
        return window.app && window.app.map;
      } catch (e) {
        return null;
      }
    }

    function isPresentationDoc() {
      try {
        var map = getMap();
        var dt = map && map._docLayer && map._docLayer._docType;
        return dt === 'presentation' || dt === 'drawing';
      } catch (e) {
        return false;
      }
    }

    function markPartsFocused() {
      try {
        var map = getMap();
        var preview = map && map._docLayer && map._docLayer._preview;
        if (preview) {
          preview.partsFocused = true;
          preview.partsFocusedApplied = true;
        }
      } catch (e) { /* ignore */ }
    }

    /** Collabora 用于键入的隐藏 clipboard，不是用户表单 */
    function isCollaboraClipboard(el) {
      if (!el) return false;
      try {
        if (el.id === 'clipboard-area' || el.id === 'copy-paste-container') return true;
        if (el.classList) {
          if (el.classList.contains('clipboard')) return true;
          if (el.classList.contains('clipboard-area')) return true;
        }
        // 常见：body 下隐藏 textarea 承接输入
        if ((el.tagName || '').toLowerCase() === 'textarea') {
          var st = window.getComputedStyle ? window.getComputedStyle(el) : null;
          if (st && (st.opacity === '0' || st.position === 'absolute' || parseInt(st.left, 10) < -100)) {
            return true;
          }
        }
      } catch (e) { /* ignore */ }
      return false;
    }

    /** 对话框 / 真正的表单输入（不要抢键） */
    function isRealFormField() {
      try {
        var el = document.activeElement;
        if (!el || isCollaboraClipboard(el)) return false;
        if (el.closest && el.closest('.jsdialog-container, .ui-dialog, .lokdialog, #mobile-wizard, .ui-listbox-container')) {
          var tag = (el.tagName || '').toLowerCase();
          if (tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable) return true;
        }
        if (window.JSDialog && typeof JSDialog.IsTextInputField === 'function') {
          if (JSDialog.IsTextInputField(el) && !isCollaboraClipboard(el)) return true;
        }
      } catch (e) { /* ignore */ }
      return false;
    }

    /** 正在编辑幻灯片上的文字（此时 ↑↓ 应移动光标，不切页） */
    function isEditingShapeText() {
      try {
        var map = getMap();
        if (!map) return false;
        var clip = map._clip;
        if (clip) {
          var st = clip._selectionType || clip.selectionType;
          // text = 正文编辑；slide = 幻灯片级选中
          if (st === 'text') return true;
        }
        // 公式栏等
        var el = document.activeElement;
        if (el && el.closest && el.closest('#toolbar-down .ui-content.unospan-formula, .formulabar')) return true;
      } catch (e) { /* ignore */ }
      return false;
    }

    function goSlide(dir) {
      var map = getMap();
      if (!map) return false;
      markPartsFocused();
      try {
        if (typeof map.focus === 'function') map.focus(false);
      } catch (e0) { /* ignore */ }

      // 优先 actionsMap（与底部上一页/下一页同一路径）
      try {
        var actions = map.uiManager && map.uiManager.actionsMap;
        if (dir === 'prev' && actions && typeof actions.previouspart === 'function') {
          actions.previouspart();
          return true;
        }
        if (dir === 'next' && actions && typeof actions.nextpart === 'function') {
          actions.nextpart();
          return true;
        }
      } catch (e1) { /* ignore */ }

      try {
        if (typeof map.setPart === 'function') {
          map.setPart(dir === 'prev' ? 'prev' : 'next');
          return true;
        }
      } catch (e2) { /* ignore */ }

      try {
        if (window.app && app.socket && typeof app.socket.sendMessage === 'function') {
          // 部分版本通过 socket 切 part
          var part = map._docLayer && typeof map._docLayer._selectedPart === 'number'
            ? map._docLayer._selectedPart
            : 0;
          var target = dir === 'prev' ? Math.max(0, part - 1) : part + 1;
          app.socket.sendMessage('setpart part=' + target);
          return true;
        }
      } catch (e3) { /* ignore */ }
      return false;
    }

    function onNavKey(e) {
      if (!isPresentationDoc()) return;
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      var key = e.key;
      if (
        key !== 'ArrowUp' &&
        key !== 'ArrowDown' &&
        key !== 'PageUp' &&
        key !== 'PageDown'
      ) {
        return;
      }
      // 真正表单 / 形状内文字编辑：不抢
      if (isRealFormField()) return;
      if ((key === 'ArrowUp' || key === 'ArrowDown') && isEditingShapeText()) return;

      // 演示中：↑↓ / PgUp/PgDn 切页（不再要求先点过底部按钮或左侧导航）
      e.preventDefault();
      e.stopPropagation();
      if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
      goSlide(key === 'ArrowUp' || key === 'PageUp' ? 'prev' : 'next');
    }

    // 点左侧导航 / 缩略图 / 底部翻页：维持 partsFocused
    document.addEventListener(
      'mousedown',
      function (e) {
        if (!isPresentationDoc()) return;
        var t = e.target;
        if (!t || !t.closest) return;
        if (
          t.closest(
            '#slide-sorter, #presentation-controls-wrapper, .parts-preview, .preview-frame, .preview-img, [id^="preview-frame"], #toolbar-down, .jsdialog.sidebar'
          )
        ) {
          markPartsFocused();
        }
        // 底部上一页/下一页按钮
        if (t.closest('#tb_action_toolbar, .w2ui-tb-button, [id*="prev"], [id*="next"]')) {
          markPartsFocused();
        }
      },
      true
    );

    document.addEventListener('keydown', onNavKey, true);
    // 有些焦点在 window
    window.addEventListener('keydown', onNavKey, true);
  }

  function forceShowToolbar() {
    injectCss();
    hideHelpTab();
    try {
      var row = document.getElementById('toolbar-row');
      if (row) {
        // 清掉 jQuery 写入的 display:none，再用 important 钉死
        row.style.removeProperty('display');
        row.style.setProperty('display', 'block', 'important');
        row.style.setProperty('visibility', 'visible', 'important');
        row.style.setProperty('opacity', '1', 'important');
        row.style.setProperty('height', '82px', 'important');
      }
      var dc = document.getElementById('document-container');
      if (dc && dc.classList) dc.classList.remove('tabs-collapsed');

      var prefs = window.prefs || (window.app && window.app.prefs);
      if (prefs && typeof prefs.set === 'function') {
        try {
          prefs.set('text.ShowToolbar', true);
          prefs.set('spreadsheet.ShowToolbar', true);
          prefs.set('presentation.ShowToolbar', true);
        } catch (e1) { /* ignore */ }
      }

      var ui = window.app && window.app.map && window.app.map.uiManager;
      if (ui) {
        try {
          ui._notebookbarShouldBeCollapsed = false;
        } catch (e2) { /* ignore */ }
        if (typeof ui.extendNotebookbar === 'function') {
          try { ui.extendNotebookbar(); } catch (e3) { /* ignore */ }
        }
        hideHelpTab();
      }

      // 若 Home 工具按钮数为 0，尝试点「开始」页签触发 loadTab
      var tools = document.querySelectorAll(
        '#toolbar-row .unotoolbutton, #toolbar-row .notebookbar .ui-content.unobutton, .notebookbar-scroll-wrapper .unotoolbutton'
      );
      if (!tools || tools.length === 0) {
        var homeTab =
          document.querySelector('button.ui-tab.notebookbar.selected') ||
          document.querySelector('[id$="-tab-label"].selected') ||
          document.querySelector('.notebookbar-tabs-container .ui-tab');
        // 找文本含「开始」或 Home 的页签
        var tabs = document.querySelectorAll('.notebookbar-tabs-container button, .notebookbar-tabs-container .ui-tab, [id$="-tab-label"]');
        for (var i = 0; i < tabs.length; i++) {
          var t = tabs[i];
          var label = (t.textContent || t.getAttribute('aria-label') || '').trim();
          if (label === '开始' || label === 'Home' || /Home|开始/i.test(label)) {
            homeTab = t;
            break;
          }
        }
        if (homeTab && typeof homeTab.click === 'function') {
          try { homeTab.click(); } catch (e4) { /* ignore */ }
        }
      }
    } catch (err) { /* ignore */ }
  }

  injectCss();
  forceShowToolbar();
  setupImpressSlideKeys();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      forceShowToolbar();
      setupImpressSlideKeys();
    });
  }
  window.addEventListener('load', function () {
    forceShowToolbar();
    setupImpressSlideKeys();
  });

  // 首 12 秒内反复纠正（UIManager 可能在文档加载后再次 collapse）
  var n = 0;
  var timer = setInterval(function () {
    forceShowToolbar();
    if (++n >= 48) clearInterval(timer);
  }, 250);

  // 若 UIManager 再次写 display:none，立刻扳回来
  try {
    var obs = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.type === 'attributes' && m.target && m.target.id === 'toolbar-row') {
          var d = m.target.style && m.target.style.display;
          if (d === 'none') forceShowToolbar();
        }
        if (m.type === 'attributes' && m.target && m.target.id === 'document-container') {
          if (m.target.classList && m.target.classList.contains('tabs-collapsed')) {
            forceShowToolbar();
          }
        }
      }
    });
    function startObs() {
      var row = document.getElementById('toolbar-row');
      var dc = document.getElementById('document-container');
      if (row) obs.observe(row, { attributes: true, attributeFilter: ['style', 'class'] });
      if (dc) obs.observe(dc, { attributes: true, attributeFilter: ['class'] });
      // 容器晚到时再挂
      if (!row || !dc) setTimeout(startObs, 500);
    }
    startObs();
  } catch (e5) { /* ignore */ }
})();

var brandProductName = '启发 Office';
var brandProductURL = '';
var brandProductFAQURL = '';
