#!/usr/bin/env python3
"""Render docs/social.png, the 1280x640 card GitHub shows when the repo is
shared. The gauge in it is the real widget, not a mock-up.

    python3 docs/render-social.py
"""
import os, sys, importlib.util
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True      # keep __pycache__ out of the source tree

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, SCALE = 1280, 640, 2

TITLE = "Claude Context Bar"
TAGLINE = "Watch your Claude Code context window fill up\nwithout stopping to run /context"
FOOTER = "github.com/CashMahmood/claude-context-bar   ·   MIT   ·   Linux, macOS, Windows"

CSS = """
#card { background-color: #0F0F13; }
#title { color: #F5F5F7; font-size: 72px; font-weight: bold; }
#tagline { color: #9A9AA4; font-size: 30px; }
#footer { color: #6E6E76; font-size: 22px; }
"""


def main():
    os.environ["CLAUDE_BAR_W"] = str(150 * SCALE)
    os.environ["CLAUDE_BAR_H"] = str(26 * SCALE)
    loader = SourceFileLoader("contextbar",
                              os.path.join(HERE, os.pardir, "bin",
                                           "claude-context-bar"))
    bar = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("contextbar", loader))
    loader.exec_module(bar)
    bar.TRACK_W, bar.TRACK_H = 64 * SCALE, 5 * SCALE
    bar.LOGO_PX = 15 * SCALE

    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    win = Gtk.OffscreenWindow()
    win.set_size_request(W, H)
    bar.apply_css(win.get_screen())
    extra = Gtk.CssProvider()
    extra.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        win.get_screen(), extra, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    shell, fill, pct = bar.build_shell()
    shell.set_size_request(bar.WIDTH, bar.HEIGHT)
    fill.set_size_request(int(bar.TRACK_W * 0.34), bar.TRACK_H)
    fill.get_style_context().add_class("ample")
    pct.set_text("34%")

    gauge = Gtk.Box()
    gauge.set_halign(Gtk.Align.CENTER)
    gauge.pack_start(shell, False, False, 0)

    def label(name, text):
        lbl = Gtk.Label(name=name)
        lbl.set_text(text)
        lbl.set_justify(Gtk.Justification.CENTER)
        return lbl

    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    column.set_halign(Gtk.Align.CENTER)
    column.set_valign(Gtk.Align.CENTER)
    title = label("title", TITLE)
    tagline = label("tagline", TAGLINE)
    footer = label("footer", FOOTER)
    tagline.set_margin_top(22)
    gauge.set_margin_top(64)
    footer.set_margin_top(64)
    for widget in (title, tagline, gauge, footer):
        column.pack_start(widget, False, False, 0)

    card = Gtk.EventBox(name="card")
    card.add(column)
    card.set_size_request(W, H)
    win.add(card)
    win.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    pb = win.get_pixbuf()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "social.png")
    pb.savev(out, "png", [], [])
    print(f"wrote {out}  {pb.get_width()}x{pb.get_height()}")


if __name__ == "__main__":
    main()
