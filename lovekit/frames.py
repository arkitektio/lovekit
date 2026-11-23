"""A frame of a data stream on the wire, the same on every transport.

Sixteen bytes, little-endian, then the values as declared (little-endian, C order)::

    version u8 | flags u8 | reserved u16 | sequence u32 | sent_at_us u64 | values
"""

import struct
import time
from dataclasses import dataclass

import numpy as np

VERSION = 1
HEADER = struct.Struct("<BBHIQ")
#: The most the values of one frame take: a frame is one packet on any transport.
MAX_FRAME_BYTES = 1024


@dataclass(frozen=True)
class Frame:
    sequence: int
    sent_at_us: int
    """When it was sent, in microseconds of the sender's clock since the epoch."""
    values: np.ndarray


def little(dtype: str) -> np.dtype:
    """``dtype`` as it is on the wire."""
    return np.dtype(dtype).newbyteorder("<")


def encode(sequence: int, values: np.ndarray) -> bytes:
    """``values`` as a frame sent now."""
    header = HEADER.pack(VERSION, 0, 0, sequence & 0xFFFFFFFF, time.time_ns() // 1000)
    return header + values.astype(little(values.dtype.name), copy=False).tobytes()


def decode(packet: bytes, dtype: str, shape: tuple[int, ...]) -> Frame:
    """The frame in ``packet``, its values read as the stream declared them."""
    version, _flags, _reserved, sequence, sent_at_us = HEADER.unpack_from(packet)
    if version != VERSION:
        raise ValueError(
            f"A frame of version {version}; this lovekit reads version {VERSION}"
        )
    values = np.frombuffer(packet, dtype=little(dtype), offset=HEADER.size).reshape(
        shape
    )
    return Frame(sequence=sequence, sent_at_us=sent_at_us, values=values)
