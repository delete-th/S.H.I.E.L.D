"""
CCTV Feed Handler - OpenCV-based frame extractor.

Supports three sources:
  - "webcam"  : live webcam feed (best for demo)
  - "file"    : local mp4 video file
  - "rtsp"    : real CCTV stream (production)

Usage:
  handler = CCTVHandler(source="webcam")
  async for frame_data in handler.stream_frames():
      # frame_data is a dict with camera_id, timestamp, jpeg bytes, base64
"""
import cv2
import base64
import asyncio
from datetime import datetime
from typing import AsyncGenerator


class CCTVHandler:
    def __init__(
        self,
        source: str = "webcam",       # "webcam" | "file" | "rtsp"
        camera_id: str = "CAM-001",
        file_path: str = "app/data/mock_cctv.mp4",
        rtsp_url: str = None,
        frame_interval: float = 0.5,  # extract a frame every 0.5 seconds
        max_frames: int = None,        # None = stream indefinitely
    ):
        self.source = source
        self.camera_id = camera_id
        self.file_path = file_path
        self.rtsp_url = rtsp_url
        self.frame_interval = frame_interval
        self.max_frames = max_frames
        self._running = False

    def _get_capture(self) -> cv2.VideoCapture:
        """Open the correct video source."""
        if self.source == "webcam":
            cap = cv2.VideoCapture(0)  # 0 = default webcam
        elif self.source == "file":
            cap = cv2.VideoCapture(self.file_path)
        elif self.source == "rtsp":
            cap = cv2.VideoCapture(self.rtsp_url)
        else:
            raise ValueError(f"Unknown source: {self.source}")

        if not cap.isOpened():
            raise RuntimeError(f"[CCTV] Could not open source: {self.source}")

        return cap

    def _frame_to_jpeg(self, frame) -> bytes:
        """Convert OpenCV frame (numpy array) to JPEG bytes."""
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()

    def _frame_to_base64(self, jpeg_bytes: bytes) -> str:
        """Convert JPEG bytes to base64 string for WebSocket transport."""
        return base64.b64encode(jpeg_bytes).decode("utf-8")

    def extract_single_frame(self) -> dict | None:
        """
        Extract one frame from source. Used for on-demand snapshots.
        Returns frame data dict or None if failed.
        """
        try:
            cap = self._get_capture()
            ret, frame = cap.read()
            cap.release()

            if not ret:
                return None

            jpeg = self._frame_to_jpeg(frame)
            return {
                "camera_id": self.camera_id,
                "timestamp": datetime.now().isoformat(),
                "jpeg_bytes": jpeg,
                "base64": self._frame_to_base64(jpeg),
                "source": self.source
            }
        except Exception as e:
            print(f"[CCTV] Frame extraction error: {e}")
            return None

    async def stream_frames(self) -> AsyncGenerator[dict, None]:
        self._running = True
        frame_count = 0

        print(f"[CCTV] Streaming from {self.source} | Camera: {self.camera_id}")

        while self._running:
            # open a fresh capture each loop so file restarts cleanly
            cap = self._get_capture()

            try:
                while self._running:
                    ret, frame = cap.read()

                    if not ret:
                        # end of file — break inner loop to reopen
                        print(f"[CCTV] End of file, looping...")
                        break

                    jpeg = self._frame_to_jpeg(frame)
                    frame_data = {
                        "camera_id": self.camera_id,
                        "frame_number": frame_count,
                        "timestamp": datetime.now().isoformat(),
                        "jpeg_bytes": jpeg,
                        "base64": self._frame_to_base64(jpeg),
                        "source": self.source
                    }

                    yield frame_data
                    frame_count += 1

                    if self.max_frames and frame_count >= self.max_frames:
                        print(f"[CCTV] Reached max_frames, stopping.")
                        self._running = False
                        break

                    await asyncio.sleep(self.frame_interval)

            finally:
                cap.release()

            # if source is not a file, don't loop — just exit
            if self.source != "file":
                break

        self._running = False
        print(f"[CCTV] Handler stopped. Total frames: {frame_count}")

    def stop(self):
        """Stop the streaming loop."""
        self._running = False


# --- Multi-camera manager ---

class CCTVManager:
    """
    Manages multiple CCTV handlers simultaneously.
    In the demo, each camera_id maps to a handler instance.
    """
    def __init__(self):
        self.cameras: dict[str, CCTVHandler] = {}

    def add_camera(self, camera_id: str, handler: CCTVHandler):
        self.cameras[camera_id] = handler
        print(f"[CCTVManager] Added camera: {camera_id}")

    def remove_camera(self, camera_id: str):
        handler = self.cameras.pop(camera_id, None)
        if handler:
            handler.stop()

    def get_camera(self, camera_id: str) -> CCTVHandler | None:
        return self.cameras.get(camera_id)

    def list_cameras(self) -> list:
        return list(self.cameras.keys())

    async def snapshot_all(self) -> list[dict]:
        """Get one frame from every camera simultaneously."""
        results = []
        for camera_id, handler in self.cameras.items():
            frame = handler.extract_single_frame()
            if frame:
                results.append(frame)
        return results


# shared instance
cctv_manager = CCTVManager()