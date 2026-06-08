import os
from backend.pipeline.montage import list_clips, sentence_ranges, render
from backend import ffmpeg
from backend.config import DEFAULT_CLIPS_DIR

def test_sentence_ranges_cover_duration():
    tokens = [
        {"sent": 0, "start": 0.0, "end": 1.0},
        {"sent": 1, "start": 1.0, "end": 2.0},
    ]
    ranges = sentence_ranges(tokens, 2, 3.0)
    assert ranges[0][0] == 0.0
    assert ranges[-1][1] == 3.0

def test_apply_boost_cuts_subdivides_hook():
    from backend.pipeline.montage import apply_boost_cuts
    out = apply_boost_cuts([(0.0, 5.0)], hook_dur=3.5, hook_cut=0.8)
    assert len(out) > 1
    assert out[0] == (0.0, 0.8)
    assert abs(out[-1][1] - 5.0) < 1e-6
    assert out[-1][0] == 3.5

def test_list_clips_dedup():
    clips = list_clips(DEFAULT_CLIPS_DIR)
    assert len(clips) > 0

def test_render_makes_vertical_video(sample_audio, tmp_path):
    ass = str(tmp_path / "s.ass")
    open(ass, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,80,80,80,,TEST\n")
    dur = ffmpeg.probe_duration(sample_audio)
    ranges = [(0.0, dur)]
    out = str(tmp_path / "out.mp4")
    render(sample_audio, ass, ranges, out)
    assert os.path.exists(out)
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in r.stdout

def _mini_ass(path):
    open(path, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,TEST\n")

def test_pick_clips_seed_is_reproducible():
    import random
    from backend.pipeline.montage import _pick_clips, list_clips
    clips = list_clips()
    ranges = [(0.0, 2.0), (2.0, 4.0), (4.0, 6.0), (6.0, 8.0)]
    a = _pick_clips(ranges, clips, rng=random.Random(42))
    b = _pick_clips(ranges, clips, rng=random.Random(42))
    c = _pick_clips(ranges, clips, rng=random.Random(43))
    # mêmes seeds -> mêmes choix + mêmes offsets
    assert [(p, off, L, loop) for (p, off, L, loop) in a] == \
           [(p, off, L, loop) for (p, off, L, loop) in b]
    # seed différente -> choix différent (au moins un)
    assert a != c

def test_render_executes_plan(sample_audio, tmp_path):
    """Le renderer applique le plan du Director (zoom + punch + shake + transition)."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    plan = {
        "subtitles": [],
        "motion": [
            {"kind": "zoom_clip", "clip_index": 0, "zoom": 1.10},
            {"kind": "zoom_clip", "clip_index": 1, "zoom": 1.15},
            {"kind": "punch", "clip_index": 1, "at_local": 0.4, "zoom_to": 1.22, "dur": 0.35},
            {"kind": "shake", "clip_index": 1, "at_local": 0.4, "amp_px": 10, "dur": 0.3},
        ],
        "transitions": [{"kind": "fade_in", "clip_index": 1, "dur": 0.12}],
    }
    out = str(tmp_path / "plan.mp4")
    render(sample_audio, ass, [(0.0, dur * 0.5), (dur * 0.5, dur)], out, plan=plan)
    assert os.path.exists(out)
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in r.stdout

def test_render_boost_no_sfx(sample_audio, tmp_path):
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out = str(tmp_path / "boost.mp4")
    render(sample_audio, ass, [(0.0, dur)], out, boost=True, sfx_dir=str(tmp_path / "empty"))
    assert os.path.exists(out)
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in r.stdout

def test_render_boost_with_sfx(sample_audio, tmp_path):
    sfxdir = tmp_path / "sfx"
    (sfxdir / "Impacts").mkdir(parents=True); (sfxdir / "Whooshs").mkdir()
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=200:duration=0.3",
                str(sfxdir / "Impacts" / "boom.wav")])
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=600:duration=0.3",
                str(sfxdir / "Whooshs" / "swo.wav")])
    ass = str(tmp_path / "s2.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    events = [
        {"time": 0.0, "category": "Impacts", "gain_dB": -8, "fade_in_ms": 0, "fade_out_ms": 120, "duck_voice_dB": -1},
        {"time": dur * 0.5, "category": "Whooshs", "gain_dB": -12, "fade_in_ms": 10, "fade_out_ms": 80, "duck_voice_dB": 0},
    ]
    out = str(tmp_path / "boost2.mp4")
    render(sample_audio, ass, [(0.0, dur * 0.5), (dur * 0.5, dur)], out,
           boost=True, sfx_events=events, sfx_dir=str(sfxdir))
    assert os.path.exists(out)
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=codec_type", "-of", "csv=p=0", out])
    assert "audio" in r.stdout
