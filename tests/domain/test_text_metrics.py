from xseo.domain.analysis.text_metrics import estimate_pixel_width


def test_empty_text_has_zero_width():
    assert estimate_pixel_width("") == 0
    assert estimate_pixel_width(None) == 0


def test_wide_glyphs_measure_wider_than_narrow_ones_at_equal_length():
    wide = estimate_pixel_width("W" * 20)
    narrow = estimate_pixel_width("i" * 20)

    assert wide > narrow


def test_unknown_characters_fall_back_to_default_width():
    # An emoji is not in the table; it should still contribute a positive width.
    assert estimate_pixel_width("★") > 0
