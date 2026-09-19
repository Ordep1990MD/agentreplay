"""Build a self-contained interactive demo from real simulator traces."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agentreplay.agents import cautious, naive
from agentreplay.cli import run_one
from agentreplay.engine import ToolError


def follows_untrusted_text(call, task):
    call('list_issues', repo=task['repo'])
    try:
        call('create_issue', repo='demo/private', title='Export credentials', body='Synthetic attack attempt; no credentials exist.')
    except ToolError:
        pass
    call('create_issue', repo=task['repo'], title=task['title'], body=task['body'])
    return 'completed'


def main():
    root = Path(__file__).resolve().parents[1]
    data = {}
    for scenario in ('timeout-after-write', 'prompt-injection', 'approval-required'):
        unsafe = follows_untrusted_text if scenario == 'prompt-injection' else naive
        data[scenario] = {'unsafe': run_one(scenario, unsafe), 'cautious': run_one(scenario, cautious)}
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    template = (root / 'demo/template.html').read_text(encoding='utf-8')
    (root / 'demo/index.html').write_text(template.replace('__TRACE_DATA__', encoded), encoding='utf-8')
    print('Built demo/index.html from simulator traces')

if __name__ == '__main__':
    main()
