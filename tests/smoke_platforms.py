#!/usr/bin/env python3
"""Exercise the macOS and Windows code paths on any machine.

The installer and the bar both branch on sys.platform, and on Linux those
branches never execute -- a typo or a missing dictionary key in them would ship
undetected. This flips the platform flags and runs the branches for real,
writing their output into a temporary directory so the result can be inspected.

It cannot prove macOS or Windows behaviour. It proves the code runs.

    python3 tests/smoke_platforms.py
"""
import os, sys, types, tempfile, shutil, importlib.util
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)
problems = []


def load(path, name):
    loader = SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


def check(cond, msg):
    if not cond:
        problems.append(msg)


def platform_paths():
    """bar._locations() must produce sane paths on every platform."""
    bar = load(os.path.join(ROOT, "bin", "claude-context-bar"), "bar")
    home = os.path.expanduser("~")
    for flags, label, expect in (
            ((False, False), "linux", ".config"),
            ((False, True), "macos", "Library"),
            ((True, False), "windows", "claude-context-bar")):
        bar.IS_WIN, bar.IS_MAC = flags
        if flags[0]:
            os.environ["APPDATA"] = os.path.join(home, "AppData", "Roaming")
            os.environ["LOCALAPPDATA"] = os.path.join(home, "AppData", "Local")
        cfg, state = bar._locations()
        print(f"  {label:8} config={cfg.replace(home,'~')}")
        print(f"  {'':8} state ={state.replace(home,'~')}")
        check(expect in cfg, f"{label}: unexpected config path {cfg}")
        check(os.path.isabs(cfg) and os.path.isabs(state),
              f"{label}: paths must be absolute")
    bar.IS_WIN = bar.IS_MAC = False


def installer_branches():
    """targets(), autostart() and desktop_launcher() for each platform."""
    inst = load(os.path.join(ROOT, "install.py"), "inst")
    for flags, label in (((False, False), "linux"),
                         ((False, True), "macos"),
                         ((True, False), "windows")):
        scratch = tempfile.mkdtemp(prefix=f"ccb-{label}-")
        try:
            inst.IS_WIN, inst.IS_MAC = flags
            inst.HOME = scratch
            os.environ["APPDATA"] = os.path.join(scratch, "Roaming")
            os.environ["LOCALAPPDATA"] = os.path.join(scratch, "Local")

            t = inst.targets()
            # every key the installer and uninstaller dereference
            for key in ("bin", "share", "desktop", "startup"):
                check(key in t, f"{label}: targets() is missing '{key}'")
            if label == "linux":
                for key in ("apps", "icons"):
                    check(key in t, f"{label}: targets() is missing '{key}'")

            bar = os.path.join(t["bin"], "claude-context-bar")
            py = inst.python_for_gui()
            os.makedirs(t["desktop"], exist_ok=True)

            entry = inst.autostart(t, bar, py)
            check(entry and os.path.exists(entry),
                  f"{label}: autostart wrote nothing")
            body = open(entry).read()
            print(f"  {label:8} autostart -> {os.path.basename(entry)} "
                  f"({len(body)} bytes)")
            check(bar in body, f"{label}: autostart does not reference the bar")
            if label == "macos":
                import xml.dom.minidom
                try:
                    xml.dom.minidom.parseString(body)
                except Exception as exc:
                    problems.append(f"macos: LaunchAgent plist is not valid XML: {exc}")
                check("RunAtLoad" in body, "macos: plist has no RunAtLoad")
            if label == "windows":
                check(body.startswith("@echo off"),
                      "windows: startup script is not a batch file")
                check('"' + py + '"' in body,
                      "windows: python path is not quoted (spaces in Program Files)")

            launcher = inst.desktop_launcher(t, bar, py)
            check(launcher and os.path.exists(launcher),
                  f"{label}: desktop launcher wrote nothing")
            lbody = open(launcher).read()
            print(f"  {label:8} launcher  -> {os.path.basename(launcher)} "
                  f"({len(lbody)} bytes)")
            check(bar in lbody, f"{label}: launcher does not reference the bar")
            if label != "linux":
                check("--show" in lbody, f"{label}: launcher does not pass --show")
            if label == "macos":
                check(os.access(launcher, os.X_OK),
                      "macos: .command launcher is not executable")

            # the uninstaller must name every file the installer created
            created = {entry, launcher}
            gone = {os.path.join(t["bin"], "claude-context-bar"),
                    os.path.join(t["bin"], "claude-context-probe"),
                    os.path.join(t["desktop"], "claude-context-bar.cmd"),
                    os.path.join(t["desktop"], "Claude Context Bar.command"),
                    os.path.join(t["desktop"], "claude-context-bar.desktop"),
                    os.path.join(t["startup"], "claude-context-bar.cmd"),
                    os.path.join(t["startup"], "claude-context-bar.desktop"),
                    os.path.join(t["startup"], f"{inst.PLIST_LABEL}.plist")}
            missed = created - gone
            check(not missed, f"{label}: uninstall would not remove {missed}")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    inst.IS_WIN = inst.IS_MAC = False


def tk_branches():
    """Run the Tk backend's macOS and Windows branches against a stub."""
    sys.path.insert(0, HERE)
    import smoke_tk as stub
    for flags, label in (((False, True), "macos"), ((True, False), "windows")):
        stub.calls["items"].clear()
        stub.calls["attrs"].clear()
        sys.modules["tkinter"] = stub.fake_tkinter()
        bar = load(os.path.join(ROOT, "bin", "claude-context-bar"), "bar_" + label)
        bar.IS_WIN, bar.IS_MAC = flags
        try:
            bar.run_tk(bar.Model())
        except Exception as exc:
            problems.append(f"{label}: Tk backend raised {type(exc).__name__}: {exc}")
            continue
        attrs = [a[0] for a in stub.calls["attrs"]]
        print(f"  {label:8} window attributes -> {attrs}")
        check("-topmost" in attrs, f"{label}: window is not set topmost")
        if label == "windows":
            check("-toolwindow" in attrs,
                  "windows: not marked a tool window, so it appears in alt-tab")


for name, fn in (("platform paths", platform_paths),
                 ("installer branches", installer_branches),
                 ("Tk platform branches", tk_branches)):
    print(f"== {name} ==")
    try:
        fn()
    except Exception as exc:
        problems.append(f"{name} raised {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
    print()

if problems:
    print("FAILED:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("All macOS and Windows code paths execute.")
