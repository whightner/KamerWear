"""A deterministic stand-in for the pose model in Smart Fit tests.

`synthetic_pose()` draws a simple body silhouette (head, torso bands of known
widths, arms, two legs) and places the landmarks on it, so the real geometry
code can be checked with exact numbers. `FakePoseBackend` picks a scenario
from the colour of the uploaded photo and records what it received.
"""

import io
from dataclasses import dataclass, field

import numpy as np
import pytest
from PIL import Image

from app.fit import pose as pose_module
from app.fit.pose import PoseResult

WIDTH, HEIGHT = 600, 1000
TOP, FLOOR = 100, 900  # 800 px tall body


@dataclass
class Body:
    """Silhouette sizes in pixels (front widths, or side depths)."""

    chest: int = 170
    waist: int = 150
    hip: int = 180
    shoulder_joints: int = 160
    arms: str = "away"  # "away", "touching" or "none"
    leg_gap: bool = True
    side: bool = False
    top: int = TOP
    floor: int = FLOOR
    visibility: float = 0.95
    hide: list[int] = field(default_factory=list)  # landmarks to make invisible

    @property
    def body_px(self) -> int:
        return self.floor - self.top

    @property
    def shoulder_y(self) -> float:
        return self.top + 0.18 * self.body_px

    @property
    def hip_y(self) -> float:
        return self.shoulder_y + 0.30 * self.body_px

    @property
    def crotch_y(self) -> float:
        return self.hip_y + 0.04 * self.body_px


def synthetic_pose(body: Body, width: int = WIDTH, height: int = HEIGHT) -> PoseResult:
    cx = width / 2
    mask = np.zeros((height, width), dtype=np.float32)
    torso = body.hip_y - body.shoulder_y

    def fill(y0, y1, x0, x1):
        y0, y1 = max(0, int(round(y0))), min(height, int(round(y1)))
        x0, x1 = max(0, int(round(x0))), min(width, int(round(x1)))
        mask[y0:y1, x0:x1] = 1.0

    def band(y0, y1, w):
        fill(y0, y1, cx - w / 2, cx + w / 2)

    head_w = 0.4 * body.chest
    band(body.top, body.shoulder_y, head_w)
    band(body.shoulder_y, body.shoulder_y + 0.45 * torso, body.chest)
    band(body.shoulder_y + 0.45 * torso, body.shoulder_y + 0.85 * torso, body.waist)
    band(body.shoulder_y + 0.85 * torso, body.crotch_y, body.hip)
    leg_w = body.hip / 2 - (12 if body.leg_gap else 0)
    if body.leg_gap:
        fill(body.crotch_y, body.floor, cx - body.hip / 2, cx - body.hip / 2 + leg_w)
        fill(body.crotch_y, body.floor, cx + body.hip / 2 - leg_w, cx + body.hip / 2)
    else:
        band(body.crotch_y, body.floor, body.hip)

    arm_w = 40
    widest = max(body.chest, body.hip, body.waist)
    if body.arms == "away":
        arm_x = widest / 2 + 25 + arm_w / 2
    else:  # touching: the arm overlaps the torso edge
        arm_x = body.chest / 2 + arm_w / 2 - 10
    arm_bottom = body.hip_y + 0.12 * body.body_px
    if body.arms != "none" and not body.side:
        for sign in (-1, 1):
            x = cx + sign * arm_x
            fill(body.shoulder_y, arm_bottom, x - arm_w / 2, x + arm_w / 2)

    points = np.zeros((33, 3))
    points[:, 2] = body.visibility

    def put(index, x, y):
        points[index, 0], points[index, 1] = x, y

    half_sh = (10 if body.side else body.shoulder_joints) / 2
    put(0, cx + (head_w / 2 - 5 if body.side else 0), body.top + 0.06 * body.body_px)
    put(7, cx - 10, body.top + 0.05 * body.body_px)
    put(8, cx + 10, body.top + 0.05 * body.body_px)
    put(11, cx + half_sh, body.shoulder_y)
    put(12, cx - half_sh, body.shoulder_y)
    half_hip = (8 if body.side else 0.4 * body.hip) / 2
    put(23, cx + half_hip, body.hip_y)
    put(24, cx - half_hip, body.hip_y)
    if body.side or body.arms == "none":
        arm_points = [cx, cx]
    else:
        arm_points = [cx + arm_x, cx - arm_x]
    for (elbow, wrist, index), x in zip(((13, 15, 19), (14, 16, 20)), arm_points, strict=True):
        put(elbow, x, body.shoulder_y + 0.6 * torso)
        put(wrist, x, body.hip_y)
        put(index, x, body.hip_y + 0.05 * body.body_px)
    leg_x = (body.hip / 2 - leg_w / 2) if not body.side else 0
    for sign, (knee, ankle, heel, foot) in ((1, (25, 27, 29, 31)), (-1, (26, 28, 30, 32))):
        x = cx + sign * leg_x
        put(knee, x, (body.hip_y + body.floor) / 2)
        put(ankle, x, body.floor - 0.04 * body.body_px)
        put(heel, x, body.floor - 0.01 * body.body_px)
        put(foot, x, body.floor)
    if body.arms == "none" and not body.side:
        points[[13, 14, 15, 16, 19, 20], 2] = 0.1  # arms not detected
    for index in body.hide:
        points[index, 2] = 0.1
    return PoseResult(width=width, height=height, people=1, landmarks=points, mask=mask)


FRONT = Body()
SIDE = Body(chest=120, waist=110, hip=124, side=True)

# Upload colour -> scenario returned by the fake backend.
SCENARIOS: dict[tuple[int, int, int], object] = {
    (200, 60, 60): FRONT,
    (60, 200, 60): SIDE,
    (60, 60, 200): "nobody",
    (200, 200, 60): "two people",
    (200, 60, 200): Body(hide=[27, 28, 29, 30, 31, 32]),  # feet not visible
    (60, 200, 200): Body(arms="touching"),
    (120, 120, 120): FRONT,  # side slot sent a front view
    (90, 40, 10): "crash",
}


def photo_bytes(color=(200, 60, 60), size=(WIDTH, HEIGHT), fmt="JPEG", **save) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt, **save)
    return buffer.getvalue()


class FakePoseBackend:
    model_name = "fake-pose"

    def __init__(self) -> None:
        self.calls = 0
        self.received: list[Image.Image] = []

    def detect(self, image: Image.Image) -> PoseResult:
        self.calls += 1
        self.received.append(image)
        color = image.convert("RGB").getpixel((5, 5))
        # JPEG shifts colours slightly: match the nearest scenario.
        key = min(SCENARIOS, key=lambda c: sum((a - b) ** 2 for a, b in zip(c, color)))
        scenario = SCENARIOS[key]
        w, h = image.size
        if scenario == "nobody":
            return PoseResult(width=w, height=h, people=0)
        if scenario == "crash":
            raise RuntimeError("model exploded")
        if scenario == "two people":
            result = synthetic_pose(FRONT, w, h)
            result.people = 2
            return result
        return synthetic_pose(scenario, w, h)


@pytest.fixture
def fake_pose():
    backend = FakePoseBackend()
    pose_module.set_backend(backend)
    yield backend
    pose_module.set_backend(None)
