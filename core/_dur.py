import re
import shutil
import subprocess
from pathlib import Path
from .exception import FileNotProvidedError, DurationDetectionError
from typing import Union


def checkDur(path: Union[str, Path]) -> float:
    """返回秒数。探测链：ffprobe -> imageio-ffmpeg -> mediainfo -> opencv。"""
    # deepseek写的。我不会写。
    p = Path(path)
    if not p.is_file():
        raise FileNotProvidedError(f"file not found: {p}")

    def _via_ffprobe(pa: Path):
        if shutil.which('ffprobe') is None:
            return None
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                 "default=noprint_wrappers=1:nokey=1",
                 str(pa)],
                capture_output=True, text=True, timeout=30, )
            out = r.stdout.strip()
            return float(out) if out else None
        except Exception:
            return None

    def _via_imageio_ffmpeg(pa: Path):
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            r = subprocess.run([exe, "-i", str(pa)], capture_output=True, text=True, timeout=30, encoding="utf-8")
            # 从stderr抓: Duration: 00:01:23.45,
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
            if not m:
                return None
            h, mm, ss = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mm * 60 + ss
        except Exception:
            return None

    def _via_mediainfo(pa: Path):
        try:
            from pymediainfo import MediaInfo
            info = MediaInfo.parse(str(pa))
            for t in info.tracks:
                if t.track_type == "Video" and t.duration:
                    return t.duration / 1000.0
        except Exception:
            return None

    def _via_opencv(pa: Path):
        try:
            import cv2
            cap = cv2.VideoCapture(str(pa))
            fps = cap.get(cv2.CAP_PROP_FPS)
            n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps and n:
                return n / fps
        except Exception:
            return None

    for fn in (_via_ffprobe, _via_imageio_ffmpeg, _via_mediainfo, _via_opencv):
        val = fn(p)
        if val and val > 0:
            return val

    raise DurationDetectionError(
        "无法探测视频时长。请安装ffmpeg 或 pip install ohutils[video] 或 pip install pymediainfo 或 调用时显式传入duration")


def checkDurI(path: Union[str, Path]) -> int:
    """返回整数秒。"""
    return max(1, round(checkDur(path)))
