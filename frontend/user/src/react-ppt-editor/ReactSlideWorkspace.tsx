import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  BringToFront,
  Copy,
  Image,
  Maximize2,
  MousePointer2,
  Play,
  Plus,
  Redo2,
  RefreshCw,
  SendToBack,
  Square,
  Table2,
  Trash2,
  Type,
  Undo2,
  X,
} from "lucide-react";
import { KonvaSlideEditor, type EditorCommand, type EditorCommandType, type EditorState } from "./KonvaSlideEditor";
import type { PreviewSlide, SlideDocument } from "./types";

interface ReactSlideWorkspaceProps {
  slides: PreviewSlide[];
  selectedIndex?: number;
  editable: boolean;
  downloadUrl?: string;
  loading?: boolean;
  onSelect: (index: number) => void;
  onCreateSlide: () => Promise<void> | void;
  onDeleteSlide: (index: number) => Promise<void> | void;
  onRefresh: () => Promise<void> | void;
  onSaveSlide: (slide: PreviewSlide, content: string, document: SlideDocument, notes: string) => Promise<void>;
  onSaveNotes: (slide: PreviewSlide, notes: string) => Promise<{ scriptSynced?: boolean } | void>;
  draftKeyPrefix?: string;
}

type NotesSaveState = "idle" | "dirty" | "saving" | "saved" | "pendingSync" | "local" | "error";

const SPEAKER_NOTES_MAX_LENGTH = 4000;

export function ReactSlideWorkspace({
  slides,
  selectedIndex,
  editable,
  loading,
  onSelect,
  onCreateSlide,
  onDeleteSlide,
  onRefresh,
  onSaveSlide,
  onSaveNotes,
  draftKeyPrefix = "ppt-notes",
}: ReactSlideWorkspaceProps) {
  const slidesDataSignature = slides.map((slide) => [
    slide.index,
    String(slide.content || "").length,
    hashPreviewValue(slide.content),
    hashPreviewValue(slide.notes),
    hashPreviewValue(slide.document?.speakerNotes),
  ].join(":")).join("|");
  const displaySlides = useMemo(
    () => slides.map((slide) => ({
      ...slide,
      content: cleanSvgForInline(slide.content),
      notes: resolvePreviewSlideNotes(slide),
    })),
    [slides, slidesDataSignature],
  );
  const selectedSlide = displaySlides.find((slide) => slide.index === selectedIndex) ?? displaySlides[0];
  const [editorCommand, setEditorCommand] = useState<EditorCommand | undefined>(undefined);
  const [editorState, setEditorState] = useState<EditorState>({
    autoSave: true,
    saveState: "idle",
    canEdit: editable,
    canUndo: false,
    canRedo: false,
  });
  const [notesDraft, setNotesDraft] = useState(selectedSlide?.notes ?? "");
  const [notesDrawerOpen, setNotesDrawerOpen] = useState(false);
  const [notesSaveState, setNotesSaveState] = useState<NotesSaveState>("idle");
  const [recoverableDraft, setRecoverableDraft] = useState<string | null>(null);
  const [slideshowOpen, setSlideshowOpen] = useState(false);
  const [slideshowIndex, setSlideshowIndex] = useState(0);
  const [speakerOpen, setSpeakerOpen] = useState(false);
  const [speakerIndex, setSpeakerIndex] = useState(0);
  const [speakerCountdown, setSpeakerCountdown] = useState<number | null>(null);
  const [speakerStarted, setSpeakerStarted] = useState(false);
  const [speakerStartedAt, setSpeakerStartedAt] = useState<number | null>(null);
  const [speakerNow, setSpeakerNow] = useState(Date.now());
  const speakerOverlayRef = useRef<HTMLDivElement | null>(null);
  const notesStorageKey = selectedSlide ? `${draftKeyPrefix}:${selectedSlide.index}` : "";
  const speakerSlide = displaySlides[speakerIndex];
  const speakerNextSlide = displaySlides[speakerIndex + 1];
  const speakerElapsed = speakerStartedAt ? formatSpeakerElapsed(speakerNow - speakerStartedAt) : "00:00";

  useEffect(() => {
    const serverNotes = selectedSlide?.notes ?? "";
    setNotesDraft(serverNotes);
    setNotesSaveState("idle");
    if (!selectedSlide || !notesStorageKey) {
      setRecoverableDraft(null);
      return;
    }
    try {
      const cached = window.localStorage.getItem(notesStorageKey);
      setRecoverableDraft(cached && cached !== serverNotes ? cached : null);
    } catch {
      setRecoverableDraft(null);
    }
  }, [selectedSlide?.index, selectedSlide?.notes, notesStorageKey]);

  useEffect(() => {
    if (!selectedSlide || !notesStorageKey) return;
    const serverNotes = selectedSlide.notes ?? "";
    try {
      if (notesDraft !== serverNotes) {
        window.localStorage.setItem(notesStorageKey, notesDraft);
      } else {
        window.localStorage.removeItem(notesStorageKey);
      }
    } catch {
      if (notesDraft !== serverNotes) setNotesSaveState("local");
    }
  }, [notesDraft, notesStorageKey, selectedSlide]);

  useEffect(() => {
    if (!slideshowOpen) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSlideshowOpen(false);
      if (event.key === "ArrowRight" || event.key === " ") setSlideshowIndex((index) => Math.min(displaySlides.length - 1, index + 1));
      if (event.key === "ArrowLeft") setSlideshowIndex((index) => Math.max(0, index - 1));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [slideshowOpen, displaySlides.length]);

  useEffect(() => {
    if (!speakerOpen) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeSpeakerView();
        return;
      }
      if (event.key === "Enter" && !speakerStarted && speakerCountdown === null) {
        startSpeakerCountdown();
        return;
      }
      if (event.key.toLowerCase() === "f") {
        void requestSpeakerFullscreen();
        return;
      }
      if (event.key === "ArrowRight" || event.key === " ") {
        event.preventDefault();
        goSpeakerNext();
      }
      if (event.key === "ArrowLeft") goSpeakerPrev();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [speakerOpen, speakerStarted, speakerCountdown, displaySlides.length]);

  useEffect(() => {
    if (!speakerOpen || speakerCountdown === null) return undefined;
    if (speakerCountdown <= 0) {
      const now = Date.now();
      setSpeakerCountdown(null);
      setSpeakerStarted(true);
      setSpeakerStartedAt(now);
      setSpeakerNow(now);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      setSpeakerCountdown((value) => (value === null ? null : value - 1));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [speakerOpen, speakerCountdown]);

  useEffect(() => {
    if (!speakerOpen || !speakerStarted) return undefined;
    const timer = window.setInterval(() => setSpeakerNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [speakerOpen, speakerStarted]);

  const runCommand = (type: EditorCommandType) => {
    setEditorCommand({ type, id: Date.now() });
  };

  const saveSlide = async (slide: PreviewSlide, content: string, document: SlideDocument) => {
    await onSaveSlide(slide, content, { ...document, speakerNotes: notesDraft }, notesDraft);
  };

  const saveNotesDraft = useCallback(async () => {
    if (!selectedSlide || !editable || notesDraft === (selectedSlide.notes ?? "")) return;
    setNotesSaveState("saving");
    try {
      const result = await onSaveNotes(selectedSlide, notesDraft);
      if (notesStorageKey) window.localStorage.removeItem(notesStorageKey);
      setRecoverableDraft(null);
      if (result?.scriptSynced === false) {
        setNotesSaveState("pendingSync");
        return;
      }
      setNotesSaveState("saved");
      window.setTimeout(() => setNotesSaveState("idle"), 1600);
    } catch {
      setNotesSaveState("error");
    }
  }, [editable, notesDraft, notesStorageKey, onSaveNotes, selectedSlide]);

  useEffect(() => {
    if (notesSaveState !== "dirty") return undefined;
    const timer = window.setTimeout(() => {
      void saveNotesDraft();
    }, 2200);
    return () => window.clearTimeout(timer);
  }, [notesSaveState, notesDraft, saveNotesDraft]);

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (notesSaveState !== "dirty" && notesSaveState !== "local" && notesSaveState !== "saving") return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [notesSaveState]);

  const restoreLocalDraft = () => {
    if (!recoverableDraft) return;
    setNotesDraft(recoverableDraft);
    setNotesSaveState("dirty");
    setRecoverableDraft(null);
    setNotesDrawerOpen(true);
  };

  const startSlideshow = () => {
    const index = Math.max(0, displaySlides.findIndex((slide) => slide.index === selectedSlide?.index));
    setSlideshowIndex(index);
    setSlideshowOpen(true);
  };

  const openSpeakerView = () => {
    const index = Math.max(0, displaySlides.findIndex((slide) => slide.index === selectedSlide?.index));
    setSpeakerIndex(index);
    setSpeakerOpen(true);
    setSpeakerCountdown(null);
    setSpeakerStarted(false);
    setSpeakerStartedAt(null);
    setSpeakerNow(Date.now());
  };

  const closeSpeakerView = () => {
    const fullscreenElement = document.fullscreenElement;
    if (fullscreenElement && fullscreenElement === speakerOverlayRef.current && document.exitFullscreen) {
      void document.exitFullscreen().catch(() => {});
    }
    setSpeakerOpen(false);
    setSpeakerCountdown(null);
    setSpeakerStarted(false);
    setSpeakerStartedAt(null);
  };

  const startSpeakerCountdown = () => {
    setSpeakerCountdown(3);
    setSpeakerStarted(false);
    setSpeakerStartedAt(null);
    setSpeakerNow(Date.now());
  };

  const requestSpeakerFullscreen = async () => {
    const target = speakerOverlayRef.current;
    if (!target?.requestFullscreen) return;
    try {
      await target.requestFullscreen();
    } catch {
      // Browser may reject fullscreen without direct user gesture.
    }
  };

  const goSpeakerNext = () => {
    if (!displaySlides.length) return;
    setSpeakerIndex((index) => Math.min(displaySlides.length - 1, index + 1));
  };

  const goSpeakerPrev = () => {
    setSpeakerIndex((index) => Math.max(0, index - 1));
  };

  const speakerOverlay = speakerOpen && speakerSlide ? (
    <div className="ppa-speaker-view-overlay" ref={speakerOverlayRef} role="dialog" aria-modal="true" aria-label="演讲者视图">
      <header className="ppa-speaker-view-topbar">
        <div>
          <span>演讲模式</span>
          <strong>演讲者视图</strong>
        </div>
        <div className="ppa-speaker-view-actions">
          <button type="button" onClick={() => void requestSpeakerFullscreen()}><Maximize2 size={15} /> 全屏</button>
          <button type="button" onClick={closeSpeakerView}><X size={15} /> 退出</button>
        </div>
      </header>

      <div className="ppa-speaker-view-body">
        <section className="ppa-speaker-current">
          <div
            className="ppa-speaker-slide"
            onClick={() => {
              if (speakerStarted && speakerCountdown === null) goSpeakerNext();
            }}
            role="button"
            tabIndex={0}
            aria-label="点击进入下一页"
            dangerouslySetInnerHTML={{ __html: speakerSlide.content }}
          />
          {!speakerStarted || speakerCountdown !== null ? (
            <div className="ppa-speaker-start-layer">
              {speakerCountdown !== null ? (
                <div className="ppa-speaker-countdown" key={speakerCountdown}>{speakerCountdown}</div>
              ) : (
                <button type="button" className="ppa-speaker-start-button" onClick={startSpeakerCountdown}>
                  <Play size={18} /> 开始演讲
                </button>
              )}
            </div>
          ) : null}
        </section>

        <aside className="ppa-speaker-side">
          <section className="ppa-speaker-runtime">
            <div><small>当前页</small><strong>{speakerIndex + 1} / {displaySlides.length}</strong></div>
            <div><small>计时</small><strong>{speakerElapsed}</strong></div>
            <div><small>状态</small><strong>{speakerStarted ? "进行中" : speakerCountdown !== null ? "倒计时" : "待开始"}</strong></div>
          </section>

          <section className="ppa-speaker-card ppa-speaker-script-card">
            <div className="ppa-speaker-card-head">
              <span>当前页讲稿</span>
              <strong>第 {speakerSlide.index} 页讲稿</strong>
            </div>
            <div className="ppa-speaker-script">
              {String(speakerSlide.notes || "").trim() ? (
                <p>{speakerSlide.notes}</p>
              ) : (
                <p className="ppa-speaker-muted">当前页还没有讲稿。可以退出后在底部讲稿栏补充。</p>
              )}
            </div>
          </section>

          <section className="ppa-speaker-card ppa-speaker-next-card">
            <div className="ppa-speaker-card-head">
              <span>下一页</span>
              <strong>{speakerNextSlide ? `第 ${speakerNextSlide.index} 页` : "最后一页"}</strong>
            </div>
            {speakerNextSlide ? (
              <div className="ppa-speaker-next-thumb" dangerouslySetInnerHTML={{ __html: speakerNextSlide.content }} />
            ) : (
              <p className="ppa-speaker-muted">已经没有下一页。</p>
            )}
          </section>

          <div className="ppa-speaker-nav">
            <button type="button" disabled={speakerIndex <= 0} onClick={goSpeakerPrev}>上一页</button>
            <button type="button" disabled={speakerIndex >= displaySlides.length - 1} onClick={goSpeakerNext}>下一页</button>
          </div>
          <p className="ppa-speaker-help">点击 PPT 主画面下一页，方向键翻页，F 全屏，Esc 退出。</p>
        </aside>
      </div>
    </div>
  ) : null;

  return (
    <main className="ppa-slide-workspace">
      <div className="ppa-slide-toolbar">
        <button type="button" disabled={!editable} onClick={onCreateSlide}><Plus size={15} /> 新建页</button>
        <span className="ppa-toolbar-divider" />
        <button title="编辑文字" type="button" disabled={!editable} onClick={() => runCommand("addText")}><Type size={15} /></button>
        <button title="形状" type="button" disabled={!editable} onClick={() => runCommand("addRect")}><Square size={15} /></button>
        <button title="图片" type="button" disabled={!editable} onClick={() => runCommand("addImage")}><Image size={15} /></button>
        <button title="表格" type="button" disabled={!editable} onClick={() => runCommand("addTable")}><Table2 size={15} /></button>
        <span className="ppa-toolbar-divider" />
        <button title="撤销" type="button" disabled={!editable || !editorState.canUndo} onClick={() => runCommand("undo")}><Undo2 size={15} /></button>
        <button title="重做" type="button" disabled={!editable || !editorState.canRedo} onClick={() => runCommand("redo")}><Redo2 size={15} /></button>
        <button title="复制" type="button" disabled={!editable || !editorState.selectedType} onClick={() => runCommand("duplicate")}><Copy size={15} /></button>
        <button title="删除元素" type="button" disabled={!editable || !editorState.selectedType} onClick={() => runCommand("delete")}><Trash2 size={15} /></button>
        <span className="ppa-toolbar-divider" />
        <button title="下移一层" type="button" disabled={!editable || !editorState.selectedType} onClick={() => runCommand("backward")}><SendToBack size={15} /></button>
        <button title="上移一层" type="button" disabled={!editable || !editorState.selectedType} onClick={() => runCommand("forward")}><BringToFront size={15} /></button>
        <span className="ppa-toolbar-divider" />
        <button type="button" disabled={!editable} onClick={() => runCommand("toggleAutosave")}>自动保存</button>
        <button title="刷新" type="button" onClick={onRefresh}><RefreshCw size={15} /></button>
        <span className="ppa-toolbar-spacer" />
        <button className="ppa-toolbar-action" type="button" disabled={!displaySlides.length} onClick={startSlideshow}><Play size={15} /> 投影</button>
        <button className="ppa-toolbar-action ppa-toolbar-action-primary" type="button" disabled={!displaySlides.length} onClick={openSpeakerView}>
          演讲者视图
        </button>
        <span className="ppa-toolbar-status"><MousePointer2 size={15} /> 适应</span>
        <span className="ppa-toolbar-status">16:9</span>
      </div>

      <div className="ppa-slide-stage">
        <div className="ppa-thumbnail-rail">
          {loading ? Array.from({ length: 5 }).map((_, index) => (
            <button type="button" className={`ppa-rail-slide ${index === 0 ? "ppa-rail-slide-active" : ""}`} key={index} disabled>
              <span>{index + 1}</span>
              <div className="ppa-rail-placeholder" />
            </button>
          )) : displaySlides.length ? displaySlides.map((slide) => (
            <div
              key={slide.index}
              className={`ppa-rail-slide ${selectedSlide?.index === slide.index ? "ppa-rail-slide-active" : ""}`}
            >
              <span>{String(slide.index).padStart(2, "0")}</span>
              <div className="ppa-rail-thumb-wrap">
                <button
                  type="button"
                  className="ppa-rail-thumb-button"
                  onClick={() => onSelect(slide.index)}
                  aria-label={`选择第 ${slide.index} 页`}
                >
                  <div dangerouslySetInnerHTML={{ __html: slide.content }} />
                </button>
                {editable && displaySlides.length > 1 ? (
                  <button
                    type="button"
                    className="ppa-rail-delete"
                    onClick={(event) => {
                      event.stopPropagation();
                      void onDeleteSlide(slide.index);
                    }}
                    aria-label={`删除第 ${slide.index} 页`}
                    title="删除此页"
                  >
                    <Trash2 size={13} />
                  </button>
                ) : null}
              </div>
            </div>
          )) : (
            <button type="button" className="ppa-rail-slide ppa-rail-slide-active">
              <span>1</span>
              <div className="ppa-rail-placeholder" />
            </button>
          )}
          <button className="ppa-rail-add" type="button" disabled={!editable} onClick={onCreateSlide}>
            <Plus size={18} />
          </button>
        </div>

        <div className="ppa-slide-canvas-area">
          {selectedSlide ? (
            <KonvaSlideEditor
              slide={selectedSlide}
              editable={editable}
              command={editorCommand}
              onStateChange={setEditorState}
              onSave={saveSlide}
            />
          ) : (
            <div className="ppa-empty-frame" />
          )}
          <section className="ppa-speaker-strip" aria-label="本页讲稿">
            <div className="ppa-speaker-strip-copy">
              <strong><span /> 讲稿状态 · {notesDraft.trim() ? "已生成" : "待补充"} · {notesSaveStateLabel(notesSaveState)}</strong>
              <p>{notesDraft.trim() || "当前页还没有讲稿。生成完成后会自动沉淀到这里，也可以手动补充。"}</p>
              {recoverableDraft ? (
                <button type="button" className="ppa-link-button" onClick={restoreLocalDraft}>检测到刷新前草稿，点击恢复</button>
              ) : null}
            </div>
            <div className="ppa-speaker-strip-actions">
              <button type="button" disabled={!selectedSlide} onClick={() => setNotesDrawerOpen(true)}>展开讲稿</button>
              <button type="button" disabled={!editable || !selectedSlide || notesDraft === (selectedSlide?.notes ?? "")} onClick={() => void saveNotesDraft()}>
                保存讲稿
              </button>
            </div>
          </section>
        </div>
      </div>

      {notesDrawerOpen ? (
        <div className="ppa-notes-drawer-overlay" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setNotesDrawerOpen(false);
        }}>
          <aside className="ppa-notes-drawer" role="dialog" aria-modal="true" aria-label="本页讲稿编辑">
            <div className="ppa-notes-drawer-head">
              <div>
                <span>讲稿编辑</span>
                <strong>第 {selectedSlide?.index ?? "-"} 页讲稿</strong>
              </div>
              <button type="button" onClick={() => setNotesDrawerOpen(false)} aria-label="关闭讲稿面板"><X size={17} /></button>
            </div>
            {recoverableDraft ? (
              <div className="ppa-notes-recovery">
                <span>检测到刷新或离开前未保存的本地草稿。</span>
                <button type="button" onClick={restoreLocalDraft}>恢复草稿</button>
              </div>
            ) : null}
            <div className="ppa-notes-meta">
              <div><small>保存状态</small><strong>{notesSaveStateLabel(notesSaveState)}</strong></div>
              <div><small>字数</small><strong>{notesDraft.length} / {SPEAKER_NOTES_MAX_LENGTH}</strong></div>
            </div>
            <label className="ppa-notes-editor">
              <span>正式讲稿</span>
              <textarea
                value={notesDraft}
                maxLength={SPEAKER_NOTES_MAX_LENGTH}
                disabled={!editable || !selectedSlide}
                placeholder="输入本页讲稿。系统会自动保护未保存草稿，刷新后可恢复。"
                onChange={(event) => {
                  setNotesDraft(event.target.value);
                  setNotesSaveState("dirty");
                }}
                onBlur={() => void saveNotesDraft()}
              />
            </label>
            <div className="ppa-notes-tip">
              手动修改会优先保留。后续接入 AI 重写时，只在用户确认后更新。
            </div>
            <div className="ppa-notes-actions">
              <button type="button" onClick={() => setNotesDrawerOpen(false)}>收起</button>
              <button type="button" disabled={!editable || !selectedSlide || notesSaveState === "saving"} onClick={() => void saveNotesDraft()}>保存讲稿</button>
            </div>
          </aside>
        </div>
      ) : null}

      {slideshowOpen && displaySlides[slideshowIndex] ? (
        <div className="ppa-slideshow-overlay" role="dialog" aria-modal="true" onClick={() => setSlideshowIndex((index) => Math.min(displaySlides.length - 1, index + 1))}>
          <button type="button" className="ppa-slideshow-close" onClick={(event) => { event.stopPropagation(); setSlideshowOpen(false); }}>
            <X size={18} />
          </button>
          <div className="ppa-slideshow-slide" dangerouslySetInnerHTML={{ __html: displaySlides[slideshowIndex].content }} />
          <div className="ppa-slideshow-footer">
            <span>{slideshowIndex + 1} / {displaySlides.length}</span>
            <span>点击或空格下一页，Esc 退出</span>
          </div>
        </div>
      ) : null}

      {speakerOverlay ? createPortal(speakerOverlay, document.body) : null}
    </main>
  );
}

function notesSaveStateLabel(state: NotesSaveState) {
  if (state === "dirty") return "有未保存修改";
  if (state === "saving") return "保存中";
  if (state === "saved") return "已保存";
  if (state === "pendingSync") return "待后台同步";
  if (state === "local") return "本机保护中";
  if (state === "error") return "保存失败";
  return "已同步";
}

function cleanSvgForInline(svg: string) {
  return (svg || "")
    .replace(/^\s*<\?xml[^>]*>\s*/i, "")
    .replace(/^\s*<!DOCTYPE[^>]*>\s*/i, "")
    .trim();
}

function resolvePreviewSlideNotes(slide?: PreviewSlide | null) {
  const notes = typeof slide?.notes === "string" ? slide.notes : "";
  if (notes.trim()) return notes;
  const documentNotes = typeof slide?.document?.speakerNotes === "string" ? slide.document.speakerNotes : "";
  return documentNotes;
}

function hashPreviewValue(value: unknown) {
  const text = String(value || "");
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0;
  }
  return `${text.length}:${hash}`;
}

function formatSpeakerElapsed(ms: number) {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remain).padStart(2, "0")}`;
}
