"""Photograph a built .FCStd in a running FreeCAD GUI instance.

    python render.py <doc.FCStd> <out-dir> [port]

FreeCADCmd has no GUI and cannot take a picture, so this drives a real window
over the MCP addon's XML-RPC port. Find the port in
%APPDATA%/FreeCAD/mcp_instances - never assume 9875.
"""

from __future__ import annotations

import base64
import os
import socket
import sys
import xmlrpc.client

socket.setdefaulttimeout(120)

# Shown parts solid, machine context ghosted behind them.
COLOURS: dict[str, tuple[float, float, float]] = {
    "Pulley_40T": (0.93, 0.45, 0.13),
    "Pulley_20T": (0.93, 0.45, 0.13),
    "Bracket": (0.23, 0.47, 0.76),
    "ScrewEnd_REF": (0.62, 0.64, 0.67),
    "NEMA23_REF": (0.26, 0.27, 0.29),
    "EndPlate_REF": (0.85, 0.27, 0.10),
}

SETUP = r'''
import FreeCAD as App, FreeCADGui as Gui
for d in list(App.listDocuments()):
    App.closeDocument(d)
doc = App.openDocument(r"%(doc)s")

p = App.ParamGet("User parameter:BaseApp/Preferences/View")
p.SetBool("Simple", True)
p.SetBool("UseBackgroundColorMid", False)
for k in ("BackgroundColor", "BackgroundColor2", "BackgroundColor3"):
    p.SetUnsigned(k, 0xffffffff)
p.SetBool("ShowAxisCross", False)

for n, c in %(cols)r.items():
    o = doc.getObject(n)
    if o is None:
        continue
    o.ViewObject.ShapeColor = c
    o.ViewObject.Transparency = 0
    o.ViewObject.Visibility = True
    if "Flat Lines" in o.ViewObject.listDisplayModes():
        o.ViewObject.DisplayMode = "Flat Lines"
Gui.Selection.clearSelection()
Gui.activeDocument().activeView().setAnimationEnabled(False)
print("setup ok")
'''


class Renderer:
    def __init__(self, doc: str, out: str, port: int) -> None:
        self.doc, self.out = doc, out
        self.srv = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{port}", allow_none=True)
        os.makedirs(out, exist_ok=True)

    def run(self, code: str) -> dict:
        r = self.srv.execute_code(code)
        if not r.get("success"):
            raise SystemExit(f"FreeCAD: {r}")
        return r

    def setup(self) -> None:
        self.run(SETUP % {"doc": self.doc, "cols": COLOURS})

    def show(self, names: list[str], ghost: tuple[str, ...] = ()) -> None:
        lines = ["import FreeCAD as App, FreeCADGui as Gui",
                 "doc = App.ActiveDocument", "Gui.Selection.clearSelection()"]
        for n in COLOURS:
            lines.append(f"o = doc.getObject({n!r})")
            lines.append(f"if o: o.ViewObject.Visibility = {n in names or n in ghost!r}")
            lines.append(f"if o: o.ViewObject.Transparency = {78 if n in ghost else 0}")
        self.run("\n".join(lines))

    def shot(self, name: str, view: str = "Isometric", w: int = 2000, h: int = 1500) -> None:
        png = self.srv.get_active_screenshot(view, w, h, None)
        if not png:
            raise SystemExit("no screenshot for " + name)
        path = os.path.join(self.out, name + ".png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(png))
        _trim(path)
        print(f"  {name + '.png':<24} {os.path.getsize(path):7d} bytes")


def _trim(path: str, pad: int = 36) -> None:
    """Crop the white margin fitAll leaves, then re-pad evenly."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return
    im = Image.open(path).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if not box:
        return
    im = im.crop(box)
    out = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255))
    out.paste(im, (pad, pad))
    out.save(path)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    doc, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    port = int(sys.argv[3]) if len(sys.argv) > 3 else int(os.environ.get("WEN_FC_PORT", "9879"))

    r = Renderer(doc, out, port)
    r.setup()
    print("rendering...")
    machine = ("ScrewEnd_REF", "NEMA23_REF", "EndPlate_REF")
    r.show(["Pulley_40T", "Pulley_20T", "Bracket"], ghost=machine)
    r.shot("x-drive-assembly")
    r.shot("x-drive-front", view="Front")
    r.show(["Bracket"])
    r.shot("x-drive-bracket")
    r.show(["Pulley_40T"])
    r.shot("x-drive-pulley-40t")
    r.show(["Pulley_40T", "ScrewEnd_REF"])
    r.shot("x-drive-pulley-on-screw", view="Front")
    r.show(["Pulley_40T", "Pulley_20T", "Bracket"], ghost=machine)


main()
