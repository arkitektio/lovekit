import time
from livekit import rtc
import threading
import asyncio
import janus
import cv2
import numpy as np
from datetime import datetime


async def astream_videofile(
    room: rtc.Room,
    width: int = 1000,
    height: int = 1000,
    video_path: str = "earth.mp4",
    frame_rate: int = 30,
    auto_restream: bool = True,
):
    # get token and connect to room - not included
    # publish a track
    source = rtc.VideoSource(width, height)
    track = rtc.LocalVideoTrack.create_video_track("hue", source)
    options = rtc.TrackPublishOptions(
        source=rtc.TrackSource.SOURCE_CAMERA,
        video_encoding=rtc.VideoEncoding(
            max_framerate=frame_rate,
            max_bitrate=5000000,  # 5 Mbps
        ),
    )

    _ = await room.local_participant.publish_track(track, options)
    video_path = "earth.mp4"
    event = threading.Event()
    queue: janus.Queue[rtc.VideoFrame | None] = janus.Queue()
    threading.Thread(
        target=display_clock_video,
        args=(queue.sync_q, video_path, event, width, height, frame_rate),
    ).start()

    try:
        while True:
            frame = await queue.async_q.get()
            if frame is None:
                break
            source.capture_frame(frame)

            await asyncio.sleep(
                1 / frame_rate
            )  # Adjust sleep time for desired frame rate
    except asyncio.CancelledError:
        event.set()

        await room.disconnect()

        raise


def display_video(
    squeue: janus.SyncQueue[rtc.VideoFrame | None],
    video_path: str,
    event: threading.Event,
    width: int,
    height: int,
    frame_rate: int,
):
    cap = cv2.VideoCapture(video_path)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Resize frame if necessary
        frame = cv2.resize(frame, (width, height))

        # Convert BGR frame to RGBA format
        rgba_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)

        # Create a VideoFrame and capture it
        frame_data = rgba_frame.tobytes()
        frame = rtc.VideoFrame(width, height, rtc.VideoBufferType.RGBA, frame_data)
        squeue.put_nowait(frame)
        if event.is_set():
            break
        time.sleep(1 / frame_rate)

    cap.release()
    squeue.put_nowait(None)


def display_clock_video(
    squeue: janus.SyncQueue["rtc.VideoFrame | None"],
    video_path: str,
    event: threading.Event,
    width: int,
    height: int,
    frame_rate: int,
):
    font = cv2.FONT_HERSHEY_SIMPLEX

    while not event.is_set():
        # Create a black background
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Get current time
        timestamp = datetime.now().strftime("%H:%M:%S:%f")

        # Draw the time on the frame
        cv2.putText(
            frame,
            timestamp,
            (50, height // 2),
            font,
            3,
            (255, 255, 255),
            6,
            cv2.LINE_AA,
        )

        # Convert BGR frame to RGBA format with manual channel ordering
        b, g, r = cv2.split(frame)
        alpha = np.ones(b.shape, dtype=b.dtype) * 255
        rgba_frame = cv2.merge((r, g, b, alpha))

        # Create and queue the VideoFrame
        frame_data = rgba_frame.tobytes()
        video_frame = rtc.VideoFrame(
            width, height, rtc.VideoBufferType.RGBA, frame_data
        )

        try:
            squeue.put_nowait(video_frame)
        except Exception as e:
            print(f"Queue error: {e}")
            break

        time.sleep(0.04)

    squeue.put_nowait(None)
