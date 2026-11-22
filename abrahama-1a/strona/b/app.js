(() => {
  const tour = window.TOUR
  const $ = (selector, root = document) => root.querySelector(selector)
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]

  /* a version can borrow clips and pictures from another one: tour.base is where, tour.own is what it has itself */
  const OWN = new Set(tour.own || [])
  const url = src => (tour.base && !OWN.has(src) ? tour.base : 'assets/') + src
  const SCENES = tour.scenes
  const LEVELS = tour.levels
  const HOMES = tour.homes
  const LEVEL_IDS = LEVELS.map(level => level.id)
  const NODES = ['aerial', ...LEVEL_IDS, ...SCENES.map(scene => scene.id)]
  const EDGES = [
    ...LEVEL_IDS.map(id => ['aerial', id, 5]),
    ...LEVEL_IDS.slice(1).map((id, i) => [LEVEL_IDS[i], id, 3]),
    ...SCENES.map(scene => ['aerial', scene.id, 6]),
  ]
  const STOPS = tour.times
  const STOP_TIMES = STOPS.map(stop => stop.t)

  const els = {
    body: document.body,
    plate: $('#plate'),
    stack: $('#media'),
    timelapse: $('#timelapse'),
    shapes: $('#shapes'),
    pins: $('#pins'),
    panel: $('#panel'),
    floorList: $('#floor-list'),
    slider: $('#day-slider'),
    dayStops: $('#day-stops'),
    playDay: $('#play-day'),
    motion: $('#motion-toggle'),
    skip: $('#skip'),
    tooltip: $('#tooltip'),
    status: $('#status'),
    bookDialog: $('#book-dialog'),
    bookForm: $('#book-form'),
    bookDone: $('#book-done'),
    aboutDialog: $('#about-dialog'),
    planDialog: $('#plan-dialog'),
  }

  const state = {
    node: 'aerial',
    home: null,
    level: LEVEL_IDS[0],
    pick: null,
    time: tour.times[0].id,
    calm: false,
    busy: false,
  }

  const homeOf = num => HOMES.find(home => home.num === num)
  const levelOf = id => LEVELS.find(level => level.id === id)
  const isLevel = node => LEVEL_IDS.includes(node)
  const modeOf = () => (state.home ? 'interior' : isLevel(state.node) ? 'plan' : state.node)
  const area = value => value.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const areaLine = value => `${area(value)} m²`
  const points = poly => poly.map(point => point.join(',')).join(' ')
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value))
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

  /* Route between scenes: every edge is one clip that exists on disk */

  const route = (from, to) => {
    const dist = { [from]: 0 }
    const prev = {}
    const open = new Set(NODES)
    while (open.size) {
      const at = [...open].filter(node => node in dist).sort((a, b) => dist[a] - dist[b])[0]
      if (!at || at === to) break
      open.delete(at)
      EDGES.forEach(([a, b, cost]) => {
        const next = a === at ? b : b === at ? a : null
        if (!next || !open.has(next)) return
        if (next in dist && dist[next] <= dist[at] + cost) return
        dist[next] = dist[at] + cost
        prev[next] = at
      })
    }
    const path = [to]
    while (path[0] !== from) path.unshift(prev[path[0]])
    return path
  }

  /* Media stack: the newest picture or clip fades in over the one before */

  let showId = 0
  let settleId = 0
  let skipClip = null
  let skipAll = false

  const setLoading = isLoading => els.body.classList.toggle('is-loading', isLoading)

  const dispose = el => {
    if (el.tagName === 'VIDEO') {
      el.pause()
      el.removeAttribute('src')
      el.load()
    }
    el.remove()
  }

  const reveal = (el, fade) => {
    const older = [...els.stack.children]
    older.splice(older.indexOf(el))
    el.style.transitionDuration = `${fade}ms`
    void el.offsetWidth
    el.classList.add('is-on')
    setTimeout(() => older.forEach(dispose), fade + 80)
  }

  const showImage = (src, fade = 500) => new Promise(resolve => {
    const id = ++showId
    const img = new Image()
    img.className = 'media'
    img.alt = ''
    img.onload = () => {
      if (id !== showId) return resolve(false)
      els.stack.append(img)
      reveal(img, fade)
      resolve(true)
    }
    img.onerror = () => resolve(false)
    img.src = url(src)
  })

  const prepared = new Map()

  const release = video => {
    video.removeAttribute('src')
    video.load()
  }

  const prepare = src => {
    if (state.calm || prepared.has(src)) return
    const video = document.createElement('video')
    video.muted = true
    video.preload = 'auto'
    video.src = url(src)
    video.load()
    prepared.set(src, video)
    if (prepared.size <= 6) return
    const oldest = prepared.keys().next().value
    release(prepared.get(oldest))
    prepared.delete(oldest)
  }

  const showVideo = (src, { loop = false, fade = 400, rate = 1 } = {}) => new Promise(resolve => {
    const id = ++showId
    const video = prepared.get(src) || document.createElement('video')
    const isPrepared = prepared.delete(src)
    let isSettled = false
    let capTimer = 0
    let resumesLeft = 4
    const finish = ok => {
      if (isSettled) return
      isSettled = true
      clearTimeout(slowTimer)
      clearTimeout(failTimer)
      clearTimeout(capTimer)
      setLoading(false)
      if (!loop) skipClip = null
      if (!ok && !video.classList.contains('is-on')) dispose(video)
      resolve(ok)
    }
    const slowTimer = setTimeout(() => setLoading(true), 500)
    const failTimer = setTimeout(() => finish(false), 9000)
    video.className = 'media'
    video.muted = true
    video.playsInline = true
    video.loop = loop
    video.preload = 'auto'
    video.tabIndex = -1
    video.setAttribute('aria-hidden', 'true')
    video.addEventListener('playing', () => {
      clearTimeout(slowTimer)
      clearTimeout(failTimer)
      setLoading(false)
      if (id !== showId) return finish(false)
      reveal(video, fade)
      if (loop) return finish(true)
      const length = Number.isFinite(video.duration) ? video.duration : 8
      capTimer = setTimeout(() => finish(true), (length / rate + 2.5) * 1000)
    }, { once: true })
    video.addEventListener('pause', () => {
      if (video.ended || !video.isConnected || document.hidden || resumesLeft-- <= 0) return
      video.play().catch(() => {})
    })
    video.addEventListener('ended', () => finish(true), { once: true })
    video.addEventListener('error', () => finish(false), { once: true })
    if (!isPrepared) video.src = url(src)
    video.defaultPlaybackRate = rate
    video.playbackRate = rate
    els.stack.append(video)
    if (!loop) skipClip = () => finish(true)
    video.play().catch(() => finish(false))
  })

  const sceneOf = () => {
    if (state.home) {
      return {
        still: `img/lokal-${state.home}.jpg`,
        loop: `video/loop-lokal-${state.home}.mp4`,
        alt: `Wizualizacja lokalu ${homeOf(state.home).label} z modelu budynku`,
      }
    }
    if (state.node === 'aerial') {
      return {
        still: `img/aerial-${state.time}.jpg`,
        loop: `video/loop-${state.time}.mp4`,
        alt: `Biurowiec Abrahama 1A z lotu ptaka, ${state.time === 'day' ? 'w dzień' : 'o zmierzchu'}`,
      }
    }
    if (isLevel(state.node)) {
      return {
        still: `img/cut-${state.node}.jpg`,
        loop: `video/loop-cut-${state.node}.mp4`,
        alt: `Przekrój budynku na poziomie: ${levelOf(state.node).label}`,
      }
    }
    const scene = SCENES.find(item => item.id === state.node)
    return { still: `img/${scene.id}.jpg`, loop: `video/loop-${scene.id}.mp4`, alt: scene.alt }
  }

  const settle = async (fade = 450) => {
    const mine = ++settleId
    const { still, loop, alt } = sceneOf()
    els.stack.setAttribute('aria-label', alt)
    const isPlaying = !state.calm && await showVideo(loop, { loop: true, fade })
    if (!isPlaying && mine === settleId) await showImage(still, fade)
  }

  /* Rendering */

  const arrow = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'

  const foot = back => `
    <div class="panel-foot">
      ${back ? `<button class="link-btn" type="button" data-go="${back.go}" data-key="back">← ${back.label}</button>` : ''}
      <button class="link-btn" type="button" data-about data-key="about">O wizualizacjach</button>
    </div>`

  const aerialPanel = () => `
    <div class="title">
      <p class="eyebrow">${tour.intro.eyebrow}</p>
      <h1 tabindex="-1">Abrahama <em>1A</em></h1>
    </div>
    <p class="lede">${tour.intro.lede}</p>
    <dl class="stats">
      <div><dt>Lokale</dt><dd>${tour.stats.units}</dd></div>
      <div><dt>Powierzchnie</dt><dd>${Math.round(tour.stats.smallest)}–${Math.round(tour.stats.largest)} <small>m²</small></dd></div>
      <div><dt>Kondygnacje</dt><dd>${tour.stats.floors}</dd></div>
    </dl>
    <div class="actions">
      <button class="btn btn-primary" type="button" data-go="homes">Zobacz lokale</button>
      ${SCENES.map(scene => `<button class="btn" type="button" data-go="${scene.id}">${scene.button}</button>`).join('')}
    </div>
    ${foot()}`

  const homeCard = home => `
    <div class="home-card">
      <img src="${url(`img/lokal-${home.num}-t.jpg`)}" alt="Wizualizacja lokalu ${home.label}" width="480" height="270">
      <div>
        <h2>Lokal ${home.label}</h2>
        <p>${home.type}</p>
        <p>${areaLine(home.area)}</p>
      </div>
    </div>
    <div class="actions">
      <button class="btn btn-primary" type="button" data-enter="${home.num}" data-key="enter">Wejdź do lokalu</button>
      <button class="btn" type="button" data-book data-key="book">Umów prezentację</button>
    </div>`

  const planPanel = () => {
    const level = levelOf(state.node)
    const home = homeOf(state.pick || level.homes[0])
    return `
      <div class="segmented" role="group" aria-label="Piętro">
        ${LEVELS.map(item => `<button type="button" data-go="${item.id}" data-key="seg-${item.id}" aria-pressed="${item.id === level.id}" aria-label="${item.label}">${item.short}</button>`).join('')}
      </div>
      <div class="title">
        <p class="eyebrow">Przekrój piętra</p>
        <h1 tabindex="-1">${level.label}</h1>
      </div>
      <p class="lede">Na tym piętrze: lokal ${home.label}, ${areaLine(home.area)}. Kliknij zaznaczony lokal na przekroju, żeby do niego wejść.</p>
      ${homeCard(home)}
      ${foot({ go: 'aerial', label: 'Budynek' })}`
  }

  const interiorPanel = () => {
    const home = homeOf(state.home)
    const level = levelOf(home.level)
    const index = HOMES.indexOf(home)
    const before = HOMES[(index + HOMES.length - 1) % HOMES.length]
    const after = HOMES[(index + 1) % HOMES.length]
    return `
      <div class="title">
        <p class="eyebrow">${level.label} · ${home.type}</p>
        <h1 tabindex="-1">Lokal ${home.label}</h1>
      </div>
      <p class="lede">${home.lede}</p>
      <ul class="facts">
        <li><b>Powierzchnia</b><span>${areaLine(home.area)}</span></li>
        <li><b>Kondygnacja</b><span>${level.label}</span></li>
        <li><b>Parking</b><span>naziemny i garaż podziemny</span></li>
      </ul>
      <p class="note">Układ ścian pochodzi z modelu budynku. Meble, wykończenie i ludzie są poglądowe.</p>
      <div class="actions">
        <button class="btn btn-primary" type="button" data-book data-key="book">Umów prezentację</button>
        <button class="btn" type="button" data-plan="${home.num}" data-key="plan">Rzut lokalu</button>
        <button class="btn" type="button" data-go="${home.level}" data-key="back-plan">Piętro</button>
      </div>
      <div class="pager">
        <button type="button" data-enter="${before.num}" data-key="pager-prev" aria-label="Poprzedni lokal, ${before.label}">← <span>Poprzedni <b>${before.label}</b></span></button>
        <button type="button" data-enter="${after.num}" data-key="pager-next" aria-label="Następny lokal, ${after.label}"><span>Następny <b>${after.label}</b></span> →</button>
      </div>
      ${foot()}`
  }

  const scenePanel = scene => `
    <div class="title">
      <p class="eyebrow">${scene.eyebrow}</p>
      <h1 tabindex="-1">${scene.title}</h1>
    </div>
    <p class="lede">${scene.lede}</p>
    ${scene.facts ? `<ul class="facts">${scene.facts.map(fact => `<li><b>${fact[0]}</b><span>${fact[1]}</span></li>`).join('')}</ul>` : ''}
    <div class="actions">
      <button class="btn btn-primary" type="button" data-go="homes">Zobacz lokale</button>
      <button class="btn" type="button" data-book>Umów prezentację</button>
    </div>
    ${foot({ go: 'aerial', label: 'Budynek' })}`

  const PANELS = { aerial: aerialPanel, plan: planPanel, interior: interiorPanel }
  SCENES.forEach(scene => {
    PANELS[scene.id] = () => scenePanel(scene)
  })

  const renderShapes = mode => {
    if (mode === 'aerial') {
      els.shapes.innerHTML = LEVELS.map((level, i) => `
        <g class="floor-shape" data-level="${level.id}" style="--i:${i}">
          ${level.polys.map(poly => `<polygon class="shape" points="${points(poly)}"/>`).join('')}
        </g>`).join('')
      return
    }
    if (mode === 'plan') {
      els.shapes.innerHTML = HOMES.filter(home => home.level === state.node).map(home => `
        <polygon class="shape home-shape is-picked" data-enter="${home.num}" data-home="${home.num}" points="${points(home.poly)}"/>`).join('')
      return
    }
    els.shapes.innerHTML = ''
  }

  const renderPins = mode => {
    if (mode === 'aerial') {
      els.pins.innerHTML = LEVELS.map((level, i) => {
        const poly = level.polys[0]
        const y = (poly[0][1] + poly[2][1]) / 2
        return `<button class="pin floor-pin" type="button" style="left:${poly[0][0] - 5}%;top:${y}%;--i:${i}" data-level="${level.id}" data-key="fpin-${level.id}"
          aria-label="${level.label}, lokal ${homeOf(level.homes[0]).label}"><span>${level.short} · ${homeOf(level.homes[0]).label}</span></button>`
      }).join('')
      return
    }
    if (mode === 'plan') {
      els.pins.innerHTML = HOMES.filter(home => home.level === state.node).map((home, i) => `
        <button class="pin" type="button" style="left:${home.pin[0]}%;top:${home.pin[1]}%;--i:${i}" data-enter="${home.num}" data-home="${home.num}" data-key="pin-${home.num}"
          aria-pressed="true" aria-label="Wejdź do lokalu ${home.label}, ${areaLine(home.area)}"><span>${home.label}</span></button>`).join('')
      return
    }
    els.pins.innerHTML = ''
  }

  const hashOf = () => (state.home ? `#lokal-${state.home}` : state.node === 'aerial' ? '' : `#${state.node}`)

  let enterTimer

  const render = ({ isEntering = false } = {}) => {
    const mode = modeOf()
    const focusKey = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.key : null
    els.body.dataset.mode = mode
    els.panel.innerHTML = PANELS[mode]()
    renderShapes(mode)
    renderPins(mode)
    const navKey = mode === 'plan' || mode === 'interior' ? 'homes' : mode
    $$('[data-nav]').forEach(button => {
      if (button.dataset.nav === navKey) button.setAttribute('aria-current', 'page')
      else button.removeAttribute('aria-current')
    })
    if (isEntering) {
      els.body.classList.add('is-enter')
      clearTimeout(enterTimer)
      enterTimer = setTimeout(() => els.body.classList.remove('is-enter'), 1600)
    }
    if (!isEntering && focusKey) {
      const target = $(`[data-key="${focusKey}"]`)
      if (target) target.focus({ preventScroll: true })
    }
    try {
      history.replaceState(null, '', hashOf() || location.pathname + location.search)
    } catch (err) {
      /* file:// pages may refuse history changes; the tour works without them */
    }
  }

  const announce = () => {
    const mode = modeOf()
    const scene = SCENES.find(item => item.id === mode)
    els.status.textContent = scene ? scene.title
      : mode === 'plan' ? `${levelOf(state.node).label}, przekrój piętra`
        : mode === 'interior' ? `Lokal ${homeOf(state.home).label}` : 'Widok budynku Abrahama 1A'
  }

  /* Moving between scenes */

  const setBusy = isBusy => {
    state.busy = isBusy
    els.body.toggleAttribute('data-busy', isBusy)
  }

  const goTo = async dest => {
    if (state.busy) return
    const target = { node: dest.home ? homeOf(dest.home).level : dest.node, home: dest.home || null }
    if (target.node === state.node && target.home === state.home) return
    hideTooltip()
    /* every clip that leaves the aerial view starts from the daytime picture */
    if (state.node === 'aerial' && !state.home && state.time !== STOPS[0].id) {
      setBusy(true)
      await jumpToStop(0)
      setBusy(false)
    }
    stopDay()
    const wasInside = Boolean(state.home)

    if (wasInside && target.home) {
      Object.assign(state, { node: target.node, level: target.node, home: target.home, pick: target.home })
      render()
      announce()
      settle(600)
      return
    }

    const clips = []
    const path = route(state.node, target.node)
    if (wasInside) clips.push({ src: `video/out-${state.home}.mp4`, rate: 1 })
    path.slice(1).forEach((to, i) => clips.push({ src: `video/${path[i]}-to-${to}.mp4`, rate: path.length > 2 ? 1.4 : 1 }))
    if (target.home) clips.push({ src: `video/in-${target.home}.mp4`, rate: 1 })

    setBusy(true)
    skipAll = false
    clips.forEach(clip => prepare(clip.src))
    if (!state.calm) {
      for (const clip of clips) {
        if (skipAll) break
        const isPlayed = await showVideo(clip.src, { fade: 250, rate: clip.rate })
        if (!isPlayed) break
      }
    }

    Object.assign(state, { node: target.node, home: target.home, pick: target.home })
    if (isLevel(target.node)) {
      state.level = target.node
      state.pick = target.home || levelOf(target.node).homes[0]
    }
    prepared.forEach(release)
    prepared.clear()
    render({ isEntering: true })
    await settle()
    setBusy(false)
    announce()
    const heading = $('h1', els.panel)
    if (heading) heading.focus({ preventScroll: true })
    if (isLevel(state.node) && !state.home) prepare(`video/in-${state.pick}.mp4`)
  }

  /* Time of day: stops are evenly spaced on the slider, the time-lapse clip is not */

  const day = { t: STOP_TIMES[STOPS.findIndex(stop => stop.id === 'day')], run: 0, raf: 0, isPlaying: false, isDragging: false }
  let timelapseLoad = null
  let wantedTime = null

  const posToTime = pos => {
    const i = clamp(Math.floor(pos), 0, STOP_TIMES.length - 2)
    return STOP_TIMES[i] + (STOP_TIMES[i + 1] - STOP_TIMES[i]) * (pos - i)
  }

  const timeToPos = t => {
    let i = STOP_TIMES.length - 2
    while (i > 0 && t < STOP_TIMES[i]) i--
    return i + (t - STOP_TIMES[i]) / (STOP_TIMES[i + 1] - STOP_TIMES[i])
  }

  const nearestStop = () => clamp(Math.round(timeToPos(day.t)), 0, STOPS.length - 1)

  const paintDay = () => {
    if (STOPS.length < 2) return
    const near = nearestStop()
    if (!day.isDragging) els.slider.value = timeToPos(day.t)
    els.slider.setAttribute('aria-valuetext', STOPS[near].label)
    $$('[data-time]', els.dayStops).forEach((button, i) => button.setAttribute('aria-pressed', String(i === near)))
  }

  const setDayPlaying = isPlaying => {
    day.isPlaying = isPlaying
    els.playDay.setAttribute('aria-pressed', String(isPlaying))
    $('span', els.playDay).textContent = isPlaying ? 'Stop' : 'Do zmierzchu'
  }

  const timelapseSource = async () => {
    const url = url('video/day-to-dusk-scrub.mp4')
    if (location.protocol === 'file:') return url
    try {
      const response = await fetch(url)
      return response.ok ? URL.createObjectURL(await response.blob()) : url
    } catch (err) {
      return url
    }
  }

  const loadTimelapse = () => {
    if (timelapseLoad) return timelapseLoad
    timelapseLoad = timelapseSource().then(source => new Promise(resolve => {
      els.timelapse.addEventListener('loadeddata', () => resolve(true), { once: true })
      els.timelapse.addEventListener('error', () => resolve(false), { once: true })
      els.timelapse.src = source
      els.timelapse.load()
    }))
    return timelapseLoad
  }

  const seekTimelapse = t => {
    wantedTime = clamp(t, 0, tour.timelapseLength - .05)
    if (!els.timelapse.seeking) els.timelapse.currentTime = wantedTime
  }

  els.timelapse.addEventListener('seeked', () => {
    if (wantedTime !== null && Math.abs(els.timelapse.currentTime - wantedTime) > .03) els.timelapse.currentTime = wantedTime
  })

  const scrubTo = async (t, run) => {
    day.t = t
    paintDay()
    if (state.calm) return
    if (!(await loadTimelapse()) || run !== day.run) return
    seekTimelapse(day.t)
    if (els.timelapse.classList.contains('is-on')) return
    await Promise.race([new Promise(resolve => els.timelapse.addEventListener('seeked', resolve, { once: true })), wait(400)])
    if (run === day.run) els.timelapse.classList.add('is-on')
  }

  const glide = (to, ms, run) => new Promise(resolve => {
    const from = day.t
    const startedAt = performance.now()
    const step = now => {
      if (run !== day.run) return resolve()
      const progress = clamp((now - startedAt) / ms, 0, 1)
      scrubTo(from + (to - from) * progress, run)
      if (progress < 1) day.raf = requestAnimationFrame(step)
      else resolve()
    }
    day.raf = requestAnimationFrame(step)
  })

  const commitDay = async (index, run) => {
    day.t = STOP_TIMES[index]
    state.time = STOPS[index].id
    paintDay()
    await settle(els.timelapse.classList.contains('is-on') ? 0 : 600)
    if (run !== day.run) return
    await wait(120)
    if (run === day.run) els.timelapse.classList.remove('is-on')
  }

  const jumpToStop = async index => {
    const run = ++day.run
    cancelAnimationFrame(day.raf)
    setDayPlaying(false)
    const distance = Math.abs(STOP_TIMES[index] - day.t)
    if (distance < .02 && state.time === STOPS[index].id && !els.timelapse.classList.contains('is-on')) return
    if (!state.calm && distance >= .02) {
      await glide(STOP_TIMES[index], clamp(distance * 420, 500, 2400), run)
      if (run !== day.run) return
    }
    await commitDay(index, run)
  }

  const playDay = async () => {
    if (day.isPlaying) return jumpToStop(nearestStop())
    const run = ++day.run
    const last = STOPS.length - 1
    cancelAnimationFrame(day.raf)
    setDayPlaying(true)
    if (state.calm) {
      for (let i = 0; i <= last; i++) {
        await commitDay(i, run)
        if (run !== day.run) return
        if (i < last) await wait(1500)
        if (run !== day.run) return
      }
      return setDayPlaying(false)
    }
    await glide(STOP_TIMES[0], 600, run)
    if (run !== day.run) return
    await wait(350)
    if (run !== day.run) return
    await glide(STOP_TIMES[last], 5200, run)
    if (run !== day.run) return
    setDayPlaying(false)
    await commitDay(last, run)
  }

  const stopDay = () => {
    if (STOPS.length < 2) return
    ++day.run
    cancelAnimationFrame(day.raf)
    day.isDragging = false
    const near = nearestStop()
    day.t = STOP_TIMES[near]
    state.time = STOPS[near].id
    setDayPlaying(false)
    paintDay()
    els.timelapse.classList.remove('is-on')
  }

  els.slider.addEventListener('input', () => {
    if (!day.isDragging) {
      day.isDragging = true
      ++day.run
      cancelAnimationFrame(day.raf)
      setDayPlaying(false)
    }
    scrubTo(posToTime(Number(els.slider.value)), day.run)
  })

  els.slider.addEventListener('change', () => {
    day.isDragging = false
    jumpToStop(nearestStop())
  })

  els.playDay.addEventListener('click', playDay)

  /* Hover links the plan, the pins and the lists */

  const setHot = (attr, value) => {
    $$('.is-hot').forEach(el => el.classList.remove('is-hot'))
    if (value) $$(`[data-${attr}="${value}"]`).forEach(el => el.classList.add('is-hot'))
  }

  const hideTooltip = () => els.tooltip.classList.remove('is-on')

  const tooltipFor = el => {
    const home = el.dataset.home && homeOf(el.dataset.home)
    if (home) return `<b>Lokal ${home.label}</b><span>${home.type} · ${areaLine(home.area)}</span>`
    const level = levelOf(el.dataset.level)
    return `<b>${level.label}</b><span>${level.homes.map(num => `lokal ${homeOf(num).label} · ${areaLine(homeOf(num).area)}`).join(', ')}</span>`
  }

  const hotTarget = node => (node instanceof Element ? node.closest('[data-home], [data-level]') : null)

  const handleHover = event => {
    const el = hotTarget(event.target)
    if (!el) return
    setHot(el.dataset.home ? 'home' : 'level', el.dataset.home || el.dataset.level)
    if (el.dataset.level && state.node === 'aerial' && !state.busy) prepare(`video/aerial-to-${el.dataset.level}.mp4`)
    if (event.pointerType !== 'mouse' || !el.closest('#plate')) return
    els.tooltip.innerHTML = tooltipFor(el)
    els.tooltip.classList.add('is-on')
  }

  const handleLeave = event => {
    if (!hotTarget(event.target) || hotTarget(event.relatedTarget)) return
    setHot('home', null)
    hideTooltip()
  }

  const handleMove = event => {
    if (!els.tooltip.classList.contains('is-on')) return
    const x = clamp(event.clientX, 90, window.innerWidth - 90)
    els.tooltip.style.transform = `translate(${x}px, ${event.clientY - 14}px) translate(-50%, -100%)`
  }

  document.addEventListener('pointerover', handleHover)
  document.addEventListener('pointerout', handleLeave)
  document.addEventListener('pointermove', handleMove)
  document.addEventListener('focusin', event => {
    const el = hotTarget(event.target)
    if (el) setHot(el.dataset.home ? 'home' : 'level', el.dataset.home || el.dataset.level)
  })
  document.addEventListener('focusout', event => {
    if (hotTarget(event.target)) setHot('home', null)
  })

  /* Booking dialog (demo only) */

  const FIELDS = [
    { input: $('#book-name'), error: $('#book-name-error'), isValid: value => value.trim().length > 0 },
    { input: $('#book-email'), error: $('#book-email-error'), isValid: value => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) },
  ]

  const checkField = field => {
    const isValid = field.isValid(field.input.value)
    field.input.setAttribute('aria-invalid', String(!isValid))
    field.error.hidden = isValid
    return isValid
  }

  const openBook = () => {
    els.bookForm.reset()
    FIELDS.forEach(field => {
      field.input.removeAttribute('aria-invalid')
      field.error.hidden = true
    })
    $('#book-home').value = state.home || state.pick || ''
    els.bookForm.hidden = false
    els.bookDone.hidden = true
    els.bookDialog.showModal()
  }

  const handleBookSubmit = event => {
    event.preventDefault()
    const invalid = FIELDS.filter(field => !checkField(field))
    if (invalid.length) return invalid[0].input.focus()
    const name = $('#book-name').value.trim()
    const email = $('#book-email').value.trim()
    const home = $('#book-home').value
    $('#book-done-text').textContent = `Dziękujemy, ${name}. Na działającej stronie zapytanie${home ? ` o lokal ${homeOf(home).label}` : ''} trafiłoby do działu najmu, a potwierdzenie na adres ${email}. Ta wersja demonstracyjna niczego nie wysłała.`
    els.bookForm.hidden = true
    els.bookDone.hidden = false
    $('#book-done-title').focus()
  }

  els.bookForm.addEventListener('submit', handleBookSubmit)
  FIELDS.forEach(field => {
    field.input.addEventListener('input', () => {
      if (field.input.hasAttribute('aria-invalid')) checkField(field)
    })
    field.input.addEventListener('blur', () => {
      if (field.input.value) checkField(field)
    })
  })

  $$('dialog').forEach(dialog => dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close()
  }))

  /* Motion on/off */

  const setCalm = isCalm => {
    state.calm = isCalm
    els.motion.setAttribute('aria-pressed', String(isCalm))
    els.motion.setAttribute('aria-label', isCalm ? 'Włącz ruch' : 'Zatrzymaj ruch')
    els.motion.title = isCalm ? 'Włącz ruch' : 'Zatrzymaj ruch'
    try {
      localStorage.setItem('tour-calm', isCalm ? '1' : '0')
    } catch (err) {
      /* private mode: the choice just lasts for this visit */
    }
  }

  els.motion.addEventListener('click', () => {
    if (state.busy) return
    stopDay()
    setCalm(!state.calm)
    settle()
  })

  /* Clicks and keys */

  const openPlan = num => {
    const home = homeOf(num)
    $('#plan-title').textContent = `Rzut lokalu ${home.label}`
    const img = $('#plan-img')
    img.src = url(`img/rzut-${num}.png`)
    img.alt = `Rzut lokalu ${home.label} z modelu budynku`
    els.planDialog.showModal()
  }

  document.addEventListener('click', event => {
    const el = event.target instanceof Element && event.target.closest('[data-go], [data-enter], [data-plan], [data-book], [data-about], [data-close], [data-time], [data-level]')
    if (!el) return
    const { go, enter, plan, time, level } = el.dataset
    if (go) return goTo({ node: go === 'homes' ? state.level : go })
    if (enter) return goTo({ home: enter })
    if (plan) return openPlan(plan)
    if ('book' in el.dataset) return openBook()
    if ('about' in el.dataset) return els.aboutDialog.showModal()
    if ('close' in el.dataset) return el.closest('dialog').close()
    if (time) return jumpToStop(Number(time))
    if (level) return goTo({ node: level })
  })

  els.skip.addEventListener('click', () => {
    skipAll = true
    if (skipClip) skipClip()
  })

  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || $('dialog[open]')) return
    if (state.busy) return els.skip.click()
    if (state.home) return goTo({ node: state.node })
    if (state.node !== 'aerial') goTo({ node: 'aerial' })
  })

  const parseHash = () => {
    const key = decodeURIComponent(location.hash.slice(1)).toLowerCase()
    if (key.startsWith('lokal-') && homeOf(key.slice(6))) return { home: key.slice(6) }
    return { node: NODES.includes(key) ? key : 'aerial' }
  }

  window.addEventListener('hashchange', () => goTo(parseHash()))

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return
    $$('video', els.stack).forEach(video => {
      if (video.paused && !video.ended) video.play().catch(() => {})
    })
    if (!state.busy && !state.calm && !$('video', els.stack)) settle()
  })

  /* Start */

  const init = () => {
    els.floorList.innerHTML = LEVELS.map(level => {
      const home = homeOf(level.homes[0])
      return `
      <li>
        <button type="button" data-go="${level.id}" data-level="${level.id}">
          <span class="floor-num" aria-hidden="true">${level.short}</span>
          <span class="floor-text">${level.label}<small>lokal ${home.label} · ${areaLine(home.area)}</small></span>
          ${arrow}
        </button>
      </li>`
    }).reverse().join('')
    $('.nav').innerHTML = [['aerial', 'Budynek'], ['homes', 'Lokale'], ...SCENES.map(scene => [scene.id, scene.nav])]
      .map(([id, label]) => `<button type="button" data-go="${id}" data-nav="${id}">${label}</button>`).join('')
    $('.daylight').hidden = STOPS.length < 2
    els.dayStops.innerHTML = STOPS.map((stop, i) => `<button type="button" data-time="${i}" aria-pressed="false">${stop.label}</button>`).join('')
    $('#book-home').innerHTML = '<option value="">Jeszcze nie wiem</option>' + HOMES.map(home => `<option value="${home.num}">Lokal ${home.label} · ${areaLine(home.area)}</option>`).join('')

    let isCalm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    try {
      const saved = localStorage.getItem('tour-calm')
      if (saved) isCalm = saved === '1'
    } catch (err) {
      /* keep the system preference */
    }
    setCalm(isCalm)

    const start = parseHash()
    if (start.home) {
      const level = homeOf(start.home).level
      Object.assign(state, { node: level, level, home: start.home, pick: start.home })
    } else if (start.node !== 'aerial') {
      state.node = start.node
      if (isLevel(start.node)) Object.assign(state, { level: start.node, pick: levelOf(start.node).homes[0] })
    }

    paintDay()
    render({ isEntering: true })
    settle()
    if (modeOf() !== 'aerial') return
    els.body.classList.add('is-intro')
    setTimeout(() => els.body.classList.remove('is-intro'), 3200)
    if (!state.calm && STOPS.length > 1) setTimeout(loadTimelapse, 2500)
  }

  init()
})()
