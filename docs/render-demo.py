#!/usr/bin/env python3
"""Render docs/demo.gif: the gauge filling from empty to full.

Frames come from the real GTK widgets, so the animation cannot drift from the
actual design. The GIF is written by the small encoder below rather than by
ffmpeg or Pillow, so this needs nothing beyond GTK.

    python3 docs/render-demo.py
"""
import os, sys, importlib.util
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 2                      # render at 2x so it is legible in a README
FRAME_MS = 70
BACKDROP = "#0F0F13"
PAD = 26


# ----------------------------------------------------------------- GIF89a
class BitPacker:
    """GIF packs LZW codes least-significant-bit first."""

    def __init__(self):
        self.out = bytearray()
        self.cur = self.nbits = 0

    def write(self, code, size):
        self.cur |= code << self.nbits
        self.nbits += size
        while self.nbits >= 8:
            self.out.append(self.cur & 0xFF)
            self.cur >>= 8
            self.nbits -= 8

    def flush(self):
        if self.nbits:
            self.out.append(self.cur & 0xFF)
            self.cur = self.nbits = 0


def lzw_encode(indices, min_code_size):
    clear, end = 1 << min_code_size, (1 << min_code_size) + 1

    def fresh():
        return {(i,): i for i in range(clear)}, end + 1, min_code_size + 1

    packer = BitPacker()
    table, next_code, code_size = fresh()
    packer.write(clear, code_size)

    prefix = ()
    for px in indices:
        nxt = prefix + (px,)
        if nxt in table:
            prefix = nxt
            continue
        packer.write(table[prefix], code_size)
        table[nxt] = next_code
        next_code += 1
        # The decoder builds its table one entry behind the encoder, because it
        # cannot complete an entry until it has seen the following code. So the
        # encoder must widen one entry later than its own table suggests, or
        # the two desync the first time the table grows past 512.
        if next_code == 4096:
            packer.write(clear, code_size)
            table, next_code, code_size = fresh()
        elif next_code == (1 << code_size) + 1 and code_size < 12:
            code_size += 1
        prefix = (px,)

    if prefix:
        packer.write(table[prefix], code_size)
    packer.write(end, code_size)
    packer.flush()
    return bytes(packer.out)


def sub_blocks(data):
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out.append(len(chunk))
        out += chunk
    out.append(0)
    return bytes(out)


def quantise(frames):
    """Median-cut to 256 colours.

    Uniform posterisation bands the antialiased edges badly, and a nearest-
    colour search per pixel is far too slow in Python. Unique colours are few,
    so the cut runs over those and each frame is then a dictionary lookup.
    """
    counts = {}
    for f in frames:
        for px in f:
            counts[px] = counts.get(px, 0) + 1
    colours = list(counts)

    boxes = [colours]
    while len(boxes) < 256:
        # split whichever box spans the most in a single channel
        target, channel, spread = None, 0, 0
        for b in boxes:
            if len(b) < 2:
                continue
            for c in range(3):
                lo = min(p[c] for p in b)
                hi = max(p[c] for p in b)
                if hi - lo > spread:
                    target, channel, spread = b, c, hi - lo
        if target is None:
            break
        target.sort(key=lambda p: p[channel])
        half = sum(counts[p] for p in target) / 2
        run, cut = 0, 1
        for i, p in enumerate(target):
            run += counts[p]
            if run >= half:
                cut = max(1, min(i, len(target) - 1))
                break
        boxes.remove(target)
        boxes += [target[:cut], target[cut:]]

    palette, lookup = [], {}
    for i, b in enumerate(boxes):
        total = sum(counts[p] for p in b) or 1
        palette.append(tuple(
            min(255, round(sum(p[c] * counts[p] for p in b) / total))
            for c in range(3)))
        for p in b:
            lookup[p] = i

    return palette, [[lookup[px] for px in f] for f in frames], len(colours)


def write_gif(path, width, height, palette, frames, delay_ms):
    size_bits = max(1, (len(palette) - 1).bit_length())
    table_len = 1 << size_bits
    min_code_size = max(2, size_bits)

    out = bytearray(b"GIF89a")
    out += width.to_bytes(2, "little") + height.to_bytes(2, "little")
    out += bytes([0x80 | ((size_bits - 1) & 7), 0, 0])
    for i in range(table_len):
        out += bytes(palette[i]) if i < len(palette) else b"\0\0\0"

    out += b"\x21\xFF\x0BNETSCAPE2.0\x03\x01" + (0).to_bytes(2, "little") + b"\0"

    for idx in frames:
        out += b"\x21\xF9\x04\x04" + (delay_ms // 10).to_bytes(2, "little")
        out += b"\x00\x00"
        out += b"\x2C" + (0).to_bytes(2, "little") * 2
        out += width.to_bytes(2, "little") + height.to_bytes(2, "little")
        out += b"\x00"
        out += bytes([min_code_size]) + sub_blocks(lzw_encode(idx, min_code_size))

    out += b"\x3B"
    with open(path, "wb") as fh:
        fh.write(out)
    return len(out)


# ------------------------------------------------------------- rendering
def main():
    # Resize before the module is asked for any CSS or widgets.
    os.environ["CLAUDE_BAR_W"] = str(150 * SCALE)
    os.environ["CLAUDE_BAR_H"] = str(26 * SCALE)
    loader = SourceFileLoader("contextbar", os.path.join(HERE, os.pardir, "bin",
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
    bar.apply_css(win.get_screen())
    extra = Gtk.CssProvider()
    extra.load_from_data(f"#demo-bg {{ background-color: {BACKDROP}; }}".encode())
    Gtk.StyleContext.add_provider_for_screen(
        win.get_screen(), extra, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    shell, fill, pct = bar.build_shell()
    shell.set_size_request(bar.WIDTH, bar.HEIGHT)
    row = Gtk.Box()
    row.set_halign(Gtk.Align.CENTER)
    row.pack_start(shell, False, False, 0)
    for m in ("top", "bottom", "start", "end"):
        getattr(row, f"set_margin_{m}")(PAD * SCALE)
    backdrop = Gtk.EventBox(name="demo-bg")
    backdrop.add(row)
    win.add(backdrop)
    win.show_all()

    steps = [2 + i * 2 for i in range(49)] + [98] * 8      # sweep, then hold
    frames, w, h = [], None, None
    for used in steps:
        left = 100 - used
        fill.set_size_request(max(3, int(bar.TRACK_W * used / 100.0)), bar.TRACK_H)
        ctx = fill.get_style_context()
        for c in ("ample", "tight", "low"):
            ctx.remove_class(c)
        ctx.add_class({bar.AMPLE: "ample", bar.TIGHT: "tight",
                       bar.LOW: "low"}[bar.accent(left)])
        pct.set_text(f"{used}%")
        while Gtk.events_pending():
            Gtk.main_iteration()
        pb = win.get_pixbuf()
        w, h = pb.get_width(), pb.get_height()
        data, stride, nch = pb.get_pixels(), pb.get_rowstride(), pb.get_n_channels()
        frames.append([(data[y * stride + x * nch],
                        data[y * stride + x * nch + 1],
                        data[y * stride + x * nch + 2])
                       for y in range(h) for x in range(w)])

    palette, indexed, uniques = quantise(frames)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "demo.gif")
    size = write_gif(out, w, h, palette, indexed, FRAME_MS)
    print(f"wrote {out}  {w}x{h}  {len(frames)} frames  "
          f"{len(palette)} of {uniques} colours  {size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
