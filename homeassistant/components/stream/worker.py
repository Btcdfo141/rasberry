"""Provides the worker thread needed for processing streams."""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable, Generator, Iterator, Mapping
import contextlib
import datetime
from io import SEEK_END, BytesIO
import logging
from threading import Event
from typing import Any, cast

import attr
import av

from homeassistant.core import HomeAssistant

from . import redact_credentials
from .const import (
    AUDIO_CODECS,
    HLS_PROVIDER,
    MAX_MISSING_DTS,
    MAX_TIMESTAMP_GAP,
    PACKETS_TO_WAIT_FOR_AUDIO,
    SEGMENT_CONTAINER_FORMAT,
    SOURCE_TIMEOUT,
)
from .core import (
    STREAM_SETTINGS_NON_LL_HLS,
    KeyFrameConverter,
    Part,
    Segment,
    StreamOutput,
    StreamSettings,
)
from .diagnostics import Diagnostics
from .fmp4utils import read_init
from .hls import HlsStreamOutput

_LOGGER = logging.getLogger(__name__)
LARGE_NEGATIVE_TS = -(2**31)


class StreamWorkerError(Exception):
    """An exception thrown while processing a stream."""


class StreamEndedError(StreamWorkerError):
    """Raised when the stream is complete, exposed for facilitating testing."""


class StreamState:
    """Responsible for tracking output and playback state for a stream.

    Holds state used for playback to interpret a decoded stream. A source stream
    may be reset (e.g. reconnecting to an rtsp stream) and this object tracks
    the state to inform the player.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        outputs_callback: Callable[[], Mapping[str, StreamOutput]],
        diagnostics: Diagnostics,
    ) -> None:
        """Initialize StreamState."""
        self._stream_id: int = 0
        self.hass = hass
        self._outputs_callback: Callable[
            [], Mapping[str, StreamOutput]
        ] = outputs_callback
        # sequence gets incremented before the first segment so the first segment
        # has a sequence number of 0.
        self._sequence = -1
        self._diagnostics = diagnostics

    @property
    def sequence(self) -> int:
        """Return the current sequence for the latest segment."""
        return self._sequence

    def next_sequence(self) -> int:
        """Increment the sequence number."""
        self._sequence += 1
        return self._sequence

    @property
    def stream_id(self) -> int:
        """Return the readonly stream_id attribute."""
        return self._stream_id

    def discontinuity(self) -> None:
        """Mark the stream as having been restarted."""
        # Preserving sequence and stream_id here keep the HLS playlist logic
        # simple to check for discontinuity at output time, and to determine
        # the discontinuity sequence number.
        self._stream_id += 1
        # Call discontinuity to fix incomplete segment in HLS output
        if hls_output := self._outputs_callback().get(HLS_PROVIDER):
            cast(HlsStreamOutput, hls_output).discontinuity()

    @property
    def outputs(self) -> list[StreamOutput]:
        """Return the active stream outputs."""
        return list(self._outputs_callback().values())

    @property
    def diagnostics(self) -> Diagnostics:
        """Return diagnostics object."""
        return self._diagnostics


class StreamMuxer:
    """StreamMuxer re-packages video/audio packets for output."""

    def __init__(
        self,
        hass: HomeAssistant,
        video_stream: av.video.VideoStream,
        audio_stream: av.audio.stream.AudioStream | None,
        audio_bsf: av.BitStreamFilter | None,
        stream_state: StreamState,
        stream_settings: StreamSettings,
    ) -> None:
        """Initialize StreamMuxer."""
        self._hass = hass
        self._segment_start_dts: int = cast(int, None)
        self._memory_file: BytesIO = cast(BytesIO, None)
        self._av_output: av.container.OutputContainer = None
        self._input_video_stream: av.video.VideoStream = video_stream
        self._input_audio_stream: av.audio.stream.AudioStream | None = audio_stream
        self._audio_bsf = audio_bsf
        self._audio_bsf_context: av.BitStreamFilterContext = None
        self._output_video_stream: av.video.VideoStream = None
        self._output_audio_stream: av.audio.stream.AudioStream | None = None
        self._segment: Segment | None = None
        # the following 3 member variables are used for Part formation
        self._memory_file_pos: int = cast(int, None)
        self._part_start_dts: int = cast(int, None)
        self._part_has_keyframe = False
        self._stream_settings = stream_settings
        self._stream_state = stream_state
        self._start_time = datetime.datetime.utcnow()
        self._frag_duration_ts = (
            self._stream_settings.part_target_duration * 0.85 / video_stream.time_base
        )
        self._max_frag_duration_ts = int(
            self._stream_settings.part_target_duration / video_stream.time_base
        )
        self._max_frag_duration_exceeded = False
        # We keep track of recent packets to help us track FFmpeg's interleave queues
        self._buffered_video_packets: deque[av.Packet] = deque()
        self._last_packet_was_audio = False

    def make_new_av(
        self,
        memory_file: BytesIO,
        sequence: int,
        input_vstream: av.video.VideoStream,
        input_astream: av.audio.stream.AudioStream | None,
    ) -> tuple[
        av.container.OutputContainer,
        av.video.VideoStream,
        av.audio.stream.AudioStream | None,
    ]:
        """Make a new av OutputContainer and add output streams."""
        container = av.open(
            memory_file,
            mode="w",
            format=SEGMENT_CONTAINER_FORMAT,
            container_options={
                **{
                    # Removed skip_sidx - see https://github.com/home-assistant/core/pull/39970
                    # "cmaf" flag replaces several of the movflags used, but too recent to use for now
                    "movflags": "frag_custom+empty_moov+default_base_moof+frag_discont+negative_cts_offsets+skip_trailer+delay_moov",
                    # Sometimes the first segment begins with negative timestamps, and this setting just
                    # adjusts the timestamps in the output from that segment to start from 0. Helps from
                    # having to make some adjustments in test_durations
                    "avoid_negative_ts": "disabled",
                    "fragment_index": str(sequence + 1),
                    "video_track_timescale": str(int(1 / input_vstream.time_base)),
                },
                # Only do extra fragmenting if we are using ll_hls
                # Let ffmpeg do the work using frag_duration
                # Fragment durations may exceed the 15% allowed variance but it seems ok
                **(
                    {
                        "movflags": "empty_moov+default_base_moof+frag_discont+negative_cts_offsets+skip_trailer+delay_moov",
                        # Create a fragment every TARGET_PART_DURATION. The data from each fragment is stored in
                        # a "Part" that can be combined with the data from all the other "Part"s, plus an init
                        # section, to reconstitute the data in a "Segment".
                        # The LL-HLS spec allows for a fragment's duration to be within the range [0.85x,1.0x]
                        # of the part target duration. We use the frag_duration option to tell ffmpeg to try to
                        # cut the fragments when they reach frag_duration. However, the resulting fragments can
                        # have variability in their durations and can end up being too short or too long. With a
                        # video track with no audio, the discrete nature of frames means that the frame at the
                        # end of a fragment will sometimes extend slightly beyond the desired frag_duration.
                        # If there are two tracks, as in the case of a video feed with audio, there is an added
                        # wrinkle as the fragment cut seems to be done on the first track that crosses the desired
                        # threshold, and cutting on the audio track may also result in a shorter video fragment
                        # than desired.
                        # Given this, our approach is to give ffmpeg a frag_duration somewhere in the middle
                        # of the range, hoping that the parts stay pretty well bounded, and we adjust the part
                        # durations a bit in the hls metadata so that everything "looks" ok.
                        "frag_duration": str(
                            int(self._frag_duration_ts * input_vstream.time_base * 1e6)
                        ),
                    }
                    if not input_astream
                    else {}
                ),
            },
        )
        output_vstream = container.add_stream(template=input_vstream)
        # Check if audio is requested
        output_astream = None
        if input_astream:
            if self._audio_bsf:
                self._audio_bsf_context = self._audio_bsf.create()
                self._audio_bsf_context.set_input_stream(input_astream)
            output_astream = container.add_stream(
                template=self._audio_bsf_context or input_astream
            )
        return container, output_vstream, output_astream

    def reset(self, video_dts: int) -> None:
        """Initialize a new stream segment."""
        self._part_start_dts = self._segment_start_dts = video_dts
        self._last_packet_was_audio = False
        self._segment = None
        self._memory_file = BytesIO()
        self._memory_file_pos = 0
        (
            self._av_output,
            self._output_video_stream,
            self._output_audio_stream,
        ) = self.make_new_av(
            memory_file=self._memory_file,
            sequence=self._stream_state.next_sequence(),
            input_vstream=self._input_video_stream,
            input_astream=self._input_audio_stream,
        )
        if self._output_video_stream.name == "hevc":
            self._output_video_stream.codec_tag = "hvc1"

    def mux_packet(self, packet: av.Packet) -> None:
        """Mux a packet to the appropriate output stream."""

        # Check for end of segment
        if packet.stream == self._input_video_stream:

            part_duration_ts = packet.dts - self._part_start_dts
            if not self._max_frag_duration_exceeded:
                # If the max frag duration is exceeded, adjust the packet back down
                # to the max frag duration. We can only do this once per fragment,
                # otherwise we will have duplicate dts values.
                frag_end_adjustment = self._max_frag_duration_ts - part_duration_ts
                if frag_end_adjustment <= 0:
                    packet.dts += frag_end_adjustment
                    self._max_frag_duration_exceeded = True

            if (
                packet.is_keyframe
                and (packet.dts - self._segment_start_dts) * packet.time_base
                >= self._stream_settings.min_segment_duration
            ):
                # Flush segment (also flushes the stub part segment)
                self.flush(packet, last_part=True)

            # Mux the packet
            packet.stream = self._output_video_stream
            # Mux the current video packet
            if self._input_audio_stream:

                self._av_output.mux(packet)
                self._buffered_video_packets.append(packet)
                if (
                    self._last_packet_was_audio
                    and part_duration_ts >= self._frag_duration_ts
                ):
                    # Since we are processing the packets in time order between
                    # both streams, all the video packets before the last audio
                    # packet have been muxed. We can flush the fragment here
                    # and the next fragment will start with this packet which should
                    # still be in the interleave queue.
                    self._av_output.flush()
                    self.check_flush_part(packet)
                self._last_packet_was_audio = False
            else:
                self._av_output.mux(packet)
                self.check_flush_part(packet)
                self._part_has_keyframe |= packet.is_keyframe

        elif packet.stream == self._input_audio_stream:
            # This audio packet should release any pending video packets. Update the
            # keyframe metadata accordingly.
            self._part_has_keyframe |= any(
                pkt.is_keyframe for pkt in self._buffered_video_packets
            )
            self._buffered_video_packets.clear()
            self._last_packet_was_audio = True
            if self._audio_bsf_context:
                self._audio_bsf_context.send(packet)
                while packet := self._audio_bsf_context.recv():
                    packet.stream = self._output_audio_stream
                    self._av_output.mux(packet)
                return
            packet.stream = self._output_audio_stream
            self._av_output.mux(packet)

    def create_segment(self) -> None:
        """Create a segment when the moov is ready."""
        self._segment = Segment(
            sequence=self._stream_state.sequence,
            stream_id=self._stream_state.stream_id,
            init=read_init(self._memory_file),
            # Fetch the latest StreamOutputs, which may have changed since the
            # worker started.
            stream_outputs=self._stream_state.outputs,
            start_time=self._start_time,
        )
        self._memory_file_pos = self._memory_file.tell()
        self._memory_file.seek(0, SEEK_END)

    def check_flush_part(self, packet: av.Packet) -> None:
        """Check for and mark a part segment boundary and record its duration."""
        if self._memory_file_pos == self._memory_file.tell():
            return
        if self._segment is None:
            # We have our first non-zero byte position. This means the init has just
            # been written. Create a Segment and put it to the queue of each output.
            self.create_segment()
            if self._input_audio_stream:
                # If we are manually flushing, the first flush only wrote the moov
                self._av_output.flush()
        # Flush the moof
        self.flush(packet, last_part=False)

    def flush(self, packet: av.Packet, last_part: bool) -> None:
        """Output a part from the most recent bytes in the memory_file.

        If last_part is True, also close the segment, give it a duration,
        and clean up the av_output and memory_file.
        There are two different ways to enter this function, and when
        last_part is True, packet has not yet been muxed, while when
        last_part is False, the packet has already been muxed. However,
        in both cases, packet is the next packet and is not included in
        the Part.
        This function writes the duration metadata for the Part and
        for the Segment. However, as the fragmentation done by ffmpeg
        may result in fragment durations which fall outside the
        [0.85x,1.0x] tolerance band allowed by LL-HLS, we need to fudge
        some durations a bit by reporting them as being within that
        range.
        Note that repeated adjustments may cause drift between the part
        durations in the metadata and those in the media and result in
        playback issues in some clients.
        """
        if last_part:
            # Closing the av_output will write the remaining buffered data to the
            # memory_file as a new moof/mdat.
            self._av_output.close()
            # Closing the av_output flushes the remaining packets, so update the keyframe metadata
            self._part_has_keyframe |= any(
                pkt.is_keyframe for pkt in self._buffered_video_packets
            )
            self._buffered_video_packets.clear()
            # With delay_moov, this may be the first time the file pointer has
            # moved, so the segment may not yet have been created
            if not self._segment:
                self.create_segment()
        assert self._segment
        self._memory_file.seek(self._memory_file_pos)
        self._hass.loop.call_soon_threadsafe(
            self._segment.async_add_part,
            Part(
                duration=float((packet.dts - self._part_start_dts) * packet.time_base),
                has_keyframe=self._part_has_keyframe,
                data=self._memory_file.read(),
            ),
            (
                segment_duration := float(
                    (packet.dts - self._segment_start_dts) * packet.time_base
                )
            )
            if last_part
            else 0,
        )
        if last_part:
            # If we've written the last part, we can close the memory_file.
            self._memory_file.close()  # We don't need the BytesIO object anymore
            self._start_time += datetime.timedelta(seconds=segment_duration)
            # Reinitialize
            self.reset(packet.dts)
        else:
            # For the last part, these will get set again elsewhere so we can skip
            # setting them here.
            self._memory_file_pos = self._memory_file.tell()
            self._part_start_dts = packet.dts
        self._part_has_keyframe = False
        self._max_frag_duration_exceeded = False

    def close(self) -> None:
        """Close stream buffer."""
        self._av_output.close()
        self._memory_file.close()


class PeekIterator(Iterator):
    """An Iterator that may allow multiple passes.

    This may be consumed like a normal Iterator, however also supports a
    peek() method that buffers consumed items from the iterator.
    """

    def __init__(self, iterator: Iterator[av.Packet]) -> None:
        """Initialize PeekIterator."""
        self._iterator = iterator
        self._buffer: deque[av.Packet] = deque()
        # A pointer to either _iterator or _buffer
        self._next = self._iterator.__next__

    def __iter__(self) -> Iterator:
        """Return an iterator."""
        return self

    def __next__(self) -> av.Packet:
        """Return and consume the next item available."""
        return self._next()

    def _pop_buffer(self) -> av.Packet:
        """Consume items from the buffer until exhausted."""
        if self._buffer:
            return self._buffer.popleft()
        # The buffer is empty, so change to consume from the iterator
        self._next = self._iterator.__next__
        return self._next()

    def peek(self) -> Generator[av.Packet, None, None]:
        """Return items without consuming from the iterator."""
        # Items consumed are added to a buffer for future calls to __next__
        # or peek. First iterate over the buffer from previous calls to peek.
        self._next = self._pop_buffer
        for packet in self._buffer:
            yield packet
        for packet in self._iterator:
            self._buffer.append(packet)
            yield packet


class TimestampValidator:
    """Validate ordering of timestamps for packets in a stream."""

    def __init__(
        self,
        video_stream: av.video.VideoStream,
        audio_stream: av.audio.stream.AudioStream | None,
    ) -> None:
        """Initialize the TimestampValidator."""
        # Decode timestamp of last packet in each stream
        self._last_dts: dict[av.stream.Stream, int] = defaultdict(
            lambda: LARGE_NEGATIVE_TS
        )
        # Last audio dts + duration
        self._last_audio_dts_duration = LARGE_NEGATIVE_TS
        self._audio_stream = audio_stream
        # Number of consecutive missing decode timestamps
        self._missing_dts = 0
        # For the bounds, just use the larger of the two values. If the error is not flagged
        # by one stream, it should just get flagged by the other stream. Either value should
        # result in a value which is much less than a 32 bit INT_MAX, which helps avoid the
        # assertion error from FFmpeg.
        self._max_dts_gap = MAX_TIMESTAMP_GAP / min(
            video_stream.time_base,
            audio_stream.time_base if audio_stream else float("inf"),
        )

    def is_valid(self, packet: av.Packet) -> bool:
        """Validate the packet timestamp based on ordering within the stream."""
        # Discard packets missing DTS. Terminate if too many are missing.
        if packet.dts is None:
            if self._missing_dts >= MAX_MISSING_DTS:
                raise StreamWorkerError(
                    f"No dts in {MAX_MISSING_DTS+1} consecutive packets"
                )
            self._missing_dts += 1
            return False
        self._missing_dts = 0
        # Discard when dts is not monotonic. Terminate if gap is too wide.
        if (last_dts := self._last_dts[packet.stream]) != LARGE_NEGATIVE_TS:
            if abs(last_dts - packet.dts) > self._max_dts_gap:
                raise StreamWorkerError(
                    f"Timestamp discontinuity detected: last dts = {last_dts}, dts ="
                    f" {packet.dts}"
                )
            if packet.stream == self._audio_stream:
                ts_adjustment = self._last_audio_dts_duration - packet.dts
                if ts_adjustment * packet.time_base > 0.2:
                    # Don't let the adjustment drift too much forward
                    return False
                # adjust the packet if we are close
                if ts_adjustment * packet.time_base > -0.2:
                    packet.dts = packet.pts = packet.dts + ts_adjustment
        if packet.dts <= last_dts:
            return False
        self._last_dts[packet.stream] = packet.dts
        if packet.stream == self._audio_stream:
            self._last_audio_dts_duration = packet.dts + packet.duration
        packet.dts -= packet.stream.start_time
        packet.pts -= packet.stream.start_time
        return True


def is_keyframe(packet: av.Packet) -> Any:
    """Return true if the packet is a keyframe."""
    return packet.is_keyframe


def get_audio_bitstream_filter(
    packets: Iterator[av.Packet], audio_stream: Any
) -> av.BitStreamFilterContext | None:
    """Return the aac_adtstoasc bitstream filter if ADTS AAC is detected."""
    if not audio_stream:
        return None
    for count, packet in enumerate(packets):
        if count >= PACKETS_TO_WAIT_FOR_AUDIO:
            # Some streams declare an audio stream and never send any packets
            _LOGGER.warning("Audio stream not found")
            break
        if packet.stream == audio_stream:
            # detect ADTS AAC and disable audio
            if audio_stream.codec.name == "aac" and packet.size > 2:
                with memoryview(packet) as packet_view:
                    if packet_view[0] == 0xFF and packet_view[1] & 0xF0 == 0xF0:
                        _LOGGER.debug(
                            "ADTS AAC detected. Adding aac_adtstoaac bitstream filter"
                        )
                        return av.BitStreamFilter("aac_adtstoasc")
            break
    return None


def sort_packets(packets: PeekIterator) -> Iterator[av.Packet]:
    """
    Return an iterator which yields the interleaved audio and video packets in order.

    This assumes there is one video and one audio stream and each stream already yields
    its packets in order.
    """
    audio_deque: deque[av.Packet] = deque()
    video_deque: deque[av.Packet] = deque()
    for packet in packets:
        if packet.stream.type == "video":
            video_deque.append(packet)
        else:
            audio_deque.append(packet)
        while audio_deque and video_deque:
            if (
                video_deque[0].dts * video_deque[0].time_base
                <= audio_deque[0].dts * audio_deque[0].time_base
            ):
                yield video_deque.popleft()
            else:
                yield audio_deque.popleft()
    while video_deque:
        yield video_deque.popleft()
    while audio_deque:
        yield audio_deque.popleft()


def stream_worker(
    source: str,
    pyav_options: dict[str, str],
    stream_settings: StreamSettings,
    stream_state: StreamState,
    keyframe_converter: KeyFrameConverter,
    quit_event: Event,
) -> None:
    """Handle consuming streams."""

    if av.library_versions["libavformat"][0] >= 59 and "stimeout" in pyav_options:
        # the stimeout option was renamed to timeout as of ffmpeg 5.0
        pyav_options["timeout"] = pyav_options["stimeout"]
        del pyav_options["stimeout"]
    try:
        container = av.open(source, options=pyav_options, timeout=SOURCE_TIMEOUT)
    except av.AVError as err:
        raise StreamWorkerError(
            f"Error opening stream ({err.type}, {err.strerror})"
            f" {redact_credentials(str(source))}"
        ) from err
    try:
        video_stream = container.streams.video[0]
    except (KeyError, IndexError) as ex:
        raise StreamWorkerError("Stream has no video") from ex
    keyframe_converter.create_codec_context(codec_context=video_stream.codec_context)
    try:
        audio_stream = container.streams.audio[0]
    except (KeyError, IndexError):
        audio_stream = None
    if audio_stream and audio_stream.name not in AUDIO_CODECS:
        audio_stream = None
    # Some audio streams do not have a profile and throw errors when remuxing
    if audio_stream and audio_stream.profile is None:
        audio_stream = None
    # Disable ll-hls for hls inputs
    if container.format.name == "hls":
        for field in attr.fields(StreamSettings):
            setattr(
                stream_settings,
                field.name,
                getattr(STREAM_SETTINGS_NON_LL_HLS, field.name),
            )
    stream_state.diagnostics.set_value("container_format", container.format.name)
    stream_state.diagnostics.set_value("video_codec", video_stream.name)
    if audio_stream:
        stream_state.diagnostics.set_value("audio_codec", audio_stream.name)

    dts_validator = TimestampValidator(video_stream, audio_stream)
    container_packets = PeekIterator(
        filter(dts_validator.is_valid, container.demux((video_stream, audio_stream)))
    )

    def is_video(packet: av.Packet) -> Any:
        """Return true if the packet is for the video stream."""
        return packet.stream.type == "video"

    # Have to work around two problems with RTSP feeds in ffmpeg
    # 1 - first frame has bad pts/dts https://trac.ffmpeg.org/ticket/5018
    # 2 - seeking can be problematic https://trac.ffmpeg.org/ticket/7815
    #
    # Use a peeking iterator to peek into the start of the stream, ensuring
    # everything looks good, then go back to the start when muxing below.
    try:
        # Get the required bitstream filter
        audio_bsf = get_audio_bitstream_filter(container_packets.peek(), audio_stream)
        # Advance to the first keyframe for muxing, then rewind so the muxing
        # loop below can consume.
        first_keyframe = next(
            filter(lambda pkt: is_keyframe(pkt) and is_video(pkt), container_packets)
        )
        # Deal with problem #1 above (bad first packet pts/dts) by recalculating
        # using pts/dts from second packet. Use the peek iterator to advance
        # without consuming from container_packets. Skip over the first keyframe
        # then use the duration from the second video packet to adjust dts.
        next_video_packet = next(filter(is_video, container_packets.peek()))
        # Since the is_valid filter has already been applied before the following
        # adjustment, it does not filter out the case where the duration below is
        # 0 and both the first_keyframe and next_video_packet end up with the same
        # dts. Use "or 1" to deal with this.
        start_dts = next_video_packet.dts - (next_video_packet.duration or 1)
        first_keyframe.dts = first_keyframe.pts = start_dts
    except StreamWorkerError as ex:
        container.close()
        raise ex
    except StopIteration as ex:
        container.close()
        raise StreamEndedError("Stream ended; no additional packets") from ex
    except av.AVError as ex:
        container.close()
        raise StreamWorkerError(
            "Error demuxing stream while finding first packet: %s" % str(ex)
        ) from ex

    muxer = StreamMuxer(
        stream_state.hass,
        video_stream,
        audio_stream,
        audio_bsf,
        stream_state,
        stream_settings,
    )
    muxer.reset(start_dts)

    # Mux the first keyframe, then proceed through the rest of the packets
    muxer.mux_packet(first_keyframe)

    sorted_container_packets = (
        sort_packets(container_packets) if audio_stream else container_packets
    )

    with contextlib.closing(container), contextlib.closing(muxer):
        while not quit_event.is_set():
            try:
                packet = next(sorted_container_packets)
            except StreamWorkerError as ex:
                raise ex
            except StopIteration as ex:
                raise StreamEndedError("Stream ended; no additional packets") from ex
            except av.AVError as ex:
                raise StreamWorkerError("Error demuxing stream: %s" % str(ex)) from ex

            muxer.mux_packet(packet)

            if packet.is_keyframe and is_video(packet):
                keyframe_converter.packet = packet
