from livekit import rtc

from fakts_next.helpers import afakt


async def aconnect(url, stream):
    room = rtc.Room()
    await room.connect(url, stream.token)