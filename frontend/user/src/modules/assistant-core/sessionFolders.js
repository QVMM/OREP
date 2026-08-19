export function groupSessionsByFolder(folders, sessions) {
  const list = Array.isArray(folders) ? folders : []
  const items = Array.isArray(sessions) ? sessions : []
  const byId = new Map(list.map((f) => [String(f.id), { folder: f, sessions: [] }]))
  const unfiled = []
  for (const s of items) {
    const key = s?.folderId == null ? '' : String(s.folderId)
    if (key && byId.has(key)) byId.get(key).sessions.push(s)
    else unfiled.push(s)
  }
  return {
    groups: list.map((f) => byId.get(String(f.id))).filter(Boolean),
    unfiled,
  }
}
