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
