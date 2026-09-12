# Security policy

## Reporting a vulnerability

Please report privately through
[GitHub Security Advisories](https://github.com/CashMahmood/claude-context-bar/security/advisories/new)
rather than opening a public issue. I will acknowledge within a week.

## What this tool touches

It is a desktop overlay that reads local files. Understanding its reach should
not take long:

- **Reads** `~/.claude/projects/*/*.jsonl` and `~/.claude/jobs/*/state.json`,
  extracting only token counts, session id, session name and working
  directory. Message content is never parsed or emitted.
- **Writes** its own config, visibility, heartbeat and command files, all
  `0600`, under the platform's standard config and cache directories.
- **Executes** exactly two things: itself (the reader, through
  `sys.executable`) and `gsettings`, to register the GNOME shortcut.
- **Never** opens a socket, makes an HTTP request, phones home, or asks for
  root. There is no telemetry and no update check.

## Design guarantees

| Guarantee | How |
| --- | --- |
| No command injection | Every subprocess call passes an argument list; no `shell=True`, no `os.system`, no `eval` |
| No path traversal | `--session` is matched against known transcript names, never joined into a path |
| No cross-user signalling | Instance discovery checks the owning uid; `/proc` lists every user's processes |
| No credential material | Nothing is ever read from or written to any keychain, token store or network |
| Your shortcuts stay intact | Installing reuses its own keybinding slot; uninstalling removes only its own; it refuses to rewrite the list if it finds an entry it cannot parse |
| No privilege escalation | Neither installer uses `sudo`; everything lives under your home directory |

## Scope

Session ids, session names and project paths appear in the overlay, its tooltip
and the reader's JSON output. If you screen-share the bar, treat those the way
you would treat your terminal title.
