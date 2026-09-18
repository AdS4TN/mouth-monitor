from __future__ import annotations

import os
from typing import Any


def _cv2() -> Any:
    import cv2

    return cv2


def open_camera(index: int, width: int = 640, height: int = 480) -> Any:
    cv2 = _cv2()
    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    capture = cv2.VideoCapture(index, backend)
    if not capture.isOpened():
        capture.release()
        capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"无法打开摄像头 {index}，请检查权限或占用情况")

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ok, _ = capture.read()
    if not ok:
        capture.release()
        raise RuntimeError(f"摄像头 {index} 已打开，但无法读取画面")
    return capture


def scan_cameras(max_index: int = 5) -> list[dict[str, int | str]]:
    cameras: list[dict[str, int | str]] = []
    for index in range(max_index + 1):
        try:
            capture = open_camera(index)
        except RuntimeError:
            continue
        else:
            capture.release()
            cameras.append({"index": index, "label": f"摄像头 {index}"})
    return cameras
