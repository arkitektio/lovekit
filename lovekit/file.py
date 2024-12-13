import time
from livekit import rtc
import threading
import asyncio
import janus
import cv2


async def stream_videofile(
    room: rtc.Room,
    width: int = 1000,
    height: int = 1000,
    video_path: str = "earth.mp4",
    frame_rate: int = 30,
    auto_restream: bool = False,
):
    # get token and connect to room - not included
    # publish a track
    source = rtc.VideoSource(width, height)
    track = rtc.LocalVideoTrack.create_video_track("hue", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_CAMERA
    publication = await room.local_participant.publish_track(track, options)
    video_path = "earth.mp4"
    event = threading.Event()
    queue = janus.Queue()
    threading.Thread(
        target=display_video,
        args=(queue.sync_q, video_path, event, width, height, frame_rate),
    ).start()

    try:
        while True:
            frame = await queue.async_q.get()
            if frame is None:
                if auto_restream:
                    threading.Thread(
                        target=display_video,
                        args=(
                            queue.sync_q,
                            video_path,
                            event,
                            width,
                            height,
                            frame_rate,
                        ),
                    ).start()
                    continue
                else:
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
    squeue,
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
