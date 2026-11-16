from piplayer.ytm import hires

GOOGLE = "https://yt3.googleusercontent.com/abc123=w120-h120-l90-rj"


def test_hires_upsizes_google_covers():
    assert hires(GOOGLE) == "https://yt3.googleusercontent.com/abc123=w544-h544-l90-rj"
    assert hires(GOOGLE, 800).endswith("=w800-h800-l90-rj")


def test_hires_leaves_other_urls_alone():
    other = "https://i.ytimg.com/vi/xyz/hqdefault.jpg?sqp=w120-h120"
    assert hires(other) == other
    assert hires(None) is None
    assert hires("") == ""
