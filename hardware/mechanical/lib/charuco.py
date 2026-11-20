"""Measure a machine feature off a photograph, without perspective error.

Tape a printed ChArUco board flat on the surface being measured, photograph
it, and this recovers the board-to-image homography and rectifies the photo
into a metric, square-on view. After that a pixel IS a millimetre and
anything coplanar with the board can be measured directly.

This exists because four rounds of tape measurements disagreed with each
other, and because reading a dimension off an uncalibrated photo got the
X bracket wrong twice - once by 25 mm, once by deleting a boss that was
really there.

    python charuco.py board  [out.png] [hole_mm] [plate|small]
    python charuco.py rectify photo.jpg [out.png]
    python charuco.py probe   photo.jpg X1 Y1 X2 Y2    distance between two
                                                       points, in mm

Needs `opencv-contrib-python` and `numpy`: dev-only, never on the Pi.
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

# Two sizes, because the surface decides. The board must be COPLANAR with
# what it measures, so it has to fit on the flat part of that surface - a
# board held nearby in a different plane returns confident nonsense.
#
#   plate  110 x 40 - the whole end plate, boss poking through a cut hole
#   small   42 x 24 - the flat strip beside the boss, 40 x 45 of clear metal
#
# detect() tries every preset and keeps the best, so a photo can never be
# read against the wrong board definition. Getting that wrong would not
# fail - it would silently scale every measurement.
BOARDS = {
    "plate": dict(squares=(11, 4), square_mm=10.0, marker_mm=7.5),
    "small": dict(squares=(7, 4), square_mm=6.0, marker_mm=4.5),
}
DEFAULT_BOARD = "plate"
DICT = cv2.aruco.DICT_4X4_50
PRINT_DPI = 600
MARGIN_MM = 8.0


def _spec(name: str) -> dict:
    if name not in BOARDS:
        raise SystemExit(f"unknown board {name!r}; have {', '.join(BOARDS)}")
    return BOARDS[name]

def _board(name: str = DEFAULT_BOARD):
    b = _spec(name)
    return cv2.aruco.CharucoBoard(
        b["squares"], b["square_mm"], b["marker_mm"],
        cv2.aruco.getPredefinedDictionary(DICT),
    )


def _mm_to_px(mm: float, dpi: int = PRINT_DPI) -> int:
    return int(round(mm / 25.4 * dpi))


def make_board(path: str = "charuco_board.png", dpi: int = PRINT_DPI,
               hole_mm: float = 0.0, name: str = DEFAULT_BOARD) -> str:
    """Render the board at exact scale, with its own proof of scale on it."""
    b = _spec(name)
    w_mm = b["squares"][0] * b["square_mm"]
    h_mm = b["squares"][1] * b["square_mm"]
    img = _board(name).generateImage((_mm_to_px(w_mm, dpi), _mm_to_px(h_mm, dpi)))

    # A boss standing proud of the surface stops paper lying flat on it, and a
    # board that is not coplanar with what it measures is worse than no board:
    # parallel-but-offset by 40 mm at arm's length is a ~10% scale error. So
    # punch a hole and let the boss through.
    if hole_mm:
        cx, cy = img.shape[1] // 2, img.shape[0] // 2
        r = _mm_to_px(hole_mm / 2.0, dpi)
        cv2.circle(img, (cx, cy), r, 255, -1)
        # dashed cut line, drawn just inside so the cut removes it
        for a in range(0, 360, 8):
            t0, t1 = np.radians(a), np.radians(a + 4)
            cv2.ellipse(img, (cx, cy), (r, r), 0, np.degrees(t0), np.degrees(t1),
                        0, max(2, dpi // 400))

    m = _mm_to_px(MARGIN_MM, dpi)
    canvas = np.full((img.shape[0] + 3 * m, img.shape[1] + 2 * m), 255, np.uint8)
    canvas[m:m + img.shape[0], m:m + img.shape[1]] = img

    # A 100 mm bar with end ticks: if this does not measure 100 mm on the
    # paper, the print was scaled and every number downstream is wrong.
    y = m + img.shape[0] + m
    x0 = m
    bar_mm = 100.0 if w_mm >= 100.0 else 40.0
    x1 = x0 + _mm_to_px(bar_mm, dpi)
    cv2.line(canvas, (x0, y), (x1, y), 0, max(2, dpi // 300))
    for x in (x0, x1):
        cv2.line(canvas, (x, y - _mm_to_px(2, dpi)), (x, y + _mm_to_px(2, dpi)),
                 0, max(2, dpi // 300))
    cv2.putText(canvas, f"{bar_mm:.0f} mm - PRINT AT 100%, NO FIT-TO-PAGE",
                (x1 + _mm_to_px(4, dpi), y + _mm_to_px(2, dpi)),
                cv2.FONT_HERSHEY_SIMPLEX, dpi / 600.0, 0, max(1, dpi // 500))
    cv2.imwrite(path, canvas)
    return path


def detect(image_path: str, name: str | None = None):
    """Board corners found in a photo, plus the homography to board mm.

    With no board named, every preset is tried and the one yielding the most
    corners wins. Reading a photo against the wrong board definition would
    not fail - it would silently scale every measurement - so the choice is
    not left to whoever types the command.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"cannot read {image_path}")
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    best = None
    for candidate in ([name] if name else list(BOARDS)):
        board = _board(candidate)
        corners, ids, _, _ = cv2.aruco.CharucoDetector(board).detectBoard(grey)
        if ids is None or len(ids) < 6:
            continue
        obj = board.getChessboardCorners()[ids.flatten()][:, :2].astype(np.float32)
        pts = corners.reshape(-1, 2).astype(np.float32)
        H, _ = cv2.findHomography(pts, obj, cv2.RANSAC, 2.0)
        if H is None:
            continue
        err = _reprojection_error(H, pts, obj)
        if best is None or len(ids) > best[3]:
            best = (candidate, H, err, len(ids))

    if best is None:
        raise SystemExit(
            "no board found with 6+ corners. Get it flatter, closer, or better lit."
        )
    chosen, H, err, n = best
    return img, H, n, err, chosen

def _reprojection_error(H, img_pts, obj) -> float:
    proj = cv2.perspectiveTransform(img_pts.reshape(-1, 1, 2), H).reshape(-1, 2)
    return float(np.sqrt(((proj - obj) ** 2).sum(axis=1)).mean())


def to_mm(H, x: float, y: float) -> tuple[float, float]:
    p = cv2.perspectiveTransform(np.array([[[x, y]]], np.float32), H)
    return float(p[0, 0, 0]), float(p[0, 0, 1])


def rectify(image_path: str, out: str = "rectified.png", px_per_mm: float = 6.0,
            pad_mm: float = 40.0) -> str:
    """Write a square-on, metric view: one pixel is 1/px_per_mm of a mm."""
    img, H, n, err, name = detect(image_path)
    S = np.array([[px_per_mm, 0, pad_mm * px_per_mm],
                  [0, px_per_mm, pad_mm * px_per_mm],
                  [0, 0, 1]], np.float64)
    b = _spec(name)
    w = int((b["squares"][0] * b["square_mm"] + 2 * pad_mm) * px_per_mm)
    h = int((b["squares"][1] * b["square_mm"] + 2 * pad_mm) * px_per_mm)
    warped = cv2.warpPerspective(img, S @ H, (w, h))

    # 10 mm grid, so the rectified image carries its own ruler
    for mm in range(0, int(w / px_per_mm), 10):
        x = int(mm * px_per_mm)
        cv2.line(warped, (x, 0), (x, h), (0, 255, 0), 1)
    for mm in range(0, int(h / px_per_mm), 10):
        y = int(mm * px_per_mm)
        cv2.line(warped, (0, y), (w, y), (0, 255, 0), 1)
    cv2.imwrite(out, warped)
    print(f"board {name!r}: {n} corners, reprojection error {err:.3f} mm")
    print(f"board origin is at ({pad_mm:.0f}, {pad_mm:.0f}) mm; grid is 10 mm")
    print(f"wrote {out}  ({w} x {h} px at {px_per_mm} px/mm)")
    return out


def probe(image_path: str, x1, y1, x2, y2) -> float:
    img, H, n, err, name = detect(image_path)
    a = to_mm(H, float(x1), float(y1))
    b = to_mm(H, float(x2), float(y2))
    d = float(np.hypot(b[0] - a[0], b[1] - a[1]))
    print(f"board {name!r}: {n} corners, reprojection error {err:.3f} mm")
    print(f"({x1},{y1}) -> {a[0]:.2f}, {a[1]:.2f} mm")
    print(f"({x2},{y2}) -> {b[0]:.2f}, {b[1]:.2f} mm")
    print(f"distance {d:.2f} mm")
    return d


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "board":
        path = rest[0] if rest else "charuco_board.png"
        hole = float(rest[1]) if len(rest) > 1 else 0.0
        preset = rest[2] if len(rest) > 2 else DEFAULT_BOARD
        print("wrote", make_board(path, hole_mm=hole, name=preset))
    elif cmd == "rectify":
        rectify(rest[0], *(rest[1:2] or ["rectified.png"]))
    elif cmd == "probe":
        probe(rest[0], *rest[1:5])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
