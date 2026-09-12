#!/usr/bin/env python3
"""Cross-platform installer for the Claude Context Bar.

    python3 install.py              install
    python3 install.py --uninstall  remove everything it put in place

Options: --no-autostart, --no-hotkey, --no-desktop-icon, --no-start

On Linux ./install.sh does the same thing and is the better-tested path; this
script exists so macOS and Windows have one too.
"""
import os, sys, shutil, subprocess, argparse

APP = "claude-context-bar"
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
SRC = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

PLIST_LABEL = "com.github.cashmahmood.claude-context-bar"


def targets():
    """Where the pieces live on this platform."""
    if IS_WIN:
        root = os.path.join(os.environ.get("LOCALAPPDATA") or HOME, APP)
        return {"bin": os.path.join(root, "bin"),
                "share": os.path.join(root, "share"),
                "desktop": os.path.join(HOME, "Desktop"),
                "startup": os.path.join(
                    os.environ.get("APPDATA") or HOME, "Microsoft", "Windows",
                    "Start Menu", "Programs", "Startup")}
    base = {"bin": os.path.join(HOME, ".local", "bin"),
            "share": os.path.join(HOME, ".local", "share", APP),
            "desktop": os.path.join(HOME, "Desktop")}
    if IS_MAC:
        base["startup"] = os.path.join(HOME, "Library", "LaunchAgents")
    else:
        base["startup"] = os.path.join(HOME, ".config", "autostart")
        base["apps"] = os.path.join(HOME, ".local", "share", "applications")
        base["icons"] = os.path.join(
            HOME, ".local", "share", "icons", "hicolor", "scalable", "apps")
    return base


def python_for_gui():
    """pythonw.exe keeps a console window from flashing up on Windows."""
    if IS_WIN:
        cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if os.path.exists(cand):
            return cand
    return sys.executable


def check_toolkit():
    import importlib.util
    if not (IS_WIN or IS_MAC) and importlib.util.find_spec("gi"):
        return "GTK 3"
    if importlib.util.find_spec("tkinter"):
        return "Tk"
    print("!! No supported GUI toolkit found.")
    if IS_WIN or IS_MAC:
        print("   Tk ships with the python.org installer; the Microsoft Store")
        print("   and some Homebrew builds omit it. Reinstall Python from")
        print("   python.org, or: brew install python-tk")
    else:
        print("   Debian/Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0")
        print("               or: sudo apt install python3-tk")
    sys.exit(1)


def write(path, text, executable=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\r\n" if IS_WIN else "\n") as fh:
        fh.write(text)
    if executable and not IS_WIN:
        os.chmod(path, 0o755)


def install(args):
    t = targets()
    print(f"==> {check_toolkit()} found")

    print("==> installing")
    os.makedirs(t["bin"], exist_ok=True)
    os.makedirs(t["share"], exist_ok=True)
    for name in (APP, "claude-context-probe"):
        dst = os.path.join(t["bin"], name)
        shutil.copy2(os.path.join(SRC, "bin", name), dst)
        if not IS_WIN:
            os.chmod(dst, 0o755)
    for name in os.listdir(os.path.join(SRC, "share")):
        shutil.copy2(os.path.join(SRC, "share", name),
                     os.path.join(t["share"], name))
    bar = os.path.join(t["bin"], APP)
    py = python_for_gui()
    print(f"    binaries -> {t['bin']}")

    if not (IS_WIN or IS_MAC):
        for key in ("apps", "icons"):
            os.makedirs(t[key], exist_ok=True)
        shutil.copy2(os.path.join(SRC, "desktop", f"{APP}.desktop"),
                     os.path.join(t["apps"], f"{APP}.desktop"))
        shutil.copy2(os.path.join(SRC, "share", "logo.svg"),
                     os.path.join(t["icons"], f"{APP}.svg"))
        pin_exec(os.path.join(t["apps"], f"{APP}.desktop"), bar)
        print(f"    launcher -> {t['apps']}")

    if args.desktop_icon and os.path.isdir(t["desktop"]):
        launcher = desktop_launcher(t, bar, py)
        if launcher:
            print(f"    desktop icon -> {launcher}")

    if args.autostart:
        entry = autostart(t, bar, py)
        if entry:
            print(f"    autostart -> {entry}")

    if args.hotkey and not (IS_WIN or IS_MAC) and shutil.which("gsettings"):
        print("==> binding Super+Shift+C")
        subprocess.run([sys.executable, bar, "--install-hotkey"], check=False)
    elif args.hotkey:
        print("==> no global hotkey on this platform")
        print(f"    bind this yourself: {py} {bar} --toggle")

    if t["bin"] not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"\n!! {t['bin']} is not on your PATH.")
        if IS_WIN:
            print(f'   setx PATH "%PATH%;{t["bin"]}"')
        else:
            print(f'   export PATH="{t["bin"]}:$PATH"')

    if args.start:
        print("\n==> starting")
        subprocess.Popen([py, bar], close_fds=True,
                         creationflags=0x00000008 if IS_WIN else 0)
    print("\nDone. The bar sits at the top-centre of your screen.")
    print("  click it -> pick which session to track")


def pin_exec(desktop_file, bar):
    """A bare Exec= resolves through PATH; pin it to the real binary."""
    with open(desktop_file) as fh:
        text = fh.read()
    with open(desktop_file, "w") as fh:
        fh.write(text.replace("Exec=claude-context-bar", f"Exec={bar}"))


def desktop_launcher(t, bar, py):
    path = os.path.join(t["desktop"], f"{APP}.cmd" if IS_WIN else
                        ("Claude Context Bar.command" if IS_MAC
                         else f"{APP}.desktop"))
    if IS_WIN:
        write(path, f'@echo off\r\nstart "" "{py}" "{bar}" --show\r\n')
    elif IS_MAC:
        write(path, f'#!/bin/sh\nexec "{py}" "{bar}" --show\n', executable=True)
    else:
        shutil.copy2(os.path.join(SRC, "desktop", f"{APP}.desktop"), path)
        pin_exec(path, bar)
        os.chmod(path, 0o755)
        subprocess.run(["gio", "set", path, "metadata::trusted", "true"],
                       check=False, stderr=subprocess.DEVNULL)
    return path


def autostart(t, bar, py):
    os.makedirs(t["startup"], exist_ok=True)
    if IS_WIN:
        path = os.path.join(t["startup"], f"{APP}.cmd")
        write(path, f'@echo off\r\nstart "" "{py}" "{bar}"\r\n')
        return path
    if IS_MAC:
        path = os.path.join(t["startup"], f"{PLIST_LABEL}.plist")
        write(path, f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>{py}</string><string>{bar}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict>
</plist>
''')
        return path
    path = os.path.join(t["startup"], f"{APP}.desktop")
    shutil.copy2(os.path.join(SRC, "desktop", f"{APP}-autostart.desktop"), path)
    pin_exec(path, bar)
    return path


def uninstall(args):
    t = targets()
    bar = os.path.join(t["bin"], APP)
    print("==> stopping")
    if os.path.exists(bar):
        subprocess.run([sys.executable, bar, "--quit"], check=False)
        if not (IS_WIN or IS_MAC) and shutil.which("gsettings"):
            subprocess.run([sys.executable, bar, "--remove-hotkey"], check=False)

    print("==> removing")
    gone = [os.path.join(t["bin"], APP),
            os.path.join(t["bin"], "claude-context-probe"),
            os.path.join(t["desktop"], f"{APP}.cmd"),
            os.path.join(t["desktop"], "Claude Context Bar.command"),
            os.path.join(t["desktop"], f"{APP}.desktop"),
            os.path.join(t["startup"], f"{APP}.cmd"),
            os.path.join(t["startup"], f"{APP}.desktop"),
            os.path.join(t["startup"], f"{PLIST_LABEL}.plist")]
    if "apps" in t:
        gone.append(os.path.join(t["apps"], f"{APP}.desktop"))
    if "icons" in t:
        gone.append(os.path.join(t["icons"], f"{APP}.svg"))
    for p in gone:
        if os.path.exists(p):
            os.remove(p)
            print(f"    removed {p}")
    if os.path.isdir(t["share"]):
        shutil.rmtree(t["share"], ignore_errors=True)
        print(f"    removed {t['share']}")
    print("Done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Install the Claude Context Bar")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-autostart", dest="autostart", action="store_false")
    ap.add_argument("--no-hotkey", dest="hotkey", action="store_false")
    ap.add_argument("--no-desktop-icon", dest="desktop_icon",
                    action="store_false")
    ap.add_argument("--no-start", dest="start", action="store_false",
                    help="install without launching it (useful for testing)")
    a = ap.parse_args()
    (uninstall if a.uninstall else install)(a)
