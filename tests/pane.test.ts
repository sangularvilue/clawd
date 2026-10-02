import { expect, mock, test } from 'claude-code/testing'

import { applyClaude, newRun, step } from '../hooks/game.js'

const PANE_PROPS = {
  title: 'Clawd Quest',
  isFocused: true,
  bodyColumns: 72,
  placement: 'dock',
  scroll: { offset: 0, bodyRows: 22, contentRows: 22, maxRows: 22 },
  view: {},
} as any

test('the pane draws the title screen and plays', async ($, on) => {
  mock.store(on)
  const ui = await $.ui.mount({
    plugin: 'clawd-quest',
    surface: 'terminal',
    component: 'Pane',
    requestId: 'clawd-quest',
    props: PANE_PROPS,
    viewport: { columns: 160, rows: 40, isFullscreen: true } as any,
  })
  await ui.resize({ columns: 72, rows: 20, in: 'game' })
  await ui.advance(100)
  expect(await ui.find({ text: /CLAWD QUEST/, in: 'game' })).toBeDefined()

  await ui.key({ key: 'right', in: 'game' })
  for (let i = 0; i < 20; i++) {
    await ui.key({ key: 'right', in: 'game' })
    await ui.advance(100)
  }
  expect(await ui.find({ text: /CLAWD QUEST/, in: 'game' })).toBeUndefined()
  expect(await ui.find({ text: /F1 /, in: 'game' })).toBeDefined()

  // The run reports in and hears back
  await ui.advance(300)
  await ui.unmount()
})

test('a finished run reaches the board', async ($, on) => {
  mock.store(on)
  const ui = await $.ui.mount({
    plugin: 'clawd-quest',
    surface: 'terminal',
    component: 'Pane',
    requestId: 'clawd-quest',
    props: PANE_PROPS,
  })
  await ui.post(
    {
      kind: 'poll',
      seen: 0,
      run: { seed: 1, runId: 'r1', floor: 2, score: 4321, tokens: 9, lives: 0, context: 0, upgrades: {}, isOver: true, isPlaying: false },
    },
    { in: 'game' },
  )
  const shown: any = await $.command.run({ command: 'clawd', args: 'board' } as any)
  expect(String(shown?.text)).toContain('4321')
  await ui.unmount()
})

test('runs survive a long bot playthrough with Claude events', () => {
  const run = newRun(7)
  run.phase = 'play'
  for (let t = 0; t < 3000 && run.phase !== 'over'; t++) {
    if (run.phase === 'pick') step(run, { pick: 2 } as any)
    else step(run, { right: true, jump: t % 9 === 0, jumpHeld: true } as any)
    if (t % 200 === 0) applyClaude(run, ['edit', 'error', 'search', 'web', 'agent', 'bash-ok', 'todo'][(t / 200) % 7])
  }
  expect(run.score).toBeGreaterThan(0)
})
