"""Measure a machine feature off a photograph, without perspective error.

Tape a printed ChArUco board flat on the surface being measured, photograph
it, and this recovers the board-to-image homography and rectifies the photo
into a metric, square-on view. After that a pixel IS a millimetre and
anything coplanar with the board can be measured directly.

This exists because four rounds of tape measurements disagreed with each
other, and because reading a dimension off an uncalibrated photo got the
X bracket wrong twice - once by 25 mm, once by deleting a boss that was
really there.

    python charuco.py board  [out.png]        print this at 100%, no scaling
    python charuco.py rectify photo.jpg [out.png]
    python charuco.py probe   photo.jpg X1 Y1 X2 Y2    distance between two
                                                       points, in mm

Needs `opencv-contrib-python` and `numpy`: dev-only, never on the Pi.
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

# 10 mm squares over 11 x 4 fits the 115 x 45 X-axis end plate with room for
# the boss to cover the middle - ChArUco reads whatever corners it can see, so
# an occluded centre costs nothing.
SQUARES_X, SQUARES_Y = 11, 4
SQUARE_MM = 10.0
MARKER_MM = 7.5
DICT = cv2.aruco.DICT_4X4_50
PRINT_DPI = 600
MARGIN_MM = 8.0


def _board():
    return cv2.aruco.CharucoBoard(
        (SQUARES_X, SQUARES_Y), SQUARE_MM, MARKER_MM,
        cv2.aruco.getPredefinedDictionary(DICT),
    )


def _mm_to_px(mm: float, dpi: int = PRINT_DPI) -> int:
    return int(round(mm / 25.4 * dpi))


def make_board(path: str = "charuco_board.png", dpi: int = PRINT_DPI) -> str:
    """Render the board at exact scale, with its own proof of scale on it."""
    w_mm = SQUARES_X * SQUARE_MM
    h_mm = SQUARES_Y * SQUARE_MM
    img = _board().generateImage((_mm_to_px(w_mm, dpi), _mm_to_px(h_mm, dpi)))

    m = _mm_to_px(MARGIN_MM, dpi)
    canvas = np.full((img.shape[0] + 3 * m, img.shape[1] + 2 * m), 255, np.uint8)
    canvas[m:m + img.shape[0], m:m + img.shape[1]] = img

    # A 100 mm bar with end ticks: if this does not measure 100 mm on the
    # paper, the print was scaled and every number downstream is wrong.
    y = m + img.shape[0] + m
    x0 = m
    x1 = x0 + _mm_to_px(100.0, dpi)
    cv2.line(canvas, (x0, y), (x1, y), 0, max(2, dpi // 300))
    for x in (x0, x1):
        cv2.line(canvas, (x, y - _mm_to_px(2, dpi)), (x, y + _mm_to_px(2, dpi)),
                 0, max(2, dpi // 300))
    cv2.putText(canvas, "100 mm - PRINT AT 100%, NO FIT-TO-PAGE",
                (x1 + _mm_to_px(4, dpi), y + _mm_to_px(2, dpi)),
                cv2.FONT_HERSHEY_SIMPLEX, dpi / 600.0, 0, max(1, dpi // 500))
    cv2.imwrite(path, canvas)
    return path


def detect(image_path: str):
    """Board corners found in a photo, plus the homography to board mm."""
    img = cv2.imread(image_path)
    if img is None:
        raise SystemExit(f"cannot read {image_path}")
    board = _board()
    detector = cv2.aruco.CharucoDetector(board)
    corners, ids, _, _ = detector.detectBoard(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    if ids is None or len(ids) < 6:
        raise SystemExit(
            f"found {0 if ids is None else len(ids)} board corners, need 6+. "
            "Get the board flatter, closer, or better lit."
        )
    obj = board.getChessboardCorners()[ids.flatten()][:, :2].astype(np.float32)
    img_pts = corners.reshape(-1, 2).astype(np.float32)
    H, mask = cv2.findHomography(img_pts, obj, cv2.RANSAC, 2.0)
    if H is None:
        raise SystemExit("could not fit a homography to those corners")
    err = _reprojection_error(H, img_pts, obj)
    return img, H, len(ids), err


def _reprojection_error(H, img_pts, obj) -> float:
    proj = cv2.perspectiveTransform(img_pts.reshape(-1, 1, 2), H).reshape(-1, 2)
    return float(np.sqrt(((proj - obj) ** 2).sum(axis=1)).mean())


def to_mm(H, x: float, y: float) -> tuple[float, float]:
    p = cv2.perspectiveTransform(np.array([[[x, y]]], np.float32), H)
    return float(p[0, 0, 0]), float(p[0, 0, 1])


def rectify(image_path: str, out: str = "rectified.png", px_per_mm: float = 6.0,
            pad_mm: float = 40.0) -> str:
    """Write a square-on, metric view: one pixel is 1/px_per_mm of a mm."""
    img, H, n, err = detect(image_path)
    S = np.array([[px_per_mm, 0, pad_mm * px_per_mm],
                  [0, px_per_mm, pad_mm * px_per_mm],
                  [0, 0, 1]], np.float64)
    w = int((SQUARES_X * SQUARE_MM + 2 * pad_mm) * px_per_mm)
    h = int((SQUARES_Y * SQUARE_MM + 2 * pad_mm) * px_per_mm)
    warped = cv2.warpPerspective(img, S @ H, (w, h))

    # 10 mm grid, so the rectified image carries its own ruler
    for mm in range(0, int(w / px_per_mm), 10):
        x = int(mm * px_per_mm)
        cv2.line(warped, (x, 0), (x, h), (0, 255, 0), 1)
    for mm in range(0, int(h / px_per_mm), 10):
        y = int(mm * px_per_mm)
        cv2.line(warped, (0, y), (w, y), (0, 255, 0), 1)
    cv2.imwrite(out, warped)
    print(f"{n} corners, reprojection error {err:.3f} mm")
    print(f"board origin is at ({pad_mm:.0f}, {pad_mm:.0f}) mm; grid is 10 mm")
    print(f"wrote {out}  ({w} x {h} px at {px_per_mm} px/mm)")
    return out


def probe(image_path: str, x1, y1, x2, y2) -> float:
    img, H, n, err = detect(image_path)
    a = to_mm(H, float(x1), float(y1))
    b = to_mm(H, float(x2), float(y2))
    d = float(np.hypot(b[0] - a[0], b[1] - a[1]))
    print(f"{n} corners, reprojection error {err:.3f} mm")
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
        print("wrote", make_board(*(rest[:1] or ["charuco_board.png"])))
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
