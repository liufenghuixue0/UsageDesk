"""Read-only usage adapters. Never persist prompts or modify source logs."""
from __future__ import annotations
import json
import math
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

KEYS = ('input', 'cached', 'uncached', 'output', 'reasoning', 'normal', 'total', 'cache_write')
PRICE_URL = 'https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json'

def number(value):
    try:
        return max(0, int(value))
    except (ValueError, TypeError, OverflowError):
        return 0

def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def normalize(raw, claude=False):
    raw = raw if isinstance(raw, dict) else {}
    details = raw.get('input_tokens_details') or raw.get('prompt_tokens_details') or {}
    out_details = raw.get('output_tokens_details') or raw.get('completion_tokens_details') or {}
    inp = number(raw.get('input_tokens', raw.get('prompt_tokens', raw.get('input', 0))))
    cache = number(raw.get('cached_input_tokens', raw.get('cache_read_input_tokens', details.get('cached_tokens', 0))))
    write = number(raw.get('cache_creation_input_tokens', raw.get('cache_write_input_tokens', 0)))
    # Claude input_tokens excludes cache reads and writes; Codex input includes them.
    if claude:
        inp += cache + write
    cache = min(inp, cache)
    write = min(inp-cache, write)
    out = number(raw.get('output_tokens', raw.get('completion_tokens', raw.get('output', 0))))
    reason = min(out, number(raw.get('reasoning_output_tokens', raw.get('reasoning_tokens', out_details.get('reasoning_tokens', 0)))))
    return dict(input=inp, cached=cache, uncached=inp-cache, output=out,
                reasoning=reason, normal=out-reason, total=inp+out, cache_write=write)

def lines(path, diagnostics):
    try:
        with path.open('r', encoding='utf-8', errors='replace') as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        yield row
                except (ValueError, RecursionError):
                    if line.strip():
                        diagnostics['invalid_lines'] += 1
    except OSError:
        diagnostics['unreadable_files'] += 1

def codex_session_titles(homes):
    """Read display names from each configured Codex session index."""
    entries = {}
    for home in homes:
        index = Path(home).expanduser() / 'session_index.jsonl'
        for row in lines(index, defaultdict(int)):
            session_id = row.get('id')
            title = row.get('thread_name')
            if not isinstance(session_id, str) or not isinstance(title, str) or not title.strip():
                continue
            updated = timestamp(row.get('updated_at')) or datetime.min.replace(tzinfo=timezone.utc)
            if session_id not in entries or updated >= entries[session_id][0]:
                entries[session_id] = (updated, title.strip())
    return {session_id: entry[1] for session_id, entry in entries.items()}


def parse_codex(path):
    diagnostics = defaultdict(int)
    sid = path.stem[-36:] if path.stem.startswith('rollout-') else path.stem
    project, model, tier, parent = '未知项目', '未知模型', 'standard', None
    previous, seen, events, records, compacted = None, set(), [], {}, set()
    covered_records, latest_record = set(), None
    for row in lines(path, diagnostics):
        kind, p = row.get('type'), row.get('payload')
        if not isinstance(p, dict):
            continue
        if kind == 'session_meta':
            sid, project = str(p.get('id') or sid), str(p.get('cwd') or project)
            parent = p.get('forked_from_id') or p.get('forked_from') or p.get('parent_thread_id')
            if isinstance(parent, dict):
                parent = parent.get('id')
        if kind == 'turn_context':
            model = p.get('model') or p.get('model_name') or model
            tier = p.get('service_tier') or 'standard'
            project = p.get('cwd') or project
        if p.get('type') == 'thread_settings_applied':
            settings = p.get('thread_settings') or p
            model = settings.get('model') or model
            if 'service_tier' in settings:
                tier = settings.get('service_tier') or 'standard'
        dt = timestamp(row.get('timestamp'))
        if not dt:
            continue
        if kind == 'compacted':
            if p.get('compaction_response_id'):
                compacted.add(p['compaction_response_id'])
        if kind == 'token_usage_record' and isinstance(p.get('usage'), dict):
            rid = p.get('response_id')
            if rid:
                records[rid] = dict(at=dt.isoformat(), model=p.get('model') or model,
                    tier=p.get('service_tier') or tier, usage=normalize(p['usage']), identity=rid,
                    thread_usage=normalize(p['thread_token_usage']) if isinstance(p.get('thread_token_usage'),dict) else None)
                latest_record = rid
        if kind != 'event_msg' or p.get('type') != 'token_count':
            continue
        info = p.get('info')
        if not isinstance(info, dict):
            continue
        current = normalize(info['total_token_usage']) if isinstance(info.get('total_token_usage'), dict) else None
        repeated = current is not None and current == previous
        if repeated:
            continue
        raw_last = info.get('last_token_usage')
        if isinstance(raw_last, dict):
            usage = normalize(raw_last)
        elif current is not None:
            if previous is None or current['total'] < previous['total']:
                usage = current.copy()
            else:
                delta = {k: max(0, current[k]-previous[k]) for k in KEYS}
                usage = normalize(dict(input_tokens=delta['input'], cached_input_tokens=delta['cached'],
                    cache_write_input_tokens=delta['cache_write'], output_tokens=delta['output'], reasoning_output_tokens=delta['reasoning']))
        else:
            continue
        if current is not None:
            previous = current
        if latest_record in records:
            record = records[latest_record]
            if record['usage'] == usage or (current is not None and record.get('thread_usage') == current):
                covered_records.add(latest_record)
        identity = (dt.isoformat(), json.dumps(usage, sort_keys=True))
        if identity in seen or not usage['total']:
            continue
        seen.add(identity)
        events.append(dict(at=dt.isoformat(), model=info.get('model') or p.get('model') or model,
                           tier=info.get('service_tier') or tier, usage=usage, identity=None))
    # Only matched compactions are additional usage; arbitrary request records may duplicate totals.
    events.extend(records[rid] for rid in compacted if rid in records and rid not in covered_records)
    for e in events:
        e.update(source='Codex', session=sid, project=project)
    return dict(session=sid, parent=parent, events=sorted(events,key=lambda e:e['at']), diagnostics=dict(diagnostics))

def parse_claude(path):
    diagnostics = defaultdict(int)
    events, seen = [], set()
    for row in lines(path, diagnostics):
        # Claude progress wrappers contain nested assistant records.
        data = row.get('data')
        if isinstance(data, dict) and isinstance(data.get('message'), dict) and 'message' in data['message']:
            row = data['message']
        msg = row.get('message')
        if not isinstance(msg, dict) or not isinstance(msg.get('usage'), dict):
            continue
        dt = timestamp(row.get('timestamp'))
        if not dt:
            continue
        identity = (msg.get('id'), row.get('requestId'))
        if any(identity):
            if identity in seen:
                continue
            seen.add(identity)
        else:
            identity = (dt.isoformat(), json.dumps(msg['usage'], sort_keys=True))
            if identity in seen:
                continue
            seen.add(identity)
        u = normalize(msg['usage'], claude=True)
        if u['total']:
            events.append(dict(at=dt.isoformat(), source='Claude Code', session=row.get('sessionId') or path.stem,
                project=row.get('cwd') or path.parent.name, model=msg.get('model') or '未知模型',
                tier='standard', usage=u, identity='claude:'+str(identity),
                cache_creation=msg['usage'].get('cache_creation') or {}))
    return dict(session=path.stem, parent=None, events=events, diagnostics=dict(diagnostics))

def event_identity(event):
    identity = event.get('identity')
    if identity:
        return event['source'], identity
    return event['source'], event['session'], event['at'], tuple(event['usage'].values())


class Store:
    def __init__(self, config):
        self.config, self.cache, self.lock = config, {}, threading.RLock()

    def collect(self):
        from extra_sources import discover, read_source

        with self.lock:
            files, roots = {}, []
            codex_homes = self.config['codex_homes'] or [os.environ.get('CODEX_HOME') or Path.home()/'.codex']
            codex_titles = codex_session_titles(codex_homes)
            claude_homes = self.config['claude_homes'] or [os.environ.get('CLAUDE_CONFIG_DIR') or Path.home()/'.claude']
            for home in codex_homes:
                root = Path(home).expanduser()
                roots.extend([(root/'sessions', 'Codex'), (root/'archived_sessions', 'Codex')])
            for home in claude_homes:
                roots.append((Path(home).expanduser()/'projects', 'Claude Code'))
            missing = [str(p) for p, _ in roots if not p.exists()]
            for root, source in roots:
                if root.is_dir():
                    for p in root.rglob('*.jsonl'):
                        files[str(p.resolve())] = (p, source)
            for p, source in discover(self.config):
                files[str(p.resolve())] = (p, source)
            results, diagnostics = [], defaultdict(int)
            for name, (p, source) in sorted(files.items()):
                try:
                    stat = p.stat()
                except OSError:
                    diagnostics['unreadable_files'] += 1
                    continue
                stamp = (stat.st_size, stat.st_mtime_ns)
                if p.suffix in ('.db', '.vscdb'):
                    try:
                        wal = p.with_name(p.name + '-wal').stat()
                        stamp += (wal.st_size, wal.st_mtime_ns)
                    except FileNotFoundError:
                        pass
                    except OSError:
                        diagnostics['unreadable_files'] += 1
                        continue
                cached = self.cache.get(name)
                if not cached or cached[0] != stamp or cached[1]['diagnostics'].get('unreadable_files'):
                    parser = {'Codex': parse_codex, 'Claude Code': parse_claude}.get(source)
                    cached = (stamp, parser(p) if parser else read_source(p, source))
                    self.cache[name] = cached
                results.append((source, cached[1]))
                for k, v in cached[1]['diagnostics'].items():
                    diagnostics[k] += v
            self.cache = {k:v for k,v in self.cache.items() if k in files}
            sessions = {}
            codex_events = defaultdict(dict)
            for source, record in results:
                key = (source, record['session'])
                if source == 'Codex':
                    # A shorter rollout can contain requests missing from a longer copy.
                    merged = sessions.setdefault(key, dict(record, events=[]))
                    if not merged['parent']:
                        merged['parent'] = record['parent']
                    events_by_id = codex_events[key]
                    for event in record['events']:
                        events_by_id.setdefault(event_identity(event), event)
                elif key not in sessions or len(record['events']) > len(sessions[key]['events']):
                    sessions[key] = record
            for key, events_by_id in codex_events.items():
                # Compare fork replay against the merged, chronological parent history.
                sessions[key]['events'] = sorted(events_by_id.values(), key=lambda event: event['at'])
            all_events, identities = [], set()
            for (source, _), r in sessions.items():
                events = r['events']
                parent = sessions.get((source, r['parent'])) if isinstance(r['parent'], str) else None
                if parent:
                    prefix = [e for e in parent['events'] if not e.get('identity')]
                    index = 0
                    filtered = []
                    for e in events:
                        if not e.get('identity') and index < len(prefix) and e['usage'] == prefix[index]['usage']:
                            index += 1
                            diagnostics['fork_replay_skipped'] += 1
                        else:
                            filtered.append(e)
                            if not e.get('identity'):
                                index = len(prefix)
                    events = filtered
                elif r['parent']:
                    diagnostics['fork_parent_missing'] += 1
                for e in events:
                    identity = event_identity(e)
                    if identity in identities:
                        continue
                    identities.add(identity)
                    if source == 'Codex':
                        e = dict(e, session_title=codex_titles.get(e['session'], ''))
                    all_events.append(e)
            return sorted(all_events, key=lambda e:e['at']), dict(files=len(files), missing=missing, **diagnostics)

class Prices:
    def __init__(self, path, overrides=None):
        self.data = json.loads(Path(path).read_text(encoding='utf-8'))
        self.overrides = overrides or {}

    def cost(self, e):
        model, u = e['model'], e['usage']
        if model in self.overrides:
            p = self.overrides[model]
            write = u['cache_write']
            return ((u['uncached']-write)*p['input'] + u['cached']*p['cached'] +
                    u['output']*p['output'] + write*p.get('cache_write', p['input']))/1e6
        if 'reported_cost' in e:
            return e['reported_cost']
        rows = self.data.get('models', self.data)
        row = next((rows[key] for key in (model, 'openai/'+model, 'anthropic/'+model,
                    'gemini/'+model, 'deepseek/'+model) if key in rows), None)
        if not isinstance(row, dict):
            return None
        tier = e.get('tier', 'standard')
        tier = {'fast':'priority','standard':'','default':'','auto':'',None:''}.get(tier,tier)
        if tier not in ('','priority','flex','ultrafast'):
            return None
        suffix = ''
        thresholds = sorted((int(n)*1000, n) for n in re.findall(r'input_cost_per_token_above_(\d+)k_tokens', ' '.join(row)))
        for limit, n in thresholds:
            if u['input'] > limit:
                suffix = f'_above_{n}k_tokens'
        def rate(key):
            tier_suffix = '_'+tier if tier else ''
            v = row.get(key+suffix+tier_suffix, row.get(key+tier_suffix))
            return v if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 else None
        ir, cr, out, wr = (rate(k) for k in ('input_cost_per_token', 'cache_read_input_token_cost', 'output_cost_per_token', 'cache_creation_input_token_cost'))
        terms = [(u['uncached']-u['cache_write'], ir), (u['cached'], cr), (u['output'], out)]
        write = u['cache_write']
        if write:
            creation = e.get('cache_creation', {})
            hour = min(write, number(creation.get('ephemeral_1h_input_tokens')))
            terms.extend([(write-hour, wr), (hour, rate('cache_creation_input_token_cost_above_1hr'))])
        if any(n and r is None for n,r in terms):
            return None
        return sum(n*(r or 0) for n,r in terms)

def empty():
    return dict(**{k:0 for k in KEYS}, cost=0.0, unpriced_tokens=0, unpriced_events=0, events=0,
                reasoning_unknown_events=0, cache_unknown_events=0)

def add(target, e):
    for k in KEYS:
        target[k] += e['usage'][k]
    target['events'] += 1
    if e.get('cost') is None:
        target['unpriced_events'] += 1
        target['unpriced_tokens'] += e['usage']['total']
    else:
        target['cost'] += e['cost']
    if e['source'] == 'Claude Code' or e.get('reasoning_unknown'):
        target['reasoning_unknown_events'] += 1
    if e.get('cache_unknown'):
        target['cache_unknown_events'] += 1

def report(events, diagnostics, prices, query=None, now=None):
    query = query or {}
    now = now or datetime.now().astimezone()
    # Explicit fixed offset makes Windows timezone handling independent of optional tzdata.
    offset = int(query.get('utc_offset', '480'))
    tz = timezone(timedelta(minutes=offset))
    today = now.astimezone(tz).date()
    selected = []
    for event in events:
        if query.get('source') and event['source'] != query['source']:
            continue
        if query.get('project') and event['project'] != query['project']:
            continue
        if query.get('model') and event['model'] != query['model']:
            continue
        e = dict(event)
        e['day'] = timestamp(e['at']).astimezone(tz).date().isoformat()
        e['cost'] = prices.cost(e)
        selected.append(e)
    latest = max(selected, key=lambda e:e['at'], default=None)
    overview = {k:empty() for k in ('today', 'week', 'month', 'latest')}
    week_start = (today-timedelta(days=today.weekday())).isoformat()
    for e in selected:
        if e['day'] == today.isoformat(): add(overview['today'], e)
        if week_start <= e['day'] <= today.isoformat(): add(overview['week'], e)
        if e['day'][:7] == today.isoformat()[:7] and e['day'] <= today.isoformat(): add(overview['month'], e)
        if latest and (e['source'], e['session']) == (latest['source'], latest['session']): add(overview['latest'], e)
    filtered = [e for e in selected if (not query.get('since') or e['day'] >= query['since']) and (not query.get('until') or e['day'] <= query['until'])]
    range_start = query.get('since') or min((e['day'] for e in filtered), default=query.get('until') or today.isoformat())
    range_end = query.get('until') or max(range_start, max((e['day'] for e in filtered), default=today.isoformat()))
    groups = {key:{} for key in ('daily', 'weekly', 'monthly', 'projects', 'sessions', 'models')}
    daily_models = {}
    total = empty()
    for e in filtered:
        add(total, e)
        model_bucket = daily_models.setdefault((e['day'], e['model']), dict(key=e['day'], model=e['model'], **empty()))
        add(model_bucket, e)
        day = datetime.fromisoformat(e['day']).date()
        keys = dict(daily=e['day'], weekly=(day-timedelta(days=day.weekday())).isoformat(), monthly=e['day'][:7],
                    projects=e['project'], sessions=e['source']+' / '+e['session'], models=e['model'])
        for dimension, key in keys.items():
            bucket = groups[dimension].setdefault(key, dict(key=key, **empty(), first=e['at'], last=e['at'], sources=set()))
            if dimension == 'sessions' and e['source'] == 'Codex':
                name = e.get('session_title') or e['session'][:8]
                bucket['label'] = f"{e['source']} / {name}"
            add(bucket, e)
            bucket['first'], bucket['last'] = min(bucket['first'], e['at']), max(bucket['last'], e['at'])
            bucket['sources'].add(e['source'])
    for dimension, values in groups.items():
        for v in values.values(): v['sources'] = sorted(v['sources'])
        groups[dimension] = sorted(values.values(), key=(lambda v:v['key']) if dimension in ('daily','weekly','monthly') else (lambda v:-v['total']))
    return dict(generated_at=datetime.now(timezone.utc).isoformat(), today=today.isoformat(), utc_offset=offset,
        overview=overview, latest_session=(latest['source']+' / '+latest['session']) if latest else None,
        total=total, groups=groups, daily_models=sorted(daily_models.values(), key=lambda row:(row['key'], row['model'])),
        diagnostics=diagnostics, date_range=dict(since=range_start, until=range_end),
        filters={k:sorted({e[k] for e in events}) for k in ('source','project','model')},
        price_updated=prices.data.get('updated_at', '未知'), unpriced_models=sorted({e['model'] for e in filtered if e['cost'] is None}))

def default_config():
    return dict(codex_homes=[], claude_homes=[], prices={})
