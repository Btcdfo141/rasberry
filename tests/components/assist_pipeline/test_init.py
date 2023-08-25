"""Test Voice Assistant init."""
from dataclasses import asdict
import itertools as it
from pathlib import Path
import shutil
from unittest.mock import ANY, patch
import wave

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components import assist_pipeline, conversation, stt
from homeassistant.core import Context, HomeAssistant

from .conftest import MockSttProvider, MockSttProviderEntity, MockWakeWordEntity

from tests.typing import WebSocketGenerator

BYTES_ONE_SECOND = 16000 * 2


def process_events(events: list[assist_pipeline.PipelineEvent]) -> list[dict]:
    """Process events to remove dynamic values."""
    processed = []
    for event in events:
        as_dict = asdict(event)
        as_dict.pop("timestamp")
        if as_dict["type"] == assist_pipeline.PipelineEventType.RUN_START:
            as_dict["data"]["pipeline"] = ANY
        processed.append(as_dict)

    return processed


async def test_pipeline_from_audio_stream_auto(
    hass: HomeAssistant,
    mock_stt_provider: MockSttProvider,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream.

    In this test, no pipeline is specified.
    """

    events: list[assist_pipeline.PipelineEvent] = []

    async def audio_data():
        yield b"part1"
        yield b"part2"
        yield b""

    await assist_pipeline.async_pipeline_from_audio_stream(
        hass,
        context=Context(),
        event_callback=events.append,
        stt_metadata=stt.SpeechMetadata(
            language="",
            format=stt.AudioFormats.WAV,
            codec=stt.AudioCodecs.PCM,
            bit_rate=stt.AudioBitRates.BITRATE_16,
            sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
            channel=stt.AudioChannels.CHANNEL_MONO,
        ),
        stt_stream=audio_data(),
    )

    assert process_events(events) == snapshot
    assert mock_stt_provider.received == [b"part1", b"part2"]


async def test_pipeline_from_audio_stream_legacy(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_stt_provider: MockSttProvider,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream.

    In this test, a pipeline using a legacy stt engine is used.
    """
    client = await hass_ws_client(hass)

    events: list[assist_pipeline.PipelineEvent] = []

    async def audio_data():
        yield b"part1"
        yield b"part2"
        yield b""

    # Create a pipeline using an stt entity
    await client.send_json_auto_id(
        {
            "type": "assist_pipeline/pipeline/create",
            "conversation_engine": "homeassistant",
            "conversation_language": "en-US",
            "language": "en",
            "name": "test_name",
            "stt_engine": "test",
            "stt_language": "en-US",
            "tts_engine": "test",
            "tts_language": "en-US",
            "tts_voice": "Arnold Schwarzenegger",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    pipeline_id = msg["result"]["id"]

    # Use the created pipeline
    await assist_pipeline.async_pipeline_from_audio_stream(
        hass,
        context=Context(),
        event_callback=events.append,
        stt_metadata=stt.SpeechMetadata(
            language="en-UK",
            format=stt.AudioFormats.WAV,
            codec=stt.AudioCodecs.PCM,
            bit_rate=stt.AudioBitRates.BITRATE_16,
            sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
            channel=stt.AudioChannels.CHANNEL_MONO,
        ),
        stt_stream=audio_data(),
        pipeline_id=pipeline_id,
    )

    assert process_events(events) == snapshot
    assert mock_stt_provider.received == [b"part1", b"part2"]


async def test_pipeline_from_audio_stream_entity(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_stt_provider_entity: MockSttProviderEntity,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream.

    In this test, a pipeline using am stt entity is used.
    """
    client = await hass_ws_client(hass)

    events: list[assist_pipeline.PipelineEvent] = []

    async def audio_data():
        yield b"part1"
        yield b"part2"
        yield b""

    # Create a pipeline using an stt entity
    await client.send_json_auto_id(
        {
            "type": "assist_pipeline/pipeline/create",
            "conversation_engine": "homeassistant",
            "conversation_language": "en-US",
            "language": "en",
            "name": "test_name",
            "stt_engine": mock_stt_provider_entity.entity_id,
            "stt_language": "en-US",
            "tts_engine": "test",
            "tts_language": "en-US",
            "tts_voice": "Arnold Schwarzenegger",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    pipeline_id = msg["result"]["id"]

    # Use the created pipeline
    await assist_pipeline.async_pipeline_from_audio_stream(
        hass,
        context=Context(),
        event_callback=events.append,
        stt_metadata=stt.SpeechMetadata(
            language="en-UK",
            format=stt.AudioFormats.WAV,
            codec=stt.AudioCodecs.PCM,
            bit_rate=stt.AudioBitRates.BITRATE_16,
            sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
            channel=stt.AudioChannels.CHANNEL_MONO,
        ),
        stt_stream=audio_data(),
        pipeline_id=pipeline_id,
    )

    assert process_events(events) == snapshot
    assert mock_stt_provider_entity.received == [b"part1", b"part2"]


async def test_pipeline_from_audio_stream_no_stt(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_stt_provider: MockSttProvider,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream.

    In this test, the pipeline does not support stt
    """
    client = await hass_ws_client(hass)

    events: list[assist_pipeline.PipelineEvent] = []

    async def audio_data():
        yield b"part1"
        yield b"part2"
        yield b""

    # Create a pipeline without stt support
    await client.send_json_auto_id(
        {
            "type": "assist_pipeline/pipeline/create",
            "conversation_engine": "homeassistant",
            "conversation_language": "en-US",
            "language": "en",
            "name": "test_name",
            "stt_engine": None,
            "stt_language": None,
            "tts_engine": "test",
            "tts_language": "en-AU",
            "tts_voice": "Arnold Schwarzenegger",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    pipeline_id = msg["result"]["id"]

    # Try to use the created pipeline
    with pytest.raises(assist_pipeline.pipeline.PipelineRunValidationError):
        await assist_pipeline.async_pipeline_from_audio_stream(
            hass,
            context=Context(),
            event_callback=events.append,
            stt_metadata=stt.SpeechMetadata(
                language="en-UK",
                format=stt.AudioFormats.WAV,
                codec=stt.AudioCodecs.PCM,
                bit_rate=stt.AudioBitRates.BITRATE_16,
                sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
                channel=stt.AudioChannels.CHANNEL_MONO,
            ),
            stt_stream=audio_data(),
            pipeline_id=pipeline_id,
        )

    assert not events


async def test_pipeline_from_audio_stream_unknown_pipeline(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_stt_provider: MockSttProvider,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream.

    In this test, the pipeline does not exist.
    """
    events: list[assist_pipeline.PipelineEvent] = []

    async def audio_data():
        yield b"part1"
        yield b"part2"
        yield b""

    # Try to use the created pipeline
    with pytest.raises(assist_pipeline.PipelineNotFound):
        await assist_pipeline.async_pipeline_from_audio_stream(
            hass,
            context=Context(),
            event_callback=events.append,
            stt_metadata=stt.SpeechMetadata(
                language="en-UK",
                format=stt.AudioFormats.WAV,
                codec=stt.AudioCodecs.PCM,
                bit_rate=stt.AudioBitRates.BITRATE_16,
                sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
                channel=stt.AudioChannels.CHANNEL_MONO,
            ),
            stt_stream=audio_data(),
            pipeline_id="blah",
        )

    assert not events


async def test_pipeline_from_audio_stream_wake_word(
    hass: HomeAssistant,
    mock_stt_provider: MockSttProvider,
    mock_wake_word_provider_entity: MockWakeWordEntity,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream with wake word."""

    events: list[assist_pipeline.PipelineEvent] = []

    # [0, 1, ...]
    wake_chunk_1 = bytes(it.islice(it.cycle(range(256)), BYTES_ONE_SECOND))

    # [0, 2, ...]
    wake_chunk_2 = bytes(it.islice(it.cycle(range(0, 256, 2)), BYTES_ONE_SECOND))

    async def audio_data():
        yield wake_chunk_1  # 1 second
        yield wake_chunk_2  # 1 second
        yield b"wake word!"
        yield b"part1"
        yield b"part2"
        yield b"end"
        yield b""

    def continue_stt(self, chunk):
        # Ensure stt_vad_start event is triggered
        self.in_command = True

        # Stop on fake end chunk to trigger stt_vad_end
        return chunk != b"end"

    with patch(
        "homeassistant.components.assist_pipeline.pipeline.VoiceCommandSegmenter.process",
        continue_stt,
    ):
        await assist_pipeline.async_pipeline_from_audio_stream(
            hass,
            context=Context(),
            event_callback=events.append,
            stt_metadata=stt.SpeechMetadata(
                language="",
                format=stt.AudioFormats.WAV,
                codec=stt.AudioCodecs.PCM,
                bit_rate=stt.AudioBitRates.BITRATE_16,
                sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
                channel=stt.AudioChannels.CHANNEL_MONO,
            ),
            stt_stream=audio_data(),
            start_stage=assist_pipeline.PipelineStage.WAKE_WORD,
            wake_word_settings=assist_pipeline.WakeWordSettings(
                audio_seconds_to_buffer=1.5
            ),
        )

    assert process_events(events) == snapshot

    # 1. Half of wake_chunk_1 + all wake_chunk_2
    # 2. queued audio (from mock wake word entity)
    # 3. part1
    # 4. part2
    assert len(mock_stt_provider.received) == 4

    first_chunk = mock_stt_provider.received[0]
    assert first_chunk == wake_chunk_1[len(wake_chunk_1) // 2 :] + wake_chunk_2

    assert mock_stt_provider.received[1:] == [b"queued audio", b"part1", b"part2"]


async def test_pipeline_save_audio(
    hass: HomeAssistant,
    mock_stt_provider: MockSttProvider,
    mock_wake_word_provider_entity: MockWakeWordEntity,
    init_components,
    snapshot: SnapshotAssertion,
) -> None:
    """Test creating a pipeline from an audio stream with wake word."""

    pipeline = assist_pipeline.Pipeline(
        conversation_engine=conversation.HOME_ASSISTANT_AGENT,
        conversation_language=hass.config.language,
        language=hass.config.language,
        name="test",
        stt_engine=mock_stt_provider.name,
        stt_language=mock_stt_provider.supported_languages[0],
        tts_engine=None,
        tts_language=None,
        tts_voice=None,
        #
        save_audio=True,
    )

    audio_dir = Path(hass.config.path("media")) / "assist_pipeline"

    # Remove any existing audio
    if audio_dir.is_dir():
        shutil.rmtree(audio_dir)

    try:
        with patch(
            "homeassistant.components.assist_pipeline.async_get_pipeline",
            return_value=pipeline,
        ):
            events: list[assist_pipeline.PipelineEvent] = []

            # Pad out to an even number of bytes since these "samples" will be
            # saved as 16-bit values.
            async def audio_data():
                yield b"wake word_"
                # queued audio
                yield b"part1_"
                yield b"part2_"
                yield b""

            await assist_pipeline.async_pipeline_from_audio_stream(
                hass,
                context=Context(),
                event_callback=events.append,
                stt_metadata=stt.SpeechMetadata(
                    language="",
                    format=stt.AudioFormats.WAV,
                    codec=stt.AudioCodecs.PCM,
                    bit_rate=stt.AudioBitRates.BITRATE_16,
                    sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
                    channel=stt.AudioChannels.CHANNEL_MONO,
                ),
                stt_stream=audio_data(),
                start_stage=assist_pipeline.PipelineStage.WAKE_WORD,
                end_stage=assist_pipeline.PipelineStage.STT,
            )

            run_dirs = list(audio_dir.iterdir())

            # Only one pipeline run
            assert len(run_dirs) == 1
            assert run_dirs[0].is_dir()

            # Wake and stt files
            run_files = list(run_dirs[0].iterdir())
            assert len(run_files) == 2
            wake_file = run_files[0] if "wake" in run_files[0].name else run_files[1]
            stt_file = run_files[0] if "stt" in run_files[0].name else run_files[1]
            assert wake_file != stt_file

            # Verify wake file
            with wave.open(str(wake_file), "rb") as wake_wav:
                wake_data = wake_wav.readframes(wake_wav.getnframes())
                assert wake_data == b"wake word_"

            # Verify stt file
            with wave.open(str(stt_file), "rb") as stt_wav:
                stt_data = stt_wav.readframes(stt_wav.getnframes())
                assert stt_data == b"queued audiopart1_part2_"
    finally:
        # Clean up saved audio
        if audio_dir.is_dir():
            shutil.rmtree(audio_dir)
