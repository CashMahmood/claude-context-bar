#!/usr/bin/env bash
# Install the Claude Context Bar into the current user's home. No root needed.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share/claude-context-bar"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"

with_autostart=1
with_hotkey=1
with_desktop_icon=1
for arg in "$@"; do
  case "$arg" in
    --no-autostart)    with_autostart=0 ;;
    --no-hotkey)       with_hotkey=0 ;;
    --no-desktop-icon) with_desktop_icon=0 ;;
    -h|--help)
      echo "usage: install.sh [--no-autostart] [--no-hotkey] [--no-desktop-icon]"
      exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "==> checking prerequisites"
python3 - <<'PY' || { echo "   GTK 3 Python bindings missing."; \
  echo "   Debian/Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0"; \
  echo "   Fedora:        sudo dnf install python3-gobject gtk3"; \
  echo "   Arch:          sudo pacman -S python-gobject gtk3"; exit 1; }
import gi
gi.require_version("Gtk", "3.0"); gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GdkPixbuf
assert "svg" in [f.get_name() for f in GdkPixbuf.Pixbuf.get_formats()], \
    "no SVG loader (install librsvg)"
PY
echo "    GTK 3 + SVG loader present"

echo "==> installing"
mkdir -p "$BIN" "$SHARE" "$ICONS" "$APPS"
install -m 755 "$SRC/bin/claude-context-bar"   "$BIN/claude-context-bar"
install -m 755 "$SRC/bin/claude-context-probe" "$BIN/claude-context-probe"
install -m 644 "$SRC/share/logo.svg"           "$SHARE/logo.svg"
install -m 644 "$SRC/share/logo.svg"           "$ICONS/claude-context-bar.svg"
install -m 644 "$SRC/desktop/claude-context-bar.desktop" "$APPS/claude-context-bar.desktop"
echo "    binaries -> $BIN"
echo "    launcher -> $APPS"

if [ "$with_autostart" = 1 ]; then
  mkdir -p "$AUTOSTART"
  install -m 644 "$SRC/desktop/claude-context-bar-autostart.desktop" \
                 "$AUTOSTART/claude-context-bar.desktop"
  echo "    autostart -> $AUTOSTART"
fi

if [ "$with_desktop_icon" = 1 ]; then
  desktop_dir="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
  if [ -d "$desktop_dir" ]; then
    install -m 755 "$SRC/desktop/claude-context-bar.desktop" \
                   "$desktop_dir/claude-context-bar.desktop"
    # GNOME will not run a desktop file it has not been told to trust.
    gio set "$desktop_dir/claude-context-bar.desktop" \
        metadata::trusted true 2>/dev/null || true
    echo "    desktop icon -> $desktop_dir"
  fi
fi

command -v update-desktop-database >/dev/null && \
  update-desktop-database "$APPS" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null && \
  gtk-update-icon-cache -qtf "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

if [ "$with_hotkey" = 1 ] && command -v gsettings >/dev/null; then
  echo "==> binding Super+Shift+C"
  "$BIN/claude-context-bar" --install-hotkey || \
    echo "    (skipped; GNOME settings not available)"
fi

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo
     echo "!! $BIN is not on your PATH. Add this to ~/.bashrc:"
     echo "     export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

echo
echo "==> starting"
"$BIN/claude-context-bar" --quit 2>/dev/null || true
sleep 1
setsid nohup "$BIN/claude-context-bar" >/dev/null 2>&1 < /dev/null &
sleep 2
echo "    $("$BIN/claude-context-bar" --status)"
echo
echo "Done. The bar sits at the top-centre of your screen."
echo "  click it        -> pick which session to track"
echo "  Super+Shift+C   -> show / hide"
