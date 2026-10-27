#
# The Python Imaging Library.
# $Id$
#
# XBM File handling
#
# History:
# 1995-09-08 fl   Created
# 1996-11-01 fl   Added save support
# 1997-07-07 fl   Made header parser more tolerant
# 1997-07-22 fl   Fixed yet another parser bug
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.4)
# 2001-05-13 fl   Added hotspot handling (based on code from Bernhard Herzog)
# 2004-02-24 fl   Allow some whitespace before first #define
#
# Copyright (c) 1997-2004 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import re
from typing import IO

from . import Image, ImageFile

# XBM header
xbm_head = re.compile(
    rb"\s*#define[ \t]+.*_width[ \t]+(?P<width>[0-9]+)[\r\n]+"
    b"#define[ \t]+.*_height[ \t]+(?P<height>[0-9]+)[\r\n]+"
    b"(?P<hotspot>"
    b"#define[ \t]+[^_]*_x_hot[ \t]+(?P<xhot>[0-9]+)[\r\n]+"
    b"#define[ \t]+[^_]*_y_hot[ \t]+(?P<yhot>[0-9]+)[\r\n]+"
    b")?"
    rb"[\000-\377]*_bits\[]"
)


# One terminated header line, and the "#define" lines xbm_head expects, in order
_line = re.compile(rb"([^\r\n]*)[\r\n]+")
_define = re.compile(rb"#define[ \t]+(.*)")
_size_define = {
    name: re.compile(rb".*_" + name + rb"[ \t]+([0-9]+)")
    for name in (b"width", b"height")
}
_hotspot_define = {
    name: re.compile(rb"[^_]*_" + name + rb"[ \t]+([0-9]+)")
    for name in (b"x_hot", b"y_hot")
}


def _match_define(data: bytes, pos: int, value: re.Pattern[bytes]) -> tuple[int, int]:
    """
    Match one terminated "#define <name> <number>" line at pos, returning the
    number and the position after the line's newlines, or (-1, pos) if it does
    not match.
    """
    line = _line.match(data, pos)
    if line:
        define = _define.fullmatch(line.group(1))
        if define:
            number = value.fullmatch(define.group(1).lstrip(b" \t"))
            if number:
                return int(number.group(1)), line.end()
    return -1, pos


def _parse_header(
    data: bytes,
) -> tuple[int, int, tuple[int, int] | None, int] | None:
    """
    Accept the same headers as xbm_head, one line at a time, so that the
    overlapping quantifiers in xbm_head cannot backtrack across the whole header.
    """
    pos = len(data) - len(data.lstrip())
    width, pos = _match_define(data, pos, _size_define[b"width"])
    if width < 0:
        return None
    height, pos = _match_define(data, pos, _size_define[b"height"])
    if height < 0:
        return None

    hotspot = None
    x_hot, hot_pos = _match_define(data, pos, _hotspot_define[b"x_hot"])
    if x_hot >= 0:
        y_hot, hot_pos = _match_define(data, hot_pos, _hotspot_define[b"y_hot"])
        if y_hot >= 0:
            hotspot = x_hot, y_hot
            pos = hot_pos

    bits = data.rfind(b"_bits[]", pos)
    if bits < 0:
        return None
    return width, height, hotspot, bits + len(b"_bits[]")


def _accept(prefix: bytes) -> bool:
    return prefix.lstrip().startswith(b"#define")


##
# Image plugin for X11 bitmaps.


class XbmImageFile(ImageFile.ImageFile):
    format = "XBM"
    format_description = "X11 Bitmap"

    def _open(self) -> None:
        assert self.fp is not None

        header = _parse_header(self.fp.read(512))

        if not header:
            msg = "not a XBM file"
            raise SyntaxError(msg)

        xsize, ysize, hotspot, offset = header

        if hotspot:
            self.info["hotspot"] = hotspot

        self._mode = "1"
        self._size = xsize, ysize

        self.tile = [ImageFile._Tile("xbm", (0, 0) + self.size, offset)]


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode != "1":
        msg = f"cannot write mode {im.mode} as XBM"
        raise OSError(msg)

    fp.write(f"#define im_width {im.size[0]}\n".encode("ascii"))
    fp.write(f"#define im_height {im.size[1]}\n".encode("ascii"))

    hotspot = im.encoderinfo.get("hotspot")
    if hotspot:
        fp.write(f"#define im_x_hot {hotspot[0]}\n".encode("ascii"))
        fp.write(f"#define im_y_hot {hotspot[1]}\n".encode("ascii"))

    fp.write(b"static char im_bits[] = {\n")

    ImageFile._save(im, fp, [ImageFile._Tile("xbm", (0, 0) + im.size)])

    fp.write(b"};\n")


Image.register_open(XbmImageFile.format, XbmImageFile, _accept)
Image.register_save(XbmImageFile.format, _save)

Image.register_extension(XbmImageFile.format, ".xbm")

Image.register_mime(XbmImageFile.format, "image/xbm")
