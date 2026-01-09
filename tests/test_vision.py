from __future__ import annotations

from autos.vision import build_title_from_caption, merge_captions


def test_merge_captions_picks_longest() -> None:
    captions = ["A cat.", "A cat sitting on a chair in a sunny room."]
    assert merge_captions(captions) == "A cat sitting on a chair in a sunny room."


def test_build_title_from_caption_limits_words() -> None:
    caption = "two detectives question a nervous man in a dim room"
    title = build_title_from_caption(caption, max_words=5)
    assert title == "Two detectives question a nervous"
