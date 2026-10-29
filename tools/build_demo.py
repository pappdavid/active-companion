"""Build a static, inference-free replay from the actual retrieval pipeline."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from companion import config
from companion.pipeline import CompanionPipeline


def demo_data(build: str) -> dict:
    scenarios = []
    for path in sorted(config.SCENARIO_DIR.glob('*.json')):
        scenario = json.loads(path.read_text())
        pipe = CompanionPipeline(llm=None)
        pipe.ingest_utterances(scenario['utterances'])
        scenarios.append({'name': scenario['name'], 'events': pipe.events,
                          'gold': scenario['gold']})
    return {'build': build, 'scenarios': scenarios}


def render_demo(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return (config.ROOT / 'demo' / 'index.html').read_text().replace('__TRACE_JSON__', payload)


if __name__ == '__main__':
    build = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=config.ROOT, text=True).strip()
    out = config.ROOT / 'demo-dist'
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(render_demo(demo_data(build)))
    (out / 'release.json').write_text(json.dumps({'commit': build, 'mode': 'scripted-retrieval-replay', 'inference': False}))
    print(f'Built {out} from {build}; no inference calls.')
