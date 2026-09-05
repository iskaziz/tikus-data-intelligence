from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_share_link_control_and_hash_fields_are_present():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    js = (ROOT / 'js' / 'app.js').read_text(encoding='utf-8')
    assert 'id="comparison-copy-link"' in html
    for field in ("'date'", "'time'", "'exhibitor'", "'state'", "'obs'", "'replay'", "'compare'"):
        assert f"params.set({field}" in js or f"params.get({field}" in js
    assert 'history.replaceState' in js
    assert 'hashchange' in js
