#!/usr/bin/env bash
# Remove everything install.sh put in place.
set -uo pipefail

BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"

echo "==> stopping"
"$BIN/claude-context-bar" --quit 2>/dev/null || true

echo "==> removing the keyboard shortcut"
"$BIN/claude-context-bar" --remove-hotkey 2>/dev/null || true

echo "==> removing files"
desktop_dir="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
rm -fv "$BIN/claude-context-bar" \
       "$BIN/claude-context-probe" \
       "$APPS/claude-context-bar.desktop" \
       "$desktop_dir/claude-context-bar.desktop" \
       "$HOME/.config/autostart/claude-context-bar.desktop" \
       "$HOME/.local/share/icons/hicolor/scalable/apps/claude-context-bar.svg" \
       "$HOME/.config/claude-context-bar.json" \
       "$HOME/.cache/claude-context-bar.state" 2>/dev/null
rm -rfv "$HOME/.local/share/claude-context-bar"

command -v update-desktop-database >/dev/null && \
  update-desktop-database "$APPS" 2>/dev/null

echo "Done."
