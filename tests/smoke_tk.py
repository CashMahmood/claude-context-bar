#!/usr/bin/env python3
"""Drive the Tk backend against a stubbed toolkit.

This proves the Tk code path runs end to end -- geometry maths, the refresh
cycle, the command pump, the menu and the tooltip -- on a machine with no Tk
and no display. It cannot prove anything about how it looks; only a real
macOS or Windows run can do that.

    python3 tests/smoke_tk.py
"""
import os, sys, types, tempfile, importlib.util
from importlib.machinery import SourceFileLoader

# Point the module at a scratch config and cache BEFORE importing it, since it
# resolves those paths at import time. Without this the test would clobber the
# heartbeat of a bar that is actually running.
_scratch = tempfile.mkdtemp(prefix="ccb-smoke-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_scratch, "config")
os.environ["XDG_CACHE_HOME"] = os.path.join(_scratch, "cache")
if sys.platform in ("win32", "darwin"):
    os.environ["HOME"] = os.environ["USERPROFILE"] = _scratch

HERE = os.path.dirname(os.path.abspath(__file__))
BAR = os.path.join(HERE, os.pardir, "bin", "claude-context-bar")

calls = {"items": [], "after": [], "menu": [], "attrs": []}


class Item:
    _next = [0]

    def __init__(self, kind, args, kw):
        Item._next[0] += 1
        self.id = Item._next[0]
        self.kind, self.args, self.kw = kind, args, kw
        calls["items"].append(self)


class FakeCanvas:
    def __init__(self, master=None, **kw):
        self.kw = kw
        self.items = {}

    def _add(self, kind, args, kw):
        it = Item(kind, args, kw)
        self.items[it.id] = it
        return it.id

    def create_polygon(self, *a, **k):   return self._add("polygon", a, k)
    def create_rectangle(self, *a, **k): return self._add("rect", a, k)
    def create_text(self, *a, **k):      return self._add("text", a, k)
    def create_image(self, *a, **k):     return self._add("image", a, k)
    def coords(self, i, *a):             self.items[i].args = a
    def itemconfig(self, i, **k):        self.items[i].kw.update(k)
    def bind(self, seq, fn):             calls.setdefault("binds", {})[seq] = fn
    def pack(self, **k):                 pass


class FakeVar:
    def __init__(self, value=""): self._v = value
    def get(self):  return self._v
    def set(self, v): self._v = v


class FakeMenu:
    def __init__(self, master=None, **kw): pass
    def add_radiobutton(self, **kw): calls["menu"].append(kw.get("label"))
    def add_separator(self):         calls["menu"].append("---")
    def add_command(self, **kw):     calls["menu"].append(kw.get("label"))
    def tk_popup(self, x, y):        pass
    def grab_release(self):          pass


class FakeWidget:
    """Stands in for Label and, with the window methods, Toplevel."""

    def __init__(self, master=None, **kw):
        self.kw = kw
        calls.setdefault("widgets", []).append(kw)

    def pack(self, **k): pass
    def destroy(self):   pass
    def overrideredirect(self, *a): pass
    def wm_attributes(self, *a): pass
    def geometry(self, g): pass


class FakeRoot(FakeWidget):
    def title(self, *a): pass
    def overrideredirect(self, *a): pass
    def wm_attributes(self, *a):
        calls["attrs"].append(a)
        if a and a[0] == "-transparentcolor":
            raise FakeTclError("not supported")     # mimic Linux/macOS
    def geometry(self, g): calls["geometry"] = g
    def winfo_screenwidth(self):  return 1920
    def winfo_rootx(self): return 0
    def winfo_rooty(self): return 0
    def after(self, ms, fn=None): calls["after"].append((ms, fn))
    def deiconify(self): pass
    def withdraw(self):  pass
    def destroy(self):   pass
    def mainloop(self):  pass


class FakePhoto:
    def __init__(self, file=None, **kw):
        if not file or not os.path.exists(file):
            raise FakeTclError("no such image")
        calls["photo"] = file


class FakeTclError(Exception):
    pass


def fake_tkinter():
    m = types.ModuleType("tkinter")
    m.Tk, m.Canvas, m.Menu = FakeRoot, FakeCanvas, FakeMenu
    m.Toplevel, m.Label, m.StringVar = FakeWidget, FakeWidget, FakeVar
    m.PhotoImage = FakePhoto
    m.TclError = FakeTclError
    return m


def main():
    sys.modules["tkinter"] = fake_tkinter()
    loader = SourceFileLoader("contextbar", BAR)
    bar = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("contextbar", loader))
    loader.exec_module(bar)

    model = bar.Model()
    bar.run_tk(model)                     # returns at the stubbed mainloop

    images = [i for i in calls["items"] if i.kind == "image"]
    polys = [i for i in calls["items"] if i.kind == "polygon"]
    rects = [i for i in calls["items"] if i.kind == "rect"]
    texts = [i for i in calls["items"] if i.kind == "text"]

    problems = []
    # The mark is a pre-rendered PNG when available, since Tk cannot
    # antialias polygons; the drawn starburst is only the fallback.
    if images:
        if polys:
            problems.append("drew both the bitmap mark and the fallback rays")
    elif len(polys) != 12:
        problems.append(f"expected 12 fallback rays, drew {len(polys)}")
    if len(rects) != 2:
        problems.append(f"expected track + fill, drew {len(rects)} rects")
    if len(texts) != 1:
        problems.append(f"expected one label, drew {len(texts)}")
    if calls.get("geometry") != f"{bar.WIDTH}x{bar.HEIGHT}+885+{bar.Y_OFFSET}":
        problems.append(f"bad geometry: {calls.get('geometry')}")
    for it in polys + rects:
        for v in it.args:
            if isinstance(v, (int, float)) and not (-1 <= v <= 400):
                problems.append(f"{it.kind} coordinate out of range: {v}")

    # the refresh and pump callbacks must have been scheduled
    scheduled = {ms for ms, _ in calls["after"]}
    if bar.POLL_MS not in scheduled:
        problems.append("command pump was never scheduled")

    # click the bar: this builds the menu from real session data
    class Event:
        x_root = y_root = 10
    binds = calls.get("binds", {})
    for seq in ("<Button-1>", "<Button-3>"):
        if seq not in binds:
            problems.append(f"{seq} was never bound")
    if "<Button-1>" in binds:
        binds["<Button-1>"](Event())
    if len(calls["menu"]) < 3:
        problems.append(f"menu built only {len(calls['menu'])} rows")
    if calls["menu"] and calls["menu"][0] != "Auto — newest session":
        problems.append(f"first menu row is {calls['menu'][0]!r}")
    if "Hide" not in calls["menu"] or "Quit" not in calls["menu"]:
        problems.append("menu is missing Hide/Quit")

    # hover: the tooltip carries the session name
    if "<Enter>" in binds:
        binds["<Enter>"](None)
        binds["<Leave>"](None)

    # drive one command round-trip through the real pump
    bar.send("hide")
    pump = next(fn for ms, fn in calls["after"] if ms == bar.POLL_MS)
    pump()
    if bar.read_state() != "hidden":
        problems.append(f"hide command ignored (state={bar.read_state()})")
    bar.send("show")
    pump()
    if bar.read_state() != "visible":
        problems.append(f"show command ignored (state={bar.read_state()})")
    bar.clear_runtime()
    __import__("shutil").rmtree(_scratch, ignore_errors=True)

    print(f"  mark           : {'PNG ' + os.path.basename(calls['photo']) if images else str(len(polys)) + ' drawn rays'}")
    print(f"  track + fill   : {len(rects)}")
    print(f"  label text     : {texts[0].kw.get('text') if texts else '-'}")
    print(f"  geometry       : {calls.get('geometry')}")
    print(f"  window attrs   : {[a[0] for a in calls['attrs']]}")
    print(f"  menu rows      : {len(calls['menu'])} -> {calls['menu'][:4]}")
    if problems:
        print("\nFAILED:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("\n  Tk backend executes cleanly against a stubbed toolkit.")


if __name__ == "__main__":
    main()
