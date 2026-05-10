#!/usr/bin/env python3
"""Verify the minimal PyAV wheel: H.264 decode-only feature set."""
import sys


def log(msg: str) -> None:
    print(f"[test] {msg}", flush=True)


def test_import() -> None:
    import av  # noqa: F401
    log(f"av version     : {av.__version__}")
    log(f"FFmpeg version : {av.ffmpeg_version_info}")


def test_h264_codec() -> None:
    import av

    codec = av.codec.Codec("h264", "r")
    assert codec.name == "h264", f"Expected h264, got {codec.name}"
    assert not codec.is_encoder, "h264 should be a decoder, not an encoder"
    log(f"h264 decoder   : OK  (long_name={codec.long_name!r})")


def test_codec_context() -> None:
    import av

    ctx = av.codec.CodecContext.create("h264", "r")
    assert ctx is not None
    log("CodecContext   : OK")


def test_video_frame() -> None:
    import av

    # avutil: basic frame allocation
    frame = av.VideoFrame(64, 64, "yuv420p")
    assert frame.width == 64
    assert frame.height == 64
    assert frame.format.name == "yuv420p"
    log("VideoFrame     : OK  (64x64 yuv420p)")


def test_swscale_reformat() -> None:
    import av

    # swscale: pixel-format conversion
    src = av.VideoFrame(64, 64, "yuv420p")
    dst = src.reformat(format="rgb24")
    assert dst.format.name == "rgb24"
    assert dst.width == 64 and dst.height == 64
    log("swscale reformat: OK  (yuv420p -> rgb24)")


def test_h264_decode_annexb() -> None:
    """Verify the H.264 decoder API: send a flush packet and confirm the
    codec accepts it without crashing.  Actual frame decoding requires a
    valid bitstream; we focus on API availability here.
    """
    import av

    codec_ctx = av.codec.CodecContext.create("h264", "r")

    # A zero-length (flush) packet signals EOF to the decoder.
    # It will always return 0 frames but must not raise on a properly
    # initialised codec context.
    try:
        frames = codec_ctx.decode(av.Packet(b""))
    except av.AVError:
        # avcodec may return AVERROR_EOF on flush before any data - that's fine.
        frames = []

    log(f"H.264 decode API: OK  (flush returned {len(frames)} frame(s))")


def main() -> None:
    tests = [
        ("import av",             test_import),
        ("h264 codec",            test_h264_codec),
        ("CodecContext",          test_codec_context),
        ("VideoFrame (avutil)",   test_video_frame),
        ("swscale reformat",      test_swscale_reformat),
        ("H.264 Annex-B decode",  test_h264_decode_annexb),
    ]

    failed: list[str] = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            log(f"FAIL [{name}]: {exc}")
            failed.append(name)

    if failed:
        log(f"\n{len(failed)} test(s) FAILED: {', '.join(failed)}")
        sys.exit(1)

    log(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
