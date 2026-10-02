// Clawd Quest: an endless, procedurally generated platformer drawn in plain
// terminal text, so it runs wherever Claude Code does. Mario's running and
// stomping, Pac-Man's tokens, power pellets and ghosts, and Hades' floors with a
// pick of one upgrade after each.
//
// Nothing tops out: upgrades stack without limit and roll rarer the deeper you
// go, while enemies gain health, speed, new kinds and elite forms every few
// floors, with a boss guarding every fifth gate.
//
// This file is the Client surface module (the default export) and the game's
// pure core (the named exports), which the tests drive tick by tick. It runs on
// the drawing thread with no `$`; it hears Claude's work from the hooks module
// through its props and reports the run back with `surface.post`.

export const WORLD_ROWS = 16
export const FLOOR_LENGTH = 220
const TICK_MS = 50
const POLL_MS = 250

const GRAVITY = 0.11
const JUMP = 1.05
const RUN = 0.75
const MAX_FALL = 1.1

const T_AIR = 0
const T_GROUND = 1
const T_BRICK = 2
const T_TOKEN = 3
const T_POWER = 4
const T_LINT = 5

// Claude's orange, and the rest of the palette
const C = {
  clawd: '#D97757',
  eye: '#1A1A1A',
  grass: '#3FB950',
  dirt: '#2D333B',
  dirtDot: '#444C56',
  brick: '#8B949E',
  token: '#E3B341',
  power: '#F0883E',
  lint: '#F85149',
  gate: '#A371F7',
  locked: '#F85149',
  bug: '#F85149',
  hopper: '#DB61A2',
  looper: '#39C5CF',
  turret: '#E0823D',
  boss: '#B62324',
  elite: '#FFD33D',
  ghost: ['#FF7BC5', '#56D4DD', '#FFA657', '#D2A8FF'],
  scared: '#388BFD',
  drone: '#D2A8FF',
  bolt: '#79C0FF',
  shot: '#FF938A',
  shield: '#79C0FF',
  dim: '#768390',
  text: '#ADBAC7',
  good: '#57AB5A',
  bad: '#E5534B',
  hud: '#CDD9E5',
}

// Each a boon offered between floors. None tops out but Bypass Permissions;
// `from` is the first floor (0-based) it is offered on
export const UPGRADES = {
  opus: { name: 'Opus 5.5', text: '+15% run speed' },
  thinking: { name: 'Extended Thinking', text: '+1 jump in mid-air' },
  cache: { name: 'Prompt Caching', text: '+1 life' },
  compact: { name: '/compact', text: 'hits fill 20% less context' },
  million: { name: '1M Context', text: 'context holds more' },
  autoAccept: { name: 'Auto-accept', text: 'tokens fly to you from farther' },
  subagent: { name: 'Subagent', text: '+1 drone that zaps enemies' },
  hooks: { name: 'Hooks', text: 'harder stomps, +50% score' },
  bypass: { name: 'Bypass Permissions', text: 'lint spikes no longer hurt', max: 1 },
  ultrathink: { name: 'Ultrathink', text: 'power pellets last longer' },
  fast: { name: 'Fast Mode', text: 'X dashes; faster recharge' },
  mcp: { name: 'MCP Server', text: 'tokens are worth more' },
  fable: { name: 'Code Bolts', text: 'F fires; faster, harder, wider' },
  worktree: { name: 'Git Worktree', text: '+1 shield each floor' },
}

// Rarer rolls give several levels at once, and come more often deeper in
const RARITIES = [
  { name: 'Legendary', levels: 5, color: '#FFD33D' },
  { name: 'Epic', levels: 3, color: '#D2A8FF' },
  { name: 'Rare', levels: 2, color: '#79C0FF' },
  { name: 'Common', levels: 1, color: '#ADBAC7' },
]

const BOSS_NAMES = ['Legacy Monolith', 'Spaghetti Code', 'The Merge Queue', 'Tech Debt', 'Production Outage', 'The Rewrite']

// What Claude did in the session, as the hooks module names it, and what it does here
export const CLAUDE_EFFECTS = {
  edit: { text: 'Claude edited a file: power pellet ahead', good: true },
  'bash-ok': { text: 'Claude ran a command: context -10%', good: true },
  search: { text: 'Claude searched the code: token shower', good: true },
  agent: { text: 'Claude spawned a subagent: drone for 20s', good: true },
  todo: { text: 'Claude updated its todos: +50', good: true },
  error: { text: 'Claude hit an error: a bug crawls in', good: false },
  web: { text: 'Claude went online: a hallucination follows', good: false },
  done: { text: "Claude's done: +500", good: true },
  ask: { text: 'Claude needs you', good: false },
}

// ---------------------------------------------------------------- randomness

function rngFrom(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const between = (rand, lo, hi) => lo + Math.floor(rand() * (hi - lo + 1))

export const isBossFloor = floor => (floor + 1) % 5 === 0

// ---------------------------------------------------------------- enemies

// Base health and points per kind; both grow with depth
const KINDS = {
  bug: { hp: 1, score: 100, isStompable: true },
  ghost: { hp: 1, score: 200, isStompable: true },
  hopper: { hp: 2, score: 150, isStompable: true },
  looper: { hp: 2, score: 175, isStompable: true },
  turret: { hp: 3, score: 250, isStompable: true },
  boss: { hp: 12, score: 2500, isStompable: true },
}

// How tough an enemy is on this floor: every fourth floor adds a base's worth
// of health, and elites (from floor 6) double it and move faster
function makeEnemy(kind, x, y, floor, rand = Math.random) {
  const base = KINDS[kind]
  const eliteChance = floor >= 5 ? Math.min(0.6, (floor - 4) * 0.05) : 0
  const isElite = kind !== 'boss' && rand() < eliteChance
  let hp = base.hp * (1 + Math.floor(floor / 4)) * (isElite ? 2 : 1)
  if (kind === 'boss') hp = Math.round(8 + floor * 2.5)
  const size = { bug: [2, 1], ghost: [1, 1], hopper: [1, 1], looper: [1, 1], turret: [2, 1], boss: [6, 3] }[kind]
  return {
    kind,
    x,
    y,
    baseY: y,
    vx: -0.18,
    vy: 0,
    w: size[0],
    h: size[1],
    hp,
    maxHp: hp,
    isElite,
    pace: (1 + Math.min(floor, 40) * 0.05) * (isElite ? 1.3 : 1),
    timer: Math.floor(rand() * 40),
    hurtTicks: 0,
  }
}

// ---------------------------------------------------------------- the world

// One floor: a strip FLOOR_LENGTH columns long ending at the merge gate, the
// same every time for the same seed and floor
export function makeFloor(seed, floor) {
  const rand = rngFrom(seed * 7919 + floor * 104729)
  const width = FLOOR_LENGTH + 30
  const tiles = new Uint8Array(width * WORLD_ROWS)
  const set = (x, y, t) => {
    if (x >= 0 && x < width && y >= 0 && y < WORLD_ROWS) tiles[y * width + x] = t
  }
  const groundAt = new Int8Array(width).fill(-1)
  const enemies = []
  const isBoss = isBossFloor(floor)
  // Content past the boss end of the strip stays flat for the fight
  const end = isBoss ? FLOOR_LENGTH - 45 : FLOOR_LENGTH - 4

  let x = 0
  let gy = WORLD_ROWS - 3
  const fill = (from, to, top) => {
    for (let c = from; c < to && c < width; c++) {
      groundAt[c] = top
      for (let r = top; r < WORLD_ROWS; r++) set(c, r, T_GROUND)
    }
  }
  const tokens = (from, to, row) => {
    for (let c = from; c < to; c += 2) if (row >= 0 && tileAt({ tiles, width }, c, row) === T_AIR) set(c, row, T_TOKEN)
  }

  // Which enemies a stretch of ground gets: new kinds join every few floors
  const pickKind = () => {
    const pool = ['bug', 'bug']
    if (floor >= 1) pool.push('hopper')
    if (floor >= 3) pool.push('turret')
    if (floor >= 5) pool.push('looper', 'hopper')
    if (floor >= 8) pool.push('turret', 'looper')
    return pool[Math.floor(rand() * pool.length)]
  }
  const populate = at => {
    const chance = Math.min(0.9, 0.25 + floor * 0.05)
    const count = 1 + Math.min(3, Math.floor(floor / 7))
    for (let i = 0; i < count; i++) {
      if (rand() > chance) continue
      const bx = at - 3 - i * 3
      if (bx < 24 || groundAt[bx] < 0 || groundAt[bx - 1] < 0) continue
      const kind = pickKind()
      const y = kind === 'looper' ? groundAt[bx] - 5 : groundAt[bx] - 1
      enemies.push(makeEnemy(kind, bx, y, floor, rand))
    }
  }

  // Safe start
  fill(0, 14, gy)
  tokens(6, 14, gy - 1)
  x = 14

  while (x < end) {
    const roll = rand()
    const len = between(rand, 6, 14)
    if (roll < 0.22 && x > 20) {
      // A pit, wider deeper in, never wider than a jump
      const gap = between(rand, 3, Math.min(10, 4 + Math.floor(floor / 2)))
      for (let i = 0; i < gap; i += 2) set(x + i, gy - 4, T_TOKEN)
      x += gap
      fill(x, x + 5, gy)
      x += 5
    } else if (roll < 0.4) {
      gy = Math.max(WORLD_ROWS - 7, Math.min(WORLD_ROWS - 2, gy + (rand() < 0.5 ? -2 : 2)))
      fill(x, x + len, gy)
      tokens(x + 1, x + len, gy - 1)
      x += len
    } else if (roll < 0.62) {
      fill(x, x + len, gy)
      const py = gy - between(rand, 4, 5)
      const pl = between(rand, 4, Math.max(4, len - 2))
      const px = x + between(rand, 1, Math.max(1, len - pl))
      for (let c = px; c < px + pl; c++) set(c, py, T_BRICK)
      tokens(px, px + pl, py - 1)
      if (rand() < 0.35) set(px + Math.floor(pl / 2), py - 1, T_POWER)
      x += len
    } else if (roll < 0.74 && floor >= 1) {
      fill(x, x + len, gy)
      const lx = x + between(rand, 2, Math.max(2, len - 4))
      const ll = between(rand, 2, Math.min(5, 2 + Math.floor(floor / 4)))
      for (let c = lx; c < lx + ll; c++) set(c, gy - 1, T_LINT)
      x += len
    } else if (roll < 0.84 && x > 20) {
      const gap = between(rand, 8, 12)
      let stepY = gy - 2
      for (let c = x + 1; c < x + gap - 1; c += 4) {
        for (let i = 0; i < 3; i++) set(c + i, stepY, T_BRICK)
        set(c + 1, stepY - 1, T_TOKEN)
        stepY = Math.max(4, stepY + (rand() < 0.5 ? -1 : 1))
      }
      x += gap
      fill(x, x + 5, gy)
      x += 5
    } else {
      fill(x, x + len, gy)
      tokens(x + 1, x + len, gy - 1)
      x += len
    }
    populate(x)
  }
  // The flat run to the gate: an arena on boss floors
  fill(x, width, gy)
  tokens(x, FLOOR_LENGTH - 2, gy - 1)
  if (isBoss) {
    for (let c = x + 8; c < FLOOR_LENGTH - 6; c += 9) {
      for (let i = 0; i < 4; i++) set(c + i, gy - 4, T_BRICK)
    }
    for (let c = x + 10; c < FLOOR_LENGTH - 6; c += 9) set(c, gy - 5, T_POWER)
    const boss = makeEnemy('boss', FLOOR_LENGTH - 14, gy - 7, floor, rand)
    boss.name = BOSS_NAMES[Math.floor(floor / 5) % BOSS_NAMES.length] + (floor >= 30 ? ' Mk ' + (Math.floor(floor / 30) + 1) : '')
    enemies.push(boss)
  }
  return { tiles, width, groundAt, gateX: FLOOR_LENGTH, enemies, startY: groundAt[2] - 2, arenaX: x }
}

function tileAt(world, x, y) {
  const c = Math.floor(x)
  const r = Math.floor(y)
  if (r < 0 || r >= WORLD_ROWS) return T_AIR
  if (c < 0) return T_GROUND
  if (c >= world.width) return T_GROUND
  return world.tiles[r * world.width + c]
}

function setTile(world, x, y, t) {
  const c = Math.floor(x)
  const r = Math.floor(y)
  if (c >= 0 && c < world.width && r >= 0 && r < WORLD_ROWS) world.tiles[r * world.width + c] = t
}

const isSolid = t => t === T_GROUND || t === T_BRICK

// ---------------------------------------------------------------- a run

export function newRun(seed, resume) {
  const run = {
    seed,
    runId: seed.toString(36) + Date.now().toString(36),
    floor: 0,
    score: 0,
    tokens: 0,
    kills: 0,
    lives: 3,
    context: 0,
    upgrades: {},
    phase: 'title', // title, play, pick, over, paused
    choices: [],
    tick: 0,
    ticker: [],
    drones: [],
    tempDrones: [],
    bullets: [],
  }
  if (resume && !resume.isOver) {
    Object.assign(run, {
      seed: resume.seed,
      runId: resume.runId,
      floor: resume.floor,
      score: resume.score,
      tokens: resume.tokens,
      kills: resume.kills ?? 0,
      lives: resume.lives,
      context: resume.context,
      upgrades: { ...resume.upgrades },
    })
  }
  startFloor(run)
  return run
}

export function startFloor(run) {
  const world = makeFloor(run.seed, run.floor)
  run.world = world
  run.player = {
    x: 2,
    y: world.startY,
    vx: 0,
    vy: 0,
    w: 4,
    h: 2,
    isOnGround: false,
    facing: 1,
    airJumps: 0,
    invulnerable: 30,
    dashCooldown: 0,
    fireCooldown: 0,
    safeX: 2,
  }
  run.enemies = world.enemies
  run.bullets = []
  run.shields = lvl(run, 'worktree')
  run.ghostTimer = run.floor === 0 ? 400 : 160
  run.frightened = 0
  run.cameraX = 0
  run.drones = []
  for (let i = 0; i < Math.min(12, lvl(run, 'subagent')); i++) run.drones.push({ angle: (i * Math.PI * 2) / 3, cooldown: 30 })
  if (isBossFloor(run.floor)) say(run, 'Boss floor: ' + world.enemies[world.enemies.length - 1].name + ' guards the gate', C.locked)
}

const lvl = (run, key) => run.upgrades[key] ?? 0

// The numbers each upgrade turns, none with a ceiling but where physics needs one
const stats = run => ({
  speed: Math.min(2.2, RUN * (1 + 0.15 * lvl(run, 'opus'))),
  reach: Math.min(14, lvl(run, 'autoAccept') * 1.4),
  scoreRate: 1 + 0.5 * lvl(run, 'hooks'),
  stompDamage: 1 + Math.floor(lvl(run, 'hooks') / 2),
  stompBounce: JUMP * Math.min(1.1, 0.65 + 0.15 * lvl(run, 'hooks')),
  tokenValue: 10 * (1 + lvl(run, 'mcp')),
  pelletTicks: Math.round(120 * (1 + 0.5 * lvl(run, 'ultrathink'))),
  dashCooldown: Math.max(6, 30 - 4 * lvl(run, 'fast')),
  fireCooldown: Math.max(2, 14 - 2 * lvl(run, 'fable')),
  boltDamage: 1 + Math.floor(lvl(run, 'fable') / 2),
  boltSpread: lvl(run, 'fable') >= 7 ? 3 : lvl(run, 'fable') >= 4 ? 2 : 1,
  droneCooldown: Math.max(8, 50 - 3 * lvl(run, 'subagent')),
  droneDamage: 1 + Math.floor(lvl(run, 'subagent') / 3),
})

// Hits fill more context deeper in; /compact and 1M Context push back
const contextHit = run => (25 * (1 + run.floor * 0.05) * Math.pow(0.8, lvl(run, 'compact'))) / (1 + lvl(run, 'million'))

function say(run, text, color) {
  run.ticker.push({ text, color, ttl: 70 })
  if (run.ticker.length > 3) run.ticker.shift()
}

function addScore(run, n) {
  run.score += n * stats(run).scoreRate
}

function hurt(run, why) {
  const p = run.player
  if (p.invulnerable > 0) return
  p.invulnerable = 36
  p.vy = -0.6
  if (run.shields > 0) {
    run.shields -= 1
    say(run, 'Worktree shield took it: ' + run.shields + ' left', C.shield)
    return
  }
  run.context += contextHit(run)
  if (run.context >= 100) loseLife(run, 'Context full: auto-compacted')
  else say(run, why + ': context ' + Math.round(run.context) + '%', C.bad)
}

function loseLife(run, why) {
  run.lives -= 1
  run.context = 0
  say(run, why, C.bad)
  if (run.lives <= 0) {
    run.phase = 'over'
    return
  }
  const p = run.player
  p.x = Math.max(1, p.safeX - 2)
  const top = run.world.groundAt[Math.floor(p.x + 1)]
  p.y = (top >= 0 ? top : WORLD_ROWS - 3) - 3
  p.vx = 0
  p.vy = 0
  p.invulnerable = 50
  // Clear the landing, but never of the boss
  run.enemies = run.enemies.filter(e => e.kind === 'boss' || Math.abs(e.x - p.x) > 10)
  run.bullets = []
}

function damage(run, e, n) {
  if (e.isDead) return
  e.hp -= n
  e.hurtTicks = 4
  if (e.hp > 0) return
  e.isDead = true
  run.kills += 1
  addScore(run, KINDS[e.kind].score * (1 + run.floor * 0.1) * (e.isElite ? 2 : 1))
  if (e.kind === 'boss') {
    say(run, e.name + ' defeated: the gate opens', C.elite)
    run.frightened = 0
  }
}

function overlaps(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}

// Moves a body through the tiles, one axis at a time, in steps no longer than
// a cell so a fast body can't pass through a wall
function moveBody(world, b) {
  const steps = Math.max(1, Math.ceil(Math.abs(b.vx) / 0.9))
  const vx = b.vx / steps
  for (let s = 0; s < steps && b.vx !== 0; s++) {
    b.x += vx
    const edge = vx > 0 ? b.x + b.w - 0.001 : b.x
    for (let r = Math.floor(b.y); r <= Math.floor(b.y + b.h - 0.001); r++) {
      if (isSolid(tileAt(world, edge, r))) {
        b.x = vx > 0 ? Math.floor(edge) - b.w : Math.floor(edge) + 1
        b.hitWall = true
        b.vx = 0
        break
      }
    }
  }
  b.y += b.vy
  b.isOnGround = false
  const fromC = Math.floor(b.x)
  const toC = Math.floor(b.x + b.w - 0.001)
  if (b.vy > 0) {
    const edge = b.y + b.h - 0.001
    for (let c = fromC; c <= toC; c++) {
      if (isSolid(tileAt(world, c, edge))) {
        b.y = Math.floor(edge) - b.h
        b.vy = 0
        b.isOnGround = true
        break
      }
    }
  } else if (b.vy < 0) {
    for (let c = fromC; c <= toC; c++) {
      if (isSolid(tileAt(world, c, b.y))) {
        b.y = Math.floor(b.y) + 1
        b.vy = 0
        break
      }
    }
  }
}

// Three boons to pick from, each rolled for rarity; a boss always pays Epic
function pickUpgrades(run) {
  const rand = rngFrom(run.seed + run.floor * 31)
  const f = run.floor
  const open = Object.keys(UPGRADES).filter(k => !UPGRADES[k].max || lvl(run, k) < UPGRADES[k].max)
  const choices = []
  while (choices.length < 3 && open.length) {
    const key = open.splice(Math.floor(rand() * open.length), 1)[0]
    const r = rand()
    const legendary = f >= 9 ? Math.min(0.2, (f - 8) * 0.015) : 0
    const epic = Math.min(0.35, f * 0.02) + (isBossFloor(f) ? 1 : 0)
    const rare = Math.min(0.6, 0.12 + f * 0.03)
    let rarity = r < legendary ? 0 : r < legendary + epic ? 1 : r < legendary + epic + rare ? 2 : 3
    if (UPGRADES[key].max) rarity = 3
    choices.push({ key, rarity })
  }
  return choices
}

// Applies one of Claude's events to the run
export function applyClaude(run, kind) {
  const effect = CLAUDE_EFFECTS[kind]
  if (!effect || run.phase === 'over') return
  const p = run.player
  const ahead = Math.floor(p.x + 14 + Math.random() * 8)
  if (kind === 'edit') {
    for (let r = 1; r < WORLD_ROWS - 1; r++) {
      if (isSolid(tileAt(run.world, ahead, r + 1)) && tileAt(run.world, ahead, r) === T_AIR) {
        setTile(run.world, ahead, r, T_POWER)
        break
      }
    }
  } else if (kind === 'bash-ok') {
    run.context = Math.max(0, run.context - 10)
  } else if (kind === 'search') {
    for (let i = 0; i < 8; i++) {
      const c = ahead - 4 + i
      const r = 3 + ((i * 3) % 4)
      if (tileAt(run.world, c, r) === T_AIR) setTile(run.world, c, r, T_TOKEN)
    }
  } else if (kind === 'agent') {
    run.tempDrones.push({ angle: Math.random() * 6, cooldown: 10, ttl: 400 })
  } else if (kind === 'todo') {
    addScore(run, 50)
  } else if (kind === 'error') {
    const top = run.world.groundAt[ahead]
    if (top >= 0) run.enemies.push(makeEnemy('bug', ahead, top - 1, run.floor))
  } else if (kind === 'web') {
    spawnGhost(run)
  } else if (kind === 'done') {
    addScore(run, 500)
  }
  say(run, effect.text, effect.good ? C.good : C.bad)
}

function spawnGhost(run) {
  const n = run.enemies.filter(e => e.kind === 'ghost').length
  const ghost = makeEnemy('ghost', run.cameraX + 70, 2 + Math.random() * 6, run.floor)
  ghost.color = C.ghost[n % C.ghost.length]
  run.enemies.push(ghost)
}

function fireAt(run, from, speed) {
  const p = run.player
  const dx = p.x + 2 - from.x
  const dy = p.y + 1 - from.y
  const d = Math.hypot(dx, dy * 2) || 1
  run.bullets.push({ x: from.x, y: from.y, vx: (dx / d) * speed, vy: ((dy / d) * speed) / 2, isEnemy: true, ttl: 120 })
}

// One tick of an enemy, by kind
function think(run, e) {
  const world = run.world
  const p = run.player
  const scared = run.frightened > 0 && e.kind !== 'boss'
  e.timer += 1
  if (e.hurtTicks > 0) e.hurtTicks -= 1
  const toward = Math.sign(p.x + 1.5 - e.x) || 1

  if (e.kind === 'bug' || e.kind === 'hopper' || e.kind === 'turret') {
    e.vy = Math.min(MAX_FALL, e.vy + GRAVITY)
    e.hitWall = false
    if (e.kind === 'bug') {
      const speed = Math.min(0.6, 0.18 * e.pace) * (scared ? 0.5 : 1)
      e.vx = Math.sign(e.vx || -1) * speed
      const front = e.vx > 0 ? e.x + e.w : e.x - 0.01
      if (e.isOnGround && !isSolid(tileAt(world, front, e.y + e.h + 0.1))) e.vx = -e.vx
    } else if (e.kind === 'hopper') {
      // A regression: lies low, then leaps at you
      if (e.isOnGround) {
        e.vx = 0
        if (e.timer % Math.max(18, Math.round(45 / e.pace)) === 0 && Math.abs(p.x - e.x) < 30) {
          e.vy = -0.95
          e.vx = toward * Math.min(0.7, 0.35 * e.pace) * (scared ? -1 : 1)
        }
      }
    } else {
      // A merge conflict: plants itself and fires down the line
      e.vx = 0
      const every = Math.max(20, Math.round(90 / e.pace))
      if (!scared && e.timer % every === 0 && Math.abs(p.x - e.x) < 40) {
        fireAt(run, { x: e.x + (toward > 0 ? 2 : -0.5), y: e.y }, Math.min(0.9, 0.45 * e.pace))
      }
    }
    const dir = e.vx
    moveBody(world, e)
    if (e.hitWall) e.vx = -dir
    if (e.y > WORLD_ROWS + 1) e.isDead = true
  } else if (e.kind === 'ghost') {
    const dx = p.x + 1.5 - e.x
    const dy = p.y + 0.5 - e.y
    const d = Math.hypot(dx, dy * 2) || 1
    const speed = Math.min(0.55, 0.16 * e.pace) * (scared ? -0.6 : 1)
    e.x += (dx / d) * speed
    e.y += ((dy / d) * speed) / 2
    if (e.x < run.cameraX - 20) e.isDead = true
  } else if (e.kind === 'looper') {
    // An infinite loop: weaves toward you on a sine
    e.x += toward * Math.min(0.5, 0.12 * e.pace) * (scared ? -1 : 1)
    e.y = e.baseY + Math.sin(e.timer / 8) * 3
  } else if (e.kind === 'boss') {
    // Waits for you at the arena, then sways, fires spreads and calls in help
    if (p.x < world.arenaX - 10) return
    const rage = 1 + (1 - e.hp / e.maxHp)
    e.y = e.baseY + Math.sin(e.timer / 14) * 2.5
    e.x = Math.max(world.arenaX + 6, Math.min(world.gateX - 8, e.x + Math.sin(e.timer / 40) * 0.25))
    const every = Math.max(14, Math.round(60 / (e.pace * rage)))
    if (e.timer % every === 0) {
      const shots = 1 + Math.min(4, Math.floor(run.floor / 10))
      for (let i = 0; i < shots; i++) {
        const from = { x: e.x, y: e.y + 1 }
        fireAt(run, from, Math.min(1, 0.4 * e.pace))
        run.bullets[run.bullets.length - 1].vy += (i - (shots - 1) / 2) * 0.12
      }
    }
    if (e.timer % Math.max(60, Math.round(220 / rage)) === 0) {
      const top = world.groundAt[Math.floor(e.x - 2)]
      if (top >= 0) run.enemies.push(makeEnemy(run.floor >= 10 && e.timer % 2 ? 'hopper' : 'bug', e.x - 2, top - 1, run.floor))
    }
  }
}

// One tick of play. `input` is { left, right, jump, jumpHeld, dash, fire, pick }
export function step(run, input) {
  run.tick += 1
  for (const t of run.ticker) t.ttl -= 1
  run.ticker = run.ticker.filter(t => t.ttl > 0)

  if (run.phase === 'title' || run.phase === 'paused') {
    if (input.jump || input.left || input.right) run.phase = 'play'
    return
  }
  if (run.phase === 'pick') {
    const n = input.pick
    if (n >= 1 && n <= run.choices.length) {
      const { key, rarity } = run.choices[n - 1]
      const levels = RARITIES[rarity].levels
      run.upgrades[key] = lvl(run, key) + levels
      if (key === 'cache') run.lives += levels
      say(run, RARITIES[rarity].name + ' ' + UPGRADES[key].name + ' → ' + roman(lvl(run, key)), RARITIES[rarity].color)
      run.floor += 1
      run.phase = 'play'
      startFloor(run)
    }
    return
  }
  if (run.phase !== 'play') return

  const world = run.world
  const p = run.player
  const s = stats(run)

  // Running
  const want = (input.right ? 1 : 0) - (input.left ? 1 : 0)
  p.vx += (want * s.speed - p.vx) * (p.isOnGround ? 0.45 : 0.25)
  if (Math.abs(p.vx) < 0.02) p.vx = 0
  if (want) p.facing = want
  if (p.dashCooldown > 0) p.dashCooldown -= 1
  if (input.dash && lvl(run, 'fast') && p.dashCooldown === 0) {
    p.vx = p.facing * 3
    p.dashCooldown = s.dashCooldown
    p.invulnerable = Math.max(p.invulnerable, 6)
  }

  // Code bolts
  if (p.fireCooldown > 0) p.fireCooldown -= 1
  if (input.fire && lvl(run, 'fable') && p.fireCooldown === 0) {
    p.fireCooldown = s.fireCooldown
    for (let i = 0; i < s.boltSpread; i++) {
      const vy = (i - (s.boltSpread - 1) / 2) * 0.12
      run.bullets.push({ x: p.x + (p.facing > 0 ? 4 : -1), y: p.y + 0.5, vx: p.facing * 1.6, vy, isEnemy: false, ttl: 40, damage: s.boltDamage })
    }
  }

  // Jumping: a held key floats a little higher
  if (p.isOnGround) p.airJumps = lvl(run, 'thinking')
  if (input.jump) {
    if (p.isOnGround || p.coyote > 0) {
      p.vy = -JUMP
      p.coyote = 0
    } else if (p.airJumps > 0) {
      p.vy = -JUMP * 0.9
      p.airJumps -= 1
    }
  }
  p.vy = Math.min(MAX_FALL, p.vy + (input.jumpHeld && p.vy < 0 ? GRAVITY * 0.6 : GRAVITY))
  const wasOnGround = p.isOnGround
  moveBody(world, p)
  p.coyote = p.isOnGround ? 0 : wasOnGround ? 3 : Math.max(0, (p.coyote ?? 0) - 1)
  if (p.isOnGround && Math.abs(run.world.groundAt[Math.floor(p.x + 2)] - (p.y + p.h)) < 0.5) p.safeX = p.x
  if (p.invulnerable > 0) p.invulnerable -= 1

  if (p.y > WORLD_ROWS + 1) {
    loseLife(run, 'Segfault: fell into the void')
    return
  }

  // Tokens, pellets and lint under the player
  const reach = s.reach
  for (let c = Math.floor(p.x - reach); c <= Math.floor(p.x + p.w - 0.001 + reach); c++) {
    for (let r = Math.floor(p.y - reach / 2); r <= Math.floor(p.y + p.h - 0.001 + reach / 2); r++) {
      const t = tileAt(world, c, r)
      const isTouching = c >= Math.floor(p.x) && c <= Math.floor(p.x + p.w - 0.001) && r >= Math.floor(p.y) && r <= Math.floor(p.y + p.h - 0.001)
      if (t === T_TOKEN) {
        setTile(world, c, r, T_AIR)
        run.tokens += 1
        addScore(run, s.tokenValue)
      } else if (t === T_POWER && isTouching) {
        setTile(world, c, r, T_AIR)
        run.frightened = s.pelletTicks
        addScore(run, 50)
        say(run, 'Power pellet: enemies flee', C.power)
      } else if (t === T_LINT && isTouching && !lvl(run, 'bypass')) {
        hurt(run, 'Lint error')
      }
    }
  }
  if (run.frightened > 0) run.frightened -= 1

  // The merge gate ends the floor, once any boss is down
  const boss = run.enemies.find(e => e.kind === 'boss' && !e.isDead)
  if (boss && p.x + p.w >= world.gateX - 1) {
    p.x = world.gateX - 1 - p.w
    p.vx = Math.min(0, p.vx)
  }
  if (!boss && p.x + p.w >= world.gateX) {
    addScore(run, 250 + run.floor * 100)
    run.choices = pickUpgrades(run)
    if (run.choices.length === 0) {
      run.floor += 1
      startFloor(run)
    } else {
      run.phase = 'pick'
    }
    return
  }

  // Hallucinations drift in, Pac-Man style, more of them deeper in
  run.ghostTimer -= 1
  const ghosts = run.enemies.filter(e => e.kind === 'ghost').length
  if (run.ghostTimer <= 0) {
    run.ghostTimer = Math.max(50, 220 - run.floor * 12)
    if (ghosts < Math.min(10, 1 + Math.floor(run.floor / 2)) && p.x > 20) spawnGhost(run)
  }

  for (const e of run.enemies) {
    think(run, e)
    if (e.isDead || !overlaps(p, e)) continue
    if (run.frightened > 0 && e.kind !== 'boss') {
      damage(run, e, 999)
      say(run, 'Ate ' + (e.kind === 'ghost' ? 'a hallucination' : 'a ' + e.kind), C.power)
    } else if (KINDS[e.kind].isStompable && p.vy > 0 && p.y + p.h <= e.y + 0.9) {
      damage(run, e, s.stompDamage * (run.frightened > 0 ? 3 : 1))
      p.vy = -s.stompBounce
    } else {
      hurt(run, e.kind === 'boss' ? e.name + ' hit you' : e.kind === 'ghost' ? 'A hallucination got you' : 'A ' + e.kind + ' got you')
    }
  }

  // Bolts and enemy fire
  for (const b of run.bullets) {
    b.x += b.vx
    b.y += b.vy
    b.ttl -= 1
    if (isSolid(tileAt(world, b.x, b.y))) b.ttl = 0
    if (b.ttl <= 0) continue
    if (b.isEnemy) {
      if (b.x >= p.x && b.x < p.x + p.w && b.y >= p.y && b.y < p.y + p.h) {
        b.ttl = 0
        hurt(run, 'Merge conflict')
      }
    } else {
      const hit = run.enemies.find(e => !e.isDead && b.x >= e.x - 0.5 && b.x < e.x + e.w + 0.5 && b.y >= e.y - 0.5 && b.y < e.y + e.h + 0.5)
      if (hit) {
        damage(run, hit, b.damage)
        b.ttl = 0
      }
    }
  }
  run.bullets = run.bullets.filter(b => b.ttl > 0)

  // Subagents zap what comes close
  for (const d of [...run.drones, ...run.tempDrones]) {
    d.angle += 0.15
    d.cooldown -= 1
    if (d.ttl !== undefined) d.ttl -= 1
    if (d.cooldown > 0) continue
    const target = run.enemies.find(e => !e.isDead && Math.abs(e.x - p.x) < 16 && Math.abs(e.y - p.y) < 7)
    if (target) {
      damage(run, target, s.droneDamage)
      d.cooldown = s.droneCooldown
      d.zap = { x: target.x, y: target.y, ttl: 4 }
    }
  }
  run.tempDrones = run.tempDrones.filter(d => d.ttl > 0)
  run.enemies = run.enemies.filter(e => !e.isDead)

  addScore(run, Math.max(0, p.vx) * 0.5)
}

function roman(n) {
  if (n > 39) return String(n)
  const parts = [[10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']]
  let out = ''
  for (const [v, s] of parts) while (n >= v) (out += s), (n -= v)
  return out
}

// The power on show: one glyph per stack, the run's build at a glance
export function threat(floor) {
  return 1 + Math.floor(floor / 3)
}

// ---------------------------------------------------------------- drawing

// The frame as rows of [char, fg, bg] cells
export function draw(run, columns, rows) {
  const grid = []
  for (let r = 0; r < rows; r++) {
    const row = []
    for (let c = 0; c < columns; c++) row.push([' ', null, null])
    grid.push(row)
  }
  const put = (c, r, ch, fg, bg = null) => {
    if (r >= 0 && r < rows && c >= 0 && c < columns) grid[r][c] = [ch, fg, bg]
  }
  const text = (c, r, s, fg, bg) => {
    for (let i = 0; i < s.length; i++) put(c + i, r, s[i], fg, bg)
  }

  const worldTop = 1
  const viewRows = rows - 2
  // Show the bottom of the world when the pane is short
  const skip = Math.max(0, WORLD_ROWS - viewRows)
  const pad = Math.max(0, viewRows - WORLD_ROWS)
  const toScreen = r => worldTop + pad + r - skip

  const p = run.player
  run.cameraX = Math.max(0, Math.min(run.world.width - columns, p.x - Math.floor(columns * 0.35)))
  const cam = Math.floor(run.cameraX)
  const boss = run.enemies.find(e => e.kind === 'boss')

  // Tiles
  for (let c = 0; c < columns; c++) {
    const wc = cam + c
    for (let r = skip; r < WORLD_ROWS; r++) {
      const t = tileAt(run.world, wc, r)
      const sr = toScreen(r)
      if (t === T_GROUND) {
        const isTop = !isSolid(tileAt(run.world, wc, r - 1))
        if (isTop) put(c, sr, '▀', C.grass, C.dirt)
        else put(c, sr, (wc * 7 + r * 3) % 11 === 0 ? '·' : ' ', C.dirtDot, C.dirt)
      } else if (t === T_BRICK) {
        put(c, sr, wc % 3 === 0 ? '▐' : '█', C.brick, '#57606A')
      } else if (t === T_TOKEN) {
        put(c, sr, '·', C.token)
      } else if (t === T_POWER) {
        put(c, sr, run.tick % 10 < 6 ? '◆' : '◇', C.power)
      } else if (t === T_LINT) {
        put(c, sr, '^', C.lint)
      }
    }
    if (wc === run.world.gateX) {
      for (let r = skip; r < WORLD_ROWS; r++) {
        if (!isSolid(tileAt(run.world, wc, r))) put(c, toScreen(r), boss ? '╳' : '┃', boss ? C.locked : C.gate)
      }
    }
  }
  const gateC = run.world.gateX - cam
  text(gateC - 2, toScreen(Math.max(skip, 2)), boss ? 'LOCKED' : 'MERGE', boss ? C.locked : C.gate)

  // Enemies: elites in gold, a hit flashes white
  const isFlashing = run.frightened > 0 && run.frightened < 30 && run.tick % 6 < 3
  const scaredColor = isFlashing ? '#FFFFFF' : C.scared
  for (const e of run.enemies) {
    const sc = Math.floor(e.x) - cam
    const sr = toScreen(Math.floor(e.y))
    const scared = run.frightened > 0 && e.kind !== 'boss'
    const tint = base => (e.hurtTicks > 0 ? '#FFFFFF' : scared ? scaredColor : e.isElite ? C.elite : base)
    if (e.kind === 'bug') text(sc, sr, e.vx > 0 ? 'ж›' : '‹ж', tint(C.bug))
    else if (e.kind === 'ghost') put(sc, sr, 'ᗣ', tint(e.color))
    else if (e.kind === 'hopper') put(sc, sr, e.isOnGround ? 'Ѫ' : 'Ж', tint(C.hopper))
    else if (e.kind === 'looper') put(sc, sr, '∞', tint(C.looper))
    else if (e.kind === 'turret') text(sc, sr, '<>', tint(C.turret))
    else if (e.kind === 'boss') {
      const color = tint(C.boss)
      const face = ['▛▀▀▀▀▜', '▌▘  ▝▐', '▙▄▄▄▄▟']
      face.forEach((line, i) => text(sc, sr + i, line, color, i === 1 ? '#3D0A0A' : null))
      put(sc + 1, sr + 1, '◣', C.elite, '#3D0A0A')
      put(sc + 4, sr + 1, '◢', C.elite, '#3D0A0A')
    }
  }
  for (const b of run.bullets) {
    put(Math.floor(b.x) - cam, toScreen(Math.floor(b.y)), b.isEnemy ? '*' : '»', b.isEnemy ? C.shot : C.bolt)
  }

  // Drones and their zaps
  for (const d of [...run.drones, ...run.tempDrones]) {
    const dc = Math.round(p.x + 1.5 + Math.cos(d.angle) * 5) - cam
    const dr = toScreen(Math.round(p.y - 1 + Math.sin(d.angle) * 1.5))
    put(dc, dr, '◈', C.drone)
    if (d.zap && d.zap.ttl-- > 0) put(Math.floor(d.zap.x) - cam, toScreen(Math.floor(d.zap.y)), '✕', C.drone)
  }

  // Clawd: an orange block with two eyes on four legs, blue while shielded
  const isBlinking = p.invulnerable > 0 && run.tick % 4 < 2
  if (!isBlinking && run.phase !== 'over') {
    const pc = Math.floor(p.x) - cam
    const pr = toScreen(Math.floor(p.y))
    const eyes = p.facing > 0 ? [' ', '▪', ' ', '▪'] : ['▪', ' ', '▪', ' ']
    for (let i = 0; i < 4; i++) put(pc + i, pr, eyes[i], C.eye, C.clawd)
    const isStriding = p.isOnGround && Math.abs(p.vx) > 0.1 && run.tick % 6 < 3
    const legs = !p.isOnGround ? '▘▘▝▝' : isStriding ? '▝▘▝▘' : '▌▌▐▐'
    for (let i = 0; i < 4; i++) put(pc + i, pr + 1, legs[i], C.clawd)
    if (run.shields > 0) {
      put(pc - 1, pr, '(', C.shield)
      put(pc + 4, pr, ')', C.shield)
    }
  }

  // The top line: lives, context, shields, tokens, floor and threat, score
  const lives = run.lives <= 5 ? '♥'.repeat(Math.max(0, run.lives)) : '♥×' + run.lives
  const filled = Math.round(Math.min(100, run.context) / 12.5)
  const bar = '█'.repeat(filled) + '░'.repeat(8 - filled)
  const ctxColor = run.context >= 75 ? C.bad : run.context >= 50 ? C.power : C.good
  let at = 0
  text(at, 0, lives, C.clawd)
  at += lives.length + 1
  text(at, 0, bar, ctxColor)
  at += 9
  if (run.shields > 0) {
    text(at, 0, '♦' + run.shields, C.shield)
    at += 3
  }
  const t = threat(run.floor)
  const stars = t <= 5 ? '▲'.repeat(t) : '▲' + t
  const left = '·' + run.tokens + ' F' + (run.floor + 1) + ' '
  text(at, 0, left, C.hud)
  at += left.length
  text(at, 0, stars, t >= 8 ? C.bad : t >= 4 ? C.power : C.dim)
  at += stars.length + 1
  text(at, 0, Math.floor(run.score).toLocaleString('en-US'), C.hud)

  // The bottom line: the boss's health, else the newest message, else a hint
  const last = run.ticker[run.ticker.length - 1]
  if (boss && p.x > run.world.arenaX - 10) {
    const label = boss.name + ' '
    const width = Math.max(10, columns - label.length - 1)
    const full = Math.round((boss.hp / boss.maxHp) * width)
    text(0, rows - 1, label, C.locked)
    text(label.length, rows - 1, '█'.repeat(full) + '░'.repeat(width - full), C.boss)
  } else if (last) text(0, rows - 1, last.text.slice(0, columns), last.color)
  else {
    const keys = ['←→ run', '↑ jump']
    if (lvl(run, 'fable')) keys.push('F fire')
    if (lvl(run, 'fast')) keys.push('X dash')
    keys.push('Esc prompt')
    text(0, rows - 1, keys.join(' · '), C.dim)
  }

  if (run.phase !== 'play') overlay(run, columns, rows, text, put)
  return grid
}

function overlay(run, columns, rows, text, put) {
  const lines = []
  if (run.phase === 'title') {
    lines.push(['CLAWD QUEST', C.clawd])
    lines.push(['', null])
    lines.push(['Run right. Eat tokens ·  Stomp bugs ж', C.text])
    lines.push(['◆ makes every enemy flee', C.text])
    lines.push(['Reach the MERGE gate, pick an upgrade', C.text])
    lines.push(['It never ends: you grow, so do they', C.text])
    lines.push(["What your Claude does helps or hurts", C.text])
    lines.push(['', null])
    lines.push([run.hasKeys ? 'Press → to start' : 'Click here, then press → to start', C.token])
  } else if (run.phase === 'paused') {
    lines.push([run.pauseReason ?? 'Paused', C.token])
    lines.push(['', null])
    lines.push(['Esc to answer · → to keep playing', C.text])
  } else if (run.phase === 'pick') {
    lines.push(['Floor ' + (run.floor + 1) + ' merged', C.gate])
    lines.push(['Pick an upgrade', C.text])
    lines.push(['', null])
    run.choices.forEach(({ key, rarity }, i) => {
      const u = UPGRADES[key]
      const r = RARITIES[rarity]
      const now = lvl(run, key)
      const next = now + r.levels
      lines.push([i + 1 + '  ' + u.name + ' ' + (now ? roman(now) + '→' : '') + roman(next), r.color])
      lines.push(['   ' + (rarity < 3 ? r.name + ' · ' : '') + u.text, C.dim])
    })
    lines.push(['', null])
    lines.push(['Next: threat ▲' + threat(run.floor + 1) + (isBossFloor(run.floor + 1) ? ' · BOSS' : ''), isBossFloor(run.floor + 1) ? C.locked : C.dim])
  } else if (run.phase === 'over') {
    lines.push(['RUN OVER', C.bad])
    lines.push([Math.floor(run.score).toLocaleString('en-US') + ' on floor ' + (run.floor + 1) + ' · ' + run.kills + ' kills', C.hud])
    const build = Object.entries(run.upgrades)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([k, v]) => UPGRADES[k].name + ' ' + roman(v))
      .join(', ')
    if (build) lines.push([build, C.dim])
    lines.push(['', null])
    const board = run.board ?? []
    if (board.length) {
      lines.push(['Leaderboard', C.gate])
      board.slice(0, Math.max(1, rows - 11)).forEach((b, i) => {
        const isMine = b.runId === run.runId
        const name = (b.name ?? '').slice(0, 14).padEnd(14)
        lines.push([String(i + 1).padStart(2) + '  ' + name + ' ' + String(b.score).padStart(8) + '  f' + b.floor, isMine ? C.clawd : C.text])
      })
      lines.push(['', null])
    }
    lines.push(['Press R for a new run', C.token])
  }
  const width = Math.min(columns - 2, Math.max(...lines.map(l => l[0].length)) + 4)
  const height = lines.length + 2
  const left = Math.max(0, Math.floor((columns - width) / 2))
  const top = Math.max(1, Math.floor((rows - height) / 2))
  const bg = '#1C2128'
  for (let r = 0; r < height; r++) {
    for (let c = 0; c < width; c++) {
      const isEdge = r === 0 || r === height - 1 || c === 0 || c === width - 1
      const ch = !isEdge ? ' ' : r === 0 ? (c === 0 ? '╭' : c === width - 1 ? '╮' : '─') : r === height - 1 ? (c === 0 ? '╰' : c === width - 1 ? '╯' : '─') : '│'
      put(left + c, top + r, ch, C.clawd, bg)
    }
  }
  lines.forEach(([s, color], i) => {
    const clipped = s.slice(0, width - 4)
    text(left + Math.max(2, Math.floor((width - clipped.length) / 2)), top + 1 + i, clipped, color ?? C.text, bg)
  })
}

// Rows of same-colored runs, for Text elements
export function toRuns(grid) {
  return grid.map(row => {
    const runs = []
    for (const [ch, fg, bg] of row) {
      const last = runs[runs.length - 1]
      if (last && last.fg === fg && last.bg === bg) last.text += ch
      else runs.push({ text: ch, fg, bg })
    }
    return runs
  })
}

// ---------------------------------------------------------------- the surface

// Terminals report key presses but not releases, so a key counts as held until
// its auto-repeat stops: long after a lone press, briefly once repeats flow
const HOLD_AFTER_PRESS_MS = 260
const HOLD_WHILE_REPEATING_MS = 110

const KEYS = {
  left: 'left',
  a: 'left',
  h: 'left',
  right: 'right',
  d: 'right',
  l: 'right',
  up: 'jump',
  w: 'jump',
  k: 'jump',
  ' ': 'jump',
  space: 'jump',
  z: 'jump',
  x: 'dash',
  f: 'fire',
  c: 'fire',
  down: 'stop',
  s: 'stop',
  r: 'restart',
  1: 'pick1',
  2: 'pick2',
  3: 'pick3',
}

export default function ClawdQuest(props, surface) {
  const { Box, Text } = surface.elements
  props = props ?? {}

  if (surface.state === undefined) {
    const seed = Math.floor(Math.random() * 1e9)
    const run = newRun(seed, props.resume)
    if (props.resume && !props.resume.isOver) run.phase = 'paused'
    run.board = props.board ?? []
    const game = {
      run,
      held: new Map(), // action -> { at, isRepeating }
      queued: new Set(),
      // Events from before this instance are history, not news
      seenEvent: Math.max(0, ...(props.events ?? []).map(e => e.id)),
      lastPoll: 0,
      props,
    }

    surface.onKey(e => {
      const action = KEYS[e.key.toLowerCase?.() ?? e.key] ?? KEYS[e.key]
      if (!action) return
      game.run.hasKeys = true
      const now = Date.now()
      if (action === 'left' || action === 'right') {
        const other = action === 'left' ? 'right' : 'left'
        game.held.delete(other)
      }
      const last = game.held.get(action)
      const isRepeating = !!last && now - last.at < 600
      game.held.set(action, { at: now, isRepeating })
      // A repeat of a held jump key floats, it doesn't jump again
      if (action === 'jump' && isRepeating) return
      if (action === 'stop') {
        game.held.delete('left')
        game.held.delete('right')
        return
      }
      game.queued.add(action)
    })

    surface.onPointer(e => {
      if (e.type === 'down') game.run.hasKeys = true
    })

    surface.every(TICK_MS, () => {
      const now = Date.now()
      const isHeld = action => {
        const h = game.held.get(action)
        if (!h) return false
        const window = h.isRepeating ? HOLD_WHILE_REPEATING_MS : HOLD_AFTER_PRESS_MS
        if (now - h.at < window) return true
        game.held.delete(action)
        return false
      }
      const q = game.queued
      if (q.has('restart') && game.run.phase === 'over') {
        game.run = newRun(Math.floor(Math.random() * 1e9), null)
        game.run.phase = 'play'
        game.run.hasKeys = true
        game.run.board = game.props.board ?? []
      }
      const run = game.run
      const input = {
        left: isHeld('left') || q.has('left'),
        right: isHeld('right') || q.has('right'),
        jump: q.has('jump'),
        jumpHeld: isHeld('jump'),
        dash: q.has('dash'),
        fire: isHeld('fire') || q.has('fire'),
        pick: q.has('pick1') ? 1 : q.has('pick2') ? 2 : q.has('pick3') ? 3 : 0,
      }
      q.clear()
      step(run, input)

      if (now - game.lastPoll >= POLL_MS) {
        game.lastPoll = now
        surface.post({ kind: 'poll', seen: game.seenEvent, run: snapshot(run) })
      }
      surface.setState(game)
    })

    surface.setState(game)
    return Text({ children: ['Loading Clawd Quest…'] })
  }

  const game = surface.state
  const run = game.run
  // New props: Claude's latest events and the leaderboard
  if (props !== game.props) {
    game.props = props
    run.board = props.board ?? run.board
    for (const ev of props.events ?? []) {
      if (ev.id <= game.seenEvent) continue
      game.seenEvent = ev.id
      if (run.phase === 'title') continue
      applyClaude(run, ev.kind)
      if (ev.kind === 'ask' && run.phase === 'play') {
        run.phase = 'paused'
        run.pauseReason = 'Claude needs you'
      }
    }
  }

  const columns = Math.max(30, surface.columns || 60)
  const rows = Math.max(10, surface.rows || WORLD_ROWS + 2)
  const lines = toRuns(draw(run, columns, rows))
  return Box({
    flexDirection: 'column',
    width: '100%',
    children: lines.map(runs =>
      Text({
        wrap: 'truncate',
        children: runs.map(r =>
          r.fg || r.bg
            ? Text({ ...(r.fg ? { color: r.fg } : {}), ...(r.bg ? { backgroundColor: r.bg } : {}), children: [r.text] })
            : r.text,
        ),
      }),
    ),
  })
}

export function snapshot(run) {
  return {
    seed: run.seed,
    runId: run.runId,
    floor: run.floor,
    score: Math.floor(run.score),
    tokens: run.tokens,
    kills: run.kills,
    lives: run.lives,
    context: run.context,
    upgrades: run.upgrades,
    isOver: run.phase === 'over',
    isPlaying: run.phase === 'play',
  }
}
