export function createRequestLifecycle() {
  let generation = 0
  let active = false
  const controllers = new Map()

  const abortRequests = () => {
    for (const controller of controllers.values()) controller.abort()
    controllers.clear()
  }

  return {
    activate() {
      abortRequests()
      generation += 1
      active = true
      return generation
    },
    invalidate() {
      generation += 1
      active = false
      abortRequests()
    },
    open(key = 'default') {
      controllers.get(key)?.abort()

      const controller = new AbortController()
      const requestGeneration = generation
      controllers.set(key, controller)

      return {
        generation: requestGeneration,
        signal: controller.signal,
        isCurrent: () => (
          active
          && generation === requestGeneration
          && !controller.signal.aborted
          && controllers.get(key) === controller
        ),
        release: () => {
          if (controllers.get(key) === controller) controllers.delete(key)
        },
      }
    },
    isActive: () => active,
    isCurrent: requestGeneration => active && generation === requestGeneration,
    currentGeneration: () => generation,
  }
}

export function createSerialPoller(task, {
  delay,
  setTimer = setTimeout,
  clearTimer = clearTimeout,
  shouldRun = () => true,
}) {
  let enabled = false
  let inFlight = false
  let timer = null
  let epoch = 0

  const schedule = () => {
    if (!enabled || inFlight || timer !== null || !shouldRun()) return

    const scheduledEpoch = epoch
    timer = setTimer(async () => {
      timer = null
      if (!enabled || epoch !== scheduledEpoch || !shouldRun()) return

      inFlight = true
      try {
        await task()
      } finally {
        inFlight = false
        if (enabled) schedule()
      }
    }, delay)
  }

  return {
    start() {
      if (!enabled) {
        enabled = true
        epoch += 1
      }
      schedule()
    },
    stop() {
      enabled = false
      epoch += 1
      if (timer !== null) clearTimer(timer)
      timer = null
    },
    isRunning: () => enabled,
  }
}
