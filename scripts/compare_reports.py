"""Compare matching benchmark runs; exit 1 if any check regresses."""
import argparse
import json
from pathlib import Path


def compare(a, b):
    for key in ('schema_version', 'benchmark_version'):
        if key not in a or a[key] != b.get(key):
            raise ValueError(f'Incompatible {key}')
    left = {r['scenario']: r for r in a['results']}
    right = {r['scenario']: r for r in b['results']}
    if not left or set(left) != set(right) or len(left) != len(a['results']) or len(right) != len(b['results']):
        raise ValueError('Scenario sets must match without duplicates')
    rows = []
    for name in sorted(left):
        old, new = left[name], right[name]
        if set(old['checks']) != set(new['checks']): raise ValueError('Check sets differ')
        if any(type(v) is not bool for r in (old,new) for v in r['checks'].values()): raise ValueError('Checks must be booleans')
        rows.append({'scenario':name, 'regressed':[k for k in old['checks'] if old['checks'][k] and not new['checks'][k]], 'improved':[k for k in old['checks'] if not old['checks'][k] and new['checks'][k]], 'calls_before':old['calls'], 'calls_after':new['calls']})
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('before',type=Path);p.add_argument('after',type=Path)
    args=p.parse_args()
    try: rows=compare(json.loads(args.before.read_text()),json.loads(args.after.read_text()))
    except (ValueError,KeyError,TypeError,OSError) as exc: p.exit(2,f'Invalid reports: {exc}\n')
    print('| Scenario | Improvements | Regressions | Calls before → after |\n| --- | --- | --- | --- |')
    for r in rows: print(f"| {r['scenario']} | {len(r['improved'])} | {len(r['regressed'])} | {r['calls_before']} → {r['calls_after']} |")
    print('\nFixture comparison only; not a statistical model ranking.')
    return 1 if any(r['regressed'] for r in rows) else 0

if __name__=='__main__': raise SystemExit(main())
