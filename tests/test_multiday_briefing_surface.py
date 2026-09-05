from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_multiday_briefing_surface_present():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "js/app.js").read_text(encoding="utf-8")
    assert 'id="briefing-finalized-trend"' in html
    assert 'id="briefing-provisional-trend"' in html
    assert 'Completed theatrical days use finalized pre-show observations only.' in html
    assert 'function renderBriefingMultiDay' in js
    assert "product.finalPreShowState?.status==='complete'" in js
    assert 'product.finalPreShowSessions || []' in js
