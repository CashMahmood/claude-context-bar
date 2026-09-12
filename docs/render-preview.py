#!/usr/bin/env python3
"""Render docs/preview.png from the real widgets, so the image cannot drift
away from what the bar actually looks like.

    python3 docs/render-preview.py
"""
import os, sys, importlib.util
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True      # keep __pycache__ out of the source tree

os.environ.setdefault("GDK_BACKEND", "x11")

HERE = os.path.dirname(os.path.abspath(__file__))
# The script has no .py suffix, so point importlib at a source loader directly.
loader = SourceFileLoader(
    "contextbar", os.path.join(HERE, os.pardir, "bin", "claude-context-bar"))
bar = importlib.util.module_from_spec(importlib.util.spec_from_loader(
    "contextbar", loader))
loader.exec_module(bar)               # guarded by __main__, so nothing starts

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

STATES = [(17, "ample"), (62, "tight"), (91, "low")]
BACKDROP = "#0F0F13"

win = Gtk.OffscreenWindow()
bar.apply_css(win.get_screen())

extra = Gtk.CssProvider()
extra.load_from_data(f"#preview-bg {{ background-color: {BACKDROP}; }}".encode())
Gtk.StyleContext.add_provider_for_screen(
    win.get_screen(), extra, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=13)
for margin in ("top", "bottom", "start", "end"):
    getattr(column, f"set_margin_{margin}")(22)

for pct, state in STATES:
    shell, fill, label = bar.build_shell()
    shell.set_size_request(bar.WIDTH, bar.HEIGHT)
    fill.set_size_request(max(3, int(bar.TRACK_W * pct / 100.0)), bar.TRACK_H)
    fill.get_style_context().add_class(state)
    label.set_text(f"{pct}%")
    holder = Gtk.Box()
    holder.set_halign(Gtk.Align.CENTER)
    holder.pack_start(shell, False, False, 0)
    column.pack_start(holder, False, False, 0)

backdrop = Gtk.EventBox(name="preview-bg")
backdrop.add(column)
win.add(backdrop)
win.show_all()

while Gtk.events_pending():
    Gtk.main_iteration()

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "preview.png")
pixbuf = win.get_pixbuf()
if pixbuf is None:
    sys.exit("offscreen render produced nothing")
pixbuf.savev(out, "png", [], [])
print(f"wrote {out}  ({pixbuf.get_width()}x{pixbuf.get_height()})")
