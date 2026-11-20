"""Photogrammetry: a measurement off a photo must agree with the real board.

This is derived arithmetic with a right answer, so it gets a test. It exists
because reading dimensions off uncalibrated photographs got the X bracket
wrong twice - once by 25 mm, and once by deleting a boss that was really
there. A number that comes out of a picture now has to prove itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2", reason="opencv-contrib-python is a dev-only extra")
np = pytest.importorskip("numpy")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "hardware" / "mechanical" / "lib"))
import charuco  # noqa: E402


@pytest.fixture(scope="module")
def oblique_photo(tmp_path_factory):
    """The board, rendered then warped as if photographed off-axis."""
    out = tmp_path_factory.mktemp("charuco")
    board_png = charuco.make_board(str(out / "board.png"))
    src = cv2.imread(board_png)
    h, w = src.shape[:2]
    quad = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    skewed = np.float32([[120, 60], [w - 40, 180], [w - 200, h - 40], [60, h - 150]])
    warped = cv2.warpPerspective(src, cv2.getPerspectiveTransform(quad, skewed),
                                 (w, h), borderValue=(255, 255, 255))
    # down to a phone-ish resolution, so the test is not flattered by detail
    warped = cv2.resize(warped, (1512, int(1512 * h / w)))
    path = str(out / "photo.png")
    cv2.imwrite(path, warped)
    return path


def _corners_in_mm(path):
    img, H, n, err, name = charuco.detect(path)
    board = charuco._board(name)
    detector = cv2.aruco.CharucoDetector(board)
    found, ids, _, _ = detector.detectBoard(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    measured = cv2.perspectiveTransform(found.reshape(-1, 1, 2), H).reshape(-1, 2)
    truth = board.getChessboardCorners()[ids.flatten()][:, :2]
    return measured, truth, err


class TestMeasurementIsTrue:
    def test_every_corner_lands_within_a_tenth_of_a_millimetre(self, oblique_photo):
        measured, truth, _ = _corners_in_mm(oblique_photo)
        worst = float(np.abs(measured - truth).max())
        assert worst < 0.1, f"worst corner is out by {worst:.3f} mm"

    def test_a_span_measures_its_true_length(self, oblique_photo):
        """The error that matters is over a distance, not at a point."""
        measured, truth, _ = _corners_in_mm(oblique_photo)
        i, j = 0, len(truth) - 1
        true_mm = float(np.hypot(*(truth[j] - truth[i])))
        got_mm = float(np.hypot(*(measured[j] - measured[i])))
        assert true_mm > 50, "pick corners far enough apart to be a real test"
        assert abs(got_mm - true_mm) < 0.1

    def test_reprojection_error_is_reported_and_small(self, oblique_photo):
        """A big residual means the board was not flat, and the mm are a lie."""
        _, _, err = _corners_in_mm(oblique_photo)
        assert err < 0.1


class TestItRefusesRatherThanGuesses:
    def test_a_photo_with_no_board_is_an_error_not_a_number(self, tmp_path):
        blank = tmp_path / "blank.png"
        cv2.imwrite(str(blank), np.full((600, 800, 3), 255, np.uint8))
        with pytest.raises(SystemExit, match="no board found"):
            charuco.detect(str(blank))

    def test_a_missing_file_is_an_error(self, tmp_path):
        with pytest.raises(SystemExit, match="cannot read"):
            charuco.detect(str(tmp_path / "nope.png"))

class TestOcclusionDoesNotCorruptScale:
    """A boss standing proud stops paper lying flat, so the board gets a hole

    cut in it and the boss pokes through. The middle of the board is then
    missing. That must cost detections, not accuracy - a board that is not
    coplanar with what it measures is far worse than one with a hole in it.
    """

    @pytest.fixture(scope="class")
    def holed_photo(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("holed")
        png = charuco.make_board(str(out / "holed.png"), hole_mm=46.0)
        src = cv2.imread(png)
        h, w = src.shape[:2]
        quad = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        skew = np.float32([[120, 60], [w - 40, 180], [w - 200, h - 40], [60, h - 150]])
        warped = cv2.warpPerspective(src, cv2.getPerspectiveTransform(quad, skew),
                                     (w, h), borderValue=(255, 255, 255))
        warped = cv2.resize(warped, (1512, int(1512 * h / w)))
        path = str(out / "photo.png")
        cv2.imwrite(path, warped)
        return path

    def test_a_46mm_hole_still_leaves_enough_corners(self, holed_photo):
        _, _, n, _, _ = charuco.detect(holed_photo)
        assert n >= 10

    def test_and_the_millimetres_are_still_true(self, holed_photo):
        measured, truth, _ = _corners_in_mm(holed_photo)
        assert float(np.abs(measured - truth).max()) < 0.1

class TestItIdentifiesWhichBoardItIsLookingAt:
    """Reading a photo against the wrong board definition does not fail.

    It silently scales every measurement by the ratio of the square sizes,
    which is the worst kind of wrong: plausible and invisible. So the board
    identifies itself from the photo rather than being asserted by whoever
    typed the command.
    """

    @pytest.mark.parametrize("name", sorted(charuco.BOARDS))
    def test_each_preset_is_recognised_from_its_own_photo(self, name, tmp_path):
        png = charuco.make_board(str(tmp_path / f"{name}.png"), name=name)
        src = cv2.imread(png)
        h, w = src.shape[:2]
        quad = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        skew = np.float32([[90, 50], [w - 30, 140], [w - 150, h - 30], [50, h - 110]])
        warped = cv2.warpPerspective(src, cv2.getPerspectiveTransform(quad, skew),
                                     (w, h), borderValue=(255, 255, 255))
        warped = cv2.resize(warped, (1512, int(1512 * h / w)))
        path = str(tmp_path / "photo.png")
        cv2.imwrite(path, warped)
        _, _, _, _, chosen = charuco.detect(path)
        assert chosen == name

    def test_the_small_board_still_measures_true(self, tmp_path):
        png = charuco.make_board(str(tmp_path / "small.png"), name="small")
        src = cv2.imread(png)
        h, w = src.shape[:2]
        quad = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        skew = np.float32([[90, 50], [w - 30, 140], [w - 150, h - 30], [50, h - 110]])
        warped = cv2.warpPerspective(src, cv2.getPerspectiveTransform(quad, skew),
                                     (w, h), borderValue=(255, 255, 255))
        warped = cv2.resize(warped, (1512, int(1512 * h / w)))
        path = str(tmp_path / "photo.png")
        cv2.imwrite(path, warped)
        measured, truth, _ = _corners_in_mm(path)
        assert float(np.abs(measured - truth).max()) < 0.1
