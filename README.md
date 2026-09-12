# Claude Context Bar

A minimal always-on-top overlay for Linux that shows how much **context window**
is left in your running [Claude Code](https://claude.com/claude-code) session —
by session name, not just by folder.

```
                    ╭───────────────────────╮
                    │  ✳   ▬▬▭▭▭▭▭▭▭   16%  │
                    ╰───────────────────────╯
                       ↑       ↑         ↑
                     mark    track     used
```

It sits at the top-centre of the screen, refreshes every few seconds, and turns
amber then red as the window fills up. The track and the number both show how
much context is **used**, counting upward, so they agree with what `/context`
reports inside Claude Code. Hover for the session name, or click to switch
sessions.

## Why

`/context` tells you where you stand only when you stop and ask. This keeps the
number in view while you work, so a compaction never takes you by surprise.

## Features

- **Named sessions.** Reads the session's own title — *"Set up YunCore APH4-BE3600"*,
  not `-home-user-project` — and shows it in the tooltip and the picker.
- **Small on purpose.** 150×26 px. It reports a number, it does not narrate.
- **Session picker.** Click the bar to switch between recent sessions, or leave
  it on **Auto** to follow whichever one you are using right now.
- **Show / hide.** `Super+Shift+C` from anywhere, a menu item, or the CLI.
- **Colour-coded headroom.** Green below 50 % used, amber beyond, red past 80 %.
- **Multi-window aware.** Detects both the 200 k and 1 M context windows.
- **Reads numbers only.** It parses token counts, the session id, its title and
  its working directory. It never reads, stores or transmits message content,
  and it makes no network calls of any kind.

## Requirements

- Linux with X11 **or** Wayland (it runs through XWayland automatically)
- Python 3.8+
- GTK 3 Python bindings and an SVG loader

| Distro | Command |
| --- | --- |
| Debian / Ubuntu | `sudo apt install python3-gi gir1.2-gtk-3.0 librsvg2-common` |
| Fedora | `sudo dnf install python3-gobject gtk3 librsvg2` |
| Arch | `sudo pacman -S python-gobject gtk3 librsvg` |

Developed and tested on Ubuntu 24.04, GNOME Shell 46, Wayland.

## Install

```bash
git clone https://github.com/CashMahmood/claude-context-bar.git
cd claude-context-bar
./install.sh
```

Everything lands under your home directory — no root, no system files:

| Path | What |
| --- | --- |
| `~/.local/bin/claude-context-bar` | the overlay |
| `~/.local/bin/claude-context-probe` | the reader that produces the numbers |
| `~/.local/share/claude-context-bar/logo.svg` | the mark |
| `~/.local/share/applications/` | app-menu launcher |
| `~/.config/autostart/` | starts at login |
| `~/.config/claude-context-bar.json` | which session you pinned |

Installer flags: `--no-autostart`, `--no-hotkey`, `--no-desktop-icon`.

## Usage

Click the bar to open the menu. Everything is also available from the CLI:

| Command | Effect |
| --- | --- |
| `claude-context-bar` | start it (or reveal the running one) |
| `claude-context-bar --toggle` | show / hide — this is what the hotkey calls |
| `claude-context-bar --show` / `--hide` | force one or the other |
| `claude-context-bar --status` | running? visible? |
| `claude-context-bar --quit` | stop it |
| `claude-context-bar --install-hotkey` | bind `Super+Shift+C` |
| `claude-context-bar --remove-hotkey` | unbind it |

The reader works standalone, and prints JSON:

```bash
claude-context-probe              # the newest session
claude-context-probe --list       # every recent session
claude-context-probe --session ID # one specific session
```

```json
{"id": "6e843c67-…", "title": "Context usage progress bar overlay",
 "project": "/home/you/work", "used": 118437, "limit": 1000000,
 "pct_used": 11.8, "pct_left": 88.2, "model": "claude-opus-5", "ok": true}
```

That makes it easy to reuse elsewhere — a tmux status line, Waybar, Polybar,
i3blocks, or a shell prompt.

## Configuration

Set these in the environment before launching:

| Variable | Default | Meaning |
| --- | --- | --- |
| `CLAUDE_BAR_W` | `150` | width in pixels |
| `CLAUDE_BAR_H` | `26` | height in pixels |
| `CLAUDE_BAR_Y` | `38` | distance from the top edge |
| `CLAUDE_BAR_INTERVAL` | `4` | refresh seconds |
| `CLAUDE_BAR_CLICKTHROUGH` | unset | `1` makes clicks pass through — the menu stops working, so drive it by hotkey |
| `CLAUDE_CTX_LIMIT` | auto | force the window size, e.g. `200000` |

## How it works

Claude Code appends a JSON Lines transcript per session under
`~/.claude/projects/<encoded-path>/<session-id>.jsonl`. The reader:

1. picks the most recently modified transcript (or the one you pinned);
2. scans backwards for the last `usage` object and adds up `input_tokens`,
   `cache_read_input_tokens` and `cache_creation_input_tokens` — the last
   assistant turn's prompt *is* the live context. The reply's `output_tokens`
   are deliberately excluded, so the figure tracks `/context` rather than
   running slightly ahead of it;
3. takes the session name from the newest `aiTitle` record and the project from
   `cwd`.

The context window is read from `~/.claude/settings.json`, because the
transcript records the bare model id (`claude-opus-5`) while only the settings
file keeps the `[1m]` suffix that separates the 1 M window from the 200 k one.
If the measured usage exceeds the assumed limit, it corrects itself upward.

## Known limitations

- **It cannot cover the GNOME top bar.** A Wayland compositor gives a normal
  client no say in its position or stacking, so the overlay runs through
  XWayland, where both work — but GNOME Shell draws its own panel above every
  window. The bar therefore sits just *below* the panel. Covering the panel
  would require a GNOME Shell extension.
- **The window size is inferred**, not reported. If you switch a single session
  to a different model mid-flight, set `CLAUDE_CTX_LIMIT`.
- **The percentage is of the raw context window.** Claude Code reserves an
  auto-compact buffer (33 k on a 1 M window) that it reports separately, so
  compaction begins slightly before the bar reads 100 %.

## Uninstall

```bash
./uninstall.sh
```

Removes every file, the autostart entry and the keyboard shortcut, leaving any
other custom shortcuts you have alone.

## Contributing

Issues and pull requests are welcome. Useful directions: a GNOME Shell
extension build so it can sit in the panel proper, wlroots support via
`gtk-layer-shell`, and status-line adapters.

## Licence

MIT — see [LICENSE](LICENSE). Use it, fork it, ship it.

---

Not affiliated with, endorsed by, or sponsored by Anthropic. *Claude* is a
trademark of Anthropic, PBC. The starburst in `share/logo.svg` is an original
glyph drawn for this project.
