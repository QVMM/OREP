export function createScriptSaveCoordinator({ snapshot, persist, onState = () => {} }) {
  let dirtyRevision = 0
  let committedRevision = 0
  let runner = null

  function markDirty() {
    dirtyRevision += 1
    return dirtyRevision
  }

  function markCommitted() {
    committedRevision = dirtyRevision
  }

  function isDirty() {
    return dirtyRevision > committedRevision
  }

  async function runSerialSaves() {
    try {
      while (isDirty()) {
        const targetRevision = dirtyRevision
        const payload = snapshot()
        onState('saving')
        await persist(payload, targetRevision)
        committedRevision = targetRevision
      }
      onState('saved')
      return { revision: committedRevision }
    } catch (error) {
      onState('error')
      throw error
    }
  }

  function flush() {
    if (!runner) {
      runner = runSerialSaves().finally(() => {
        runner = null
      })
    }
    return runner
  }

  return {
    flush,
    isDirty,
    markCommitted,
    markDirty,
    get dirtyRevision() {
      return dirtyRevision
    },
    get committedRevision() {
      return committedRevision
    },
  }
}

export async function runAfterSuccessfulSave({ flush, action }) {
  await flush()
  return action()
}
