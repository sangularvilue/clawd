// Clawd Quest: an endless platformer in a pane beside the transcript while
// Claude works. What Claude does in the session reaches the game as events
// (an edit drops a power pellet, an error lets a bug in), and runs that end go
// on a leaderboard kept across sessions.

import type { Register } from 'claude-code'

const PANE = 'clawd-quest'
const DROP_IN_DELAY_MS = 2000
const COUNTDOWN_MS = 3000
const BOARD_SIZE = 10
// Claude can Read twenty files in a second; one shower each is plenty
const SAME_KIND_GAP_MS = 1500

const NAME_STARTS = ['Idle', 'Queued', 'Pending', 'Async', 'Blocked', 'Cached', 'Forked']
const NAME_ENDS = ['Clawd', 'Coder', 'Hacker', 'Intern', 'Prompter', 'Agent']

type ClaudeEvent = { id: number; kind: string }
type RunSnapshot = {
  seed: number
  runId: string
  floor: number
  score: number
  tokens: number
  lives: number
  context: number
  upgrades: Record<string, number>
  isOver: boolean
  isPlaying: boolean
}
type BoardEntry = { name: string; score: number; floor: number; runId: string; at: number }

// Kept across sessions in $.store
let isAuto = false
let name = ''
let board: BoardEntry[] = []
let savedRun: RunSnapshot | null = null

// This session's play
//   idle     the pane is closed
//   waiting  Claude is working; opening once the delay passes
//   offered  too narrow to open by itself, so the band offers a key
//   open     the pane is open
let phase: 'idle' | 'waiting' | 'offered' | 'open' = 'idle'
let isTurnRunning = false
let isAutoOpened = false
let isDismissed = false
let timer: { cancel: () => void } | null = null
let events: ClaudeEvent[] = []
let nextEventId = 1
const lastKindAt = new Map<string, number>()
let boardVersion = 0
let sentBoardVersion = -1
let lastRun: RunSnapshot | null = null
let lastSavedAt = 0

function cancelTimer() {
  timer?.cancel()
  timer = null
}

function clientProps() {
  return { events, board, name, resume: savedRun }
}

function push($: any, kind: string) {
  const now = Date.now()
  if (kind !== 'done' && kind !== 'ask' && now - (lastKindAt.get(kind) ?? 0) < SAME_KIND_GAP_MS) return
  lastKindAt.set(kind, now)
  events = [...events, { id: nextEventId++, kind }].slice(-20)
  if (phase === 'open') $.ui.invalidate('ui.render')
}

function kindOf(tool: string, isError: boolean) {
  if (isError) return 'error'
  if (['Edit', 'Write', 'MultiEdit', 'NotebookEdit'].includes(tool)) return 'edit'
  if (['Bash', 'PowerShell'].includes(tool)) return 'bash-ok'
  if (['Read', 'Grep', 'Glob'].includes(tool)) return 'search'
  if (['Agent', 'Task'].includes(tool)) return 'agent'
  if (tool === 'TodoWrite') return 'todo'
  if (['WebFetch', 'WebSearch'].includes(tool)) return 'web'
  return null
}

async function open($: any, isAsked: boolean) {
  const opened = await $.ui.open({ id: PANE, title: 'Clawd Quest', focus: true, rows: 20, columns: 76 })
  if (!opened.isPlaced) {
    await $.ui.close({ id: PANE })
    return false
  }
  phase = 'open'
  isAutoOpened = !isAsked
  $.ui.invalidate('ui.render')
  return true
}

function armDropIn($: any) {
  if (!isAuto || !isTurnRunning || isDismissed || phase !== 'idle') return
  phase = 'waiting'
  timer = $.clock.after(DROP_IN_DELAY_MS, async () => {
    timer = null
    if (phase !== 'waiting') return
    const surfaces = await $.session.surfaces()
    if (!surfaces.includes('terminal')) {
      phase = 'idle'
      return
    }
    if (!(await open($, false))) {
      phase = 'offered'
      $.ui.invalidate('ui.render')
    }
  })
}

async function pullOut($: any) {
  cancelTimer()
  if (phase === 'open') await $.ui.close({ id: PANE })
  phase = 'idle'
  $.ui.invalidate('ui.render')
}

// Claude is about to ask the person something, so they must see the prompt
async function needsYou($: any) {
  push($, 'ask')
  if (phase === 'waiting' || phase === 'offered') {
    cancelTimer()
    phase = 'idle'
    $.ui.invalidate('ui.render')
  } else if (phase === 'open' && isAutoOpened) {
    await pullOut($)
  }
}

async function record($: any, run: RunSnapshot) {
  if (board.some(b => b.runId === run.runId)) return
  const entry = { name, score: run.score, floor: run.floor + 1, runId: run.runId, at: Date.now() }
  const isBest = board.length === 0 || run.score > board[0].score
  board = [...board, entry].sort((a, b) => b.score - a.score).slice(0, BOARD_SIZE)
  boardVersion += 1
  await $.store.set('board', board)
  const rank = board.findIndex(b => b.runId === run.runId)
  if (rank >= 0) $.ui.toast((isBest ? 'New best! ' : '') + 'Clawd Quest: ' + run.score.toLocaleString('en-US') + ', #' + (rank + 1) + ' on the board')
  $.ui.invalidate('ui.render')
}

function boardText() {
  if (board.length === 0) return 'No Clawd Quest runs yet. /clawd to play.'
  return [
    'Clawd Quest leaderboard',
    ...board.map(
      (b, i) => String(i + 1).padStart(2) + '. ' + b.name.padEnd(16) + String(b.score).padStart(8) + '  floor ' + b.floor,
    ),
  ].join('\n')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    isAuto = (await $.store.get('isAuto')) === true
    board = ((await $.store.get('board')) as BoardEntry[] | undefined) ?? []
    savedRun = ((await $.store.get('run')) as RunSnapshot | undefined) ?? null
    name = ((await $.store.get('name')) as string | undefined) ?? ''
    if (!name) {
      const pick = (words: string[]) => words[Math.floor(Math.random() * words.length)]
      name = pick(NAME_STARTS) + pick(NAME_ENDS) + (10 + Math.floor(Math.random() * 90))
      await $.store.set('name', name)
    }
    await $.command.register({
      name: 'clawd',
      description: 'Play Clawd Quest while Claude works',
      argumentHint: '[off | board | name <name>]',
    })
    return next(e)
  })

  on('command.run', { command: 'clawd' }, async ($, e) => {
    const [verb, ...rest] = e.args.trim().split(/\s+/)
    if (verb === 'off') {
      isAuto = false
      await $.store.set('isAuto', false)
      await pullOut($)
      return { text: 'Clawd Quest won’t open by itself any more. /clawd plays again.' }
    }
    if (verb === 'board') return { text: boardText() }
    if (verb === 'name') {
      const wanted = rest.join(' ').trim().slice(0, 16)
      if (!wanted) return { text: 'You play as ' + name + '. /clawd name <name> changes it.' }
      name = wanted
      await $.store.set('name', name)
      return { text: 'You play as ' + name + ' now.' }
    }
    isAuto = true
    await $.store.set('isAuto', true)
    cancelTimer()
    await open($, true)
    return {
      text: 'Clawd Quest is on: click the pane, then press →. It opens by itself while Claude works. /clawd off stops that.',
    }
  })

  on('turn.start', async ($, e, next) => {
    isTurnRunning = true
    isDismissed = false
    push($, 'start')
    armDropIn($)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId) return next(e)
    isTurnRunning = false
    if (phase === 'waiting' || phase === 'offered') {
      cancelTimer()
      phase = 'idle'
      $.ui.invalidate('ui.render')
    } else if (phase === 'open' && !e.isAborted) {
      push($, 'done')
      if (isAutoOpened) {
        $.ui.toast("Claude's done. Back in 3…", { timeoutMs: COUNTDOWN_MS })
        timer = $.clock.after(COUNTDOWN_MS, () => {
          timer = null
          // A queued prompt may have started another turn meanwhile
          if (!isTurnRunning) void pullOut($)
        })
      }
    }
    return next(e)
  })

  on('tool.check', async ($, e, next) => {
    const result = await next(e)
    if (e.tool_use_id && result.decision === 'ask') await needsYou($)
    return result
  })

  on('tool.call', async ($, e, next) => {
    const tool = String(e.tool)
    if (tool === 'AskUserQuestion') await needsYou($)
    const result = await next(e)
    const kind = kindOf(tool, !!result.isError || 'deny' in result)
    if (kind) push($, kind)
    // Once an answered prompt lets Claude carry on, drop back in
    armDropIn($)
    return result
  })

  on('ui.close', async ($, e, next) => {
    if (e.id !== PANE) return next(e)
    if (e.origin?.kind === 'person' && isTurnRunning) isDismissed = true
    cancelTimer()
    phase = 'idle'
    isAutoOpened = false
    if (lastRun) {
      savedRun = lastRun.isOver ? null : lastRun
      await $.store.set('run', savedRun)
    }
    return next(e)
  })

  // The game posts its run four times a second, and hears back what's new
  on('ui.message', async ($, e) => {
    if (e.element !== 'game') return {}
    const data = e.data as { kind: string; seen: number; run: RunSnapshot }
    if (data?.kind !== 'poll') return {}
    lastRun = data.run
    if (data.run.isOver) {
      await record($, data.run)
      if (savedRun) {
        savedRun = null
        await $.store.set('run', null)
      }
    } else if (Date.now() - lastSavedAt > 3000) {
      lastSavedAt = Date.now()
      savedRun = data.run
      await $.store.set('run', savedRun)
    }
    const hasNews = events.some(ev => ev.id > data.seen)
    if (!hasNews && sentBoardVersion === boardVersion) return {}
    sentBoardVersion = boardVersion
    return { props: clientProps() }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (phase !== 'offered') return next(e)
    const { Box, Button } = $.ui.resolve(e)
    const others = await next(e)
    return Box({
      flexDirection: 'column',
      children: [
        Button({
          key: 'play',
          label: 'Play Clawd Quest while Claude works',
          hotkey: '1',
          plain: true,
          onPress: async () => {
            if (phase === 'offered' && !(await open($, true))) phase = 'idle'
          },
        }),
        ...(others ? [others] : []),
      ],
    })
  })

  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    if (phase !== 'open' || !lastRun?.isPlaying) return next(e)
    const suffix = ' · Clawd on floor ' + (lastRun.floor + 1) + ', ' + lastRun.score.toLocaleString('en-US') + '…'
    return next({ ...e, props: { ...e.props, suffix } })
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Client } = $.ui.resolve(e)
    if (e.surface !== 'terminal') return Text({ children: ['Clawd Quest plays in the terminal.'] })
    const rows = Math.max(12, Math.min(30, (e.props.scroll?.bodyRows ?? 20) - 1))
    return Box({
      flexDirection: 'column',
      children: [Client({ key: 'game', module: './game.js', width: '100%', height: rows, props: clientProps() })],
    })
  })
}
