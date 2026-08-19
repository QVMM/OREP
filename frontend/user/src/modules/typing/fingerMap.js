/**
 * 标准触打指法映射（QWERTY）
 * L4 左小指 … L1 左食指 | R1 右食指 … R4 右小指 | T 拇指（空格）
 */

export const FINGERS = [
  { id: 'L4', hand: 'left', name: '左小指', short: '小', color: '#a78bfa', home: 'KeyA' },
  { id: 'L3', hand: 'left', name: '左无名指', short: '无', color: '#60a5fa', home: 'KeyS' },
  { id: 'L2', hand: 'left', name: '左中指', short: '中', color: '#34d399', home: 'KeyD' },
  { id: 'L1', hand: 'left', name: '左食指', short: '食', color: '#fbbf24', home: 'KeyF' },
  { id: 'R1', hand: 'right', name: '右食指', short: '食', color: '#fb923c', home: 'KeyJ' },
  { id: 'R2', hand: 'right', name: '右中指', short: '中', color: '#f472b6', home: 'KeyK' },
  { id: 'R3', hand: 'right', name: '右无名指', short: '无', color: '#38bdf8', home: 'KeyL' },
  { id: 'R4', hand: 'right', name: '右小指', short: '小', color: '#c084fc', home: 'Semicolon' },
  { id: 'T', hand: 'both', name: '拇指', short: '拇', color: '#94a3b8', home: 'Space' },
]

const FINGER_BY_ID = Object.fromEntries(FINGERS.map((f) => [f.id, f]))

/** key code → finger id */
const CODE_TO_FINGER = {
  // left pinky
  Backquote: 'L4', Digit1: 'L4', KeyQ: 'L4', KeyA: 'L4', KeyZ: 'L4',
  Tab: 'L4', CapsLock: 'L4', ShiftLeft: 'L4', ControlLeft: 'L4',
  // left ring
  Digit2: 'L3', KeyW: 'L3', KeyS: 'L3', KeyX: 'L3',
  // left middle
  Digit3: 'L2', KeyE: 'L2', KeyD: 'L2', KeyC: 'L2',
  // left index
  Digit4: 'L1', Digit5: 'L1',
  KeyR: 'L1', KeyT: 'L1', KeyF: 'L1', KeyG: 'L1', KeyV: 'L1', KeyB: 'L1',
  // right index
  Digit6: 'R1', Digit7: 'R1',
  KeyY: 'R1', KeyU: 'R1', KeyH: 'R1', KeyJ: 'R1', KeyN: 'R1', KeyM: 'R1',
  // right middle
  Digit8: 'R2', KeyI: 'R2', KeyK: 'R2', Comma: 'R2',
  // right ring
  Digit9: 'R3', KeyO: 'R3', KeyL: 'R3', Period: 'R3',
  // right pinky
  Digit0: 'R4', Minus: 'R4', Equal: 'R4',
  KeyP: 'R4', BracketLeft: 'R4', BracketRight: 'R4', Backslash: 'R4',
  Semicolon: 'R4', Quote: 'R4', Slash: 'R4',
  Backspace: 'R4', Enter: 'R4', ShiftRight: 'R4',
  ControlRight: 'R4', AltRight: 'R4', MetaRight: 'R4',
  // thumbs / modifiers
  Space: 'T',
  AltLeft: 'T', MetaLeft: 'T',
}

export function fingerForCode(code) {
  if (!code) return null
  const id = CODE_TO_FINGER[code]
  return id ? FINGER_BY_ID[id] : null
}

export function fingerIdForCode(code) {
  return CODE_TO_FINGER[code] || null
}

export function homeCodeForFinger(fingerId) {
  return FINGER_BY_ID[fingerId]?.home || null
}

/** 供键盘按键染色 */
export function fingerColorForCode(code) {
  const f = fingerForCode(code)
  return f?.color || null
}
