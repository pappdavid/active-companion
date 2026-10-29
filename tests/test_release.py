"""Release regressions for user-controlled text and a provider-free demo."""
import os
os.environ['COMPANION_LLM_DISABLE'] = '1'
from fastapi.testclient import TestClient
from companion.server import app
from tools.artifacts import render_card_html


def test_http_rejects_malformed_utterances_without_mutating_state():
    client = TestClient(app)
    before = client.get('/api/state').json()
    for body in [{'text': 42}, {'text': ''}, {'text': 'x' * 4001}, {'text': 'hello', 'speaker': 42}]:
        assert client.post('/api/utterance', json=body).status_code == 422
    assert client.get('/api/state').json() == before


def test_card_artifacts_escape_transcript_and_evidence():
    attack = '<img src=x onerror=alert(1)>'
    result = render_card_html({'title': attack, 'accent': 'blue', 'mode': 'retrieval',
        'trigger_excerpt': attack, 'gap': attack,
        'bullets': [{'text': attack, 'title': attack}]})
    assert attack not in result
    assert '&lt;img' in result


def test_browser_demo_is_derived_from_real_pipeline_without_providers(monkeypatch):
    from companion import llm
    def denied(*args, **kwargs):
        raise AssertionError('public replay must never call inference')
    monkeypatch.setattr(llm, 'generate_answer', denied)
    from tools.build_demo import demo_data, render_demo
    data = demo_data('test-build')
    assert data['build'] == 'test-build'
    assert len(data['scenarios']) == 4
    sales = next(s for s in data['scenarios'] if s['name'] == 'sales_negotiation')
    assert sales['events'][2]['card']['intent'] == 'pricing'
    assert all(e['card']['mode'] == 'retrieval' for s in data['scenarios'] for e in s['events'] if e['card'])
    data['scenarios'][0]['events'][0]['utterance'] = '</script><img src=x onerror=alert(1)>'
    html = render_demo(data)
    assert '</script><img' not in html
    assert 'test-build' in html


def test_model_cannot_cite_an_unknown_evidence_title(monkeypatch):
    from companion import llm
    monkeypatch.setattr(llm, 'chat', lambda *args: '{"bullets":[{"text":"An invented claim", "cite":"[Not in evidence]"}],"gap":null}')
    result, _ = llm.generate_answer('context', 'question', [{'title': 'Known source', 'text': 'Actual source'}], {})
    assert result is None


def test_model_keeps_only_bullets_citing_retrieved_titles(monkeypatch):
    from companion import llm
    monkeypatch.setattr(llm, 'chat', lambda *args: '{"bullets":[{"text":"Supported citation", "cite":"[Known source]"},{"text":"Invented citation", "cite":"Another source"}],"gap":null}')
    result, _ = llm.generate_answer('context', 'question', [{'title': 'Known source', 'text': 'Actual source'}], {})
    assert len(result['bullets']) == 1


def test_pricing_card_prioritizes_answer_snippets_over_headings_and_contacts():
    from companion.cards import compose_card
    card = compose_card('pricing', [{'title':'Sample guide', 'text':'## A lengthy sample pricing guide heading\n- Contact: Dana Reyes, VP Operations.\n- Pricing anchor: we offer $29 per seat each month.'}], 'What is the pricing per seat?')
    assert '$29' in card['bullets'][0]['text']
    assert all(not b['text'].startswith(('#', '- ')) for b in card['bullets'])
    assert all('Contact:' not in b['text'] for b in card['bullets'])
