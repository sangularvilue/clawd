# Clawd Quest

A Claude Code plugin: an endless, procedurally generated roguelike platformer
starring Clawd, played in a pane beside the transcript while Claude works.

Super Mario Bros meets Pac-Man meets Hades. Run and stomp, eat tokens and power
pellets while hallucinations chase you, and pick an upgrade at the end of every
floor. Nothing tops out: you keep getting stronger, and the enemies keep getting
harder.

It's drawn in plain coloured text, so it runs on macOS, Windows and Linux in any
terminal, with nothing to download.

## Install

```
/plugin marketplace add sangularvilue/clawd
/plugin install clawd-quest@clawd
```

Then type `/clawd`, click the pane, and press →.

| Command | |
| :- | :- |
| `/clawd` | open the game, and let it open by itself while Claude works |
| `/clawd off` | stop it opening by itself |
| `/clawd board` | show the leaderboard |
| `/clawd name <name>` | set your name on the leaderboard |

## Controls

Click the game first so it gets your keys. Esc goes back to the prompt.

| | |
| :- | :- |
| Run | ← → or A D |
| Jump (hold to go higher) | ↑, W or space |
| Fire (Code Bolts) | F |
| Dash (Fast Mode) | X |
| Pick an upgrade | 1 2 3 |
| New run | R |

## The game

- **Tokens** `·` are points. **Power pellets** `◆` make every enemy flee for a while, so you can eat them.
- Getting hit fills your **context** bar. When it's full you auto-compact and lose a life.
- Each floor ends at a **MERGE** gate, where you pick 1 of 3 upgrades. Each pick rolls Common, Rare, Epic or Legendary, worth 1, 2, 3 or 5 levels. Rarer rolls come more often deeper in.
- Upgrades stack without limit: Opus 5.5, Extended Thinking, Prompt Caching, /compact, 1M Context, Auto-accept, Subagent, Hooks, Bypass Permissions, Ultrathink, Fast Mode, MCP Server, Code Bolts and Git Worktree.
- Enemies get more health, speed and numbers every floor. New kinds join as you go: bugs `ж`, hallucinations `ᗣ`, regressions `Ѫ`, merge conflicts `<>` and infinite loops `∞`. From floor 6 there are gold elites, and every 5th floor has a boss that keeps the gate locked until it's beaten.

## What your Claude does

| Claude… | In the game |
| :- | :- |
| edits a file | a power pellet appears ahead |
| runs a command that works | context goes down 10% |
| searches code | a shower of tokens |
| starts a subagent | a helper drone for 20s |
| updates its todo list | +50 |
| gets a tool error | a bug crawls in |
| goes online | a hallucination chases you |
| finishes | +500, and you're handed back after 3s |
| needs your input | the game pauses |

## Leaderboard

Your top 10 runs are kept on your machine across sessions.

## Development

`hooks/game.js` is the whole game: a `Client` surface module plus the pure game
core the tests drive. `hooks/register.ts` turns Claude's tool calls into game
events and keeps the leaderboard.

```
claude plugin validate .
claude plugin test .
claude --plugin-dir .
```
