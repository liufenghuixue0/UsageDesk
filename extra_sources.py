"""Read-only adapters feeding the same per-request records as Codex and Claude."""
import csv
import json
import math
import os
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from engine import normalize, number, timestamp


def roots(config, key, variable, defaults):
    if config.get(key):
        return [Path(path) for path in config[key]]
    value = os.environ.get(variable)
    return defaults if value is None else [Path(p.strip()).expanduser() for p in value.split(',') if p.strip()]


def discover(config):
    home = Path.home()
    local = Path(os.environ.get('LOCALAPPDATA', home))
    roaming = Path(os.environ.get('APPDATA', home / '.config'))
    for root in roots(config, 'opencode_homes', 'OPENCODE_DATA_DIR',
                      [Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'opencode']):
        yield from ((p, 'OpenCode') for p in root.glob('opencode*.db'))
        yield from ((p, 'OpenCode') for p in (root / 'storage/message').glob('*/*.json'))
    for root in roots(config, 'antigravity_homes', 'ANTIGRAVITY_DATA_DIR',
                      [*sorted((home / '.gemini').glob('antigravity*')), home / '.config/antigravity']):
        folder = root / 'conversations'
        if folder.is_dir() or config.get('antigravity_homes') or 'ANTIGRAVITY_DATA_DIR' in os.environ:
            yield from ((p, 'Antigravity') for p in (folder if folder.is_dir() else root).rglob('*.db'))
    for root in roots(config, 'dsh_homes', 'DSH_HOME', [home / '.dsh']):
        versions = {}
        for path in (root / 'sessions').rglob('session*.jsonl*'):
            match = re.fullmatch(r'session(?:\.v(\d+))?\.jsonl(?:\.(?:zstd|zst))?', path.name)
            if match:
                version = int(match[1] or 0)
                if path.parent not in versions or version > versions[path.parent][0]:
                    versions[path.parent] = (version, path)
        yield from ((p, 'DSH') for _, p in versions.values())
    exports, databases = [], []
    for path in roots(config, 'cursor_paths', 'CURSOR_USAGE_CSV', [local / 'UsageDesk/cursor']):
        if path.is_dir():
            exports.extend(path.glob('*.csv'))
            databases.extend(p for p in (path / 'state.vscdb', path / 'User/globalStorage/state.vscdb') if p.is_file())
        elif path.is_file() and path.suffix.lower() == '.csv':
            exports.append(path)
        elif path.is_file() and path.suffix.lower() in ('.vscdb', '.db'):
            databases.append(path)
    if not config.get('cursor_paths') and not databases:
        path = Path(os.environ.get('CURSOR_USAGE_DB', roaming / 'Cursor/User/globalStorage/state.vscdb'))
        if path.is_file():
            databases.append(path)
    yield from ((path, 'Cursor') for path in (exports or databases))


def obj(value):
    return value if isinstance(value, dict) else {}


def at(value):
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    return timestamp(value)


def dollars(value):
    try:
        amount = float(str(value).strip().lstrip('$').replace(',', ''))
        return amount if amount >= 0 and math.isfinite(amount) else None
    except ValueError:
        return None


def event(when, usage, session, model, identity, project=None, **extra):
    if when and usage['total']:
        return dict(at=when.isoformat(), usage=usage, session=str(session), model=str(model or '未知模型'),
                    identity=identity, project=str(project or '未知项目'), **extra)


def database(path):
    return closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1))


def split_usage(inp, out, read=0, write=0, reasoning=0):
    return normalize(dict(input_tokens=inp, output_tokens=out, cached_input_tokens=read,
                          cache_write_input_tokens=write, reasoning_output_tokens=reasoning), claude=True)


def opencode(path):
    def parse(data, mid, sid, created):
        tokens = obj(data.get('tokens'))
        cache, model = obj(tokens.get('cache')), obj(data.get('model'))
        reasoning = number(tokens.get('reasoning'))
        usage = split_usage(tokens.get('input'), number(tokens.get('output')) + reasoning,
                            cache.get('read'), cache.get('write'), reasoning)
        cost = dollars(data.get('cost'))
        return event(at(obj(data.get('time')).get('created') or created), usage, sid,
                     data.get('modelID') or model.get('id') or model.get('modelID'), mid,
                     obj(data.get('path')).get('root'), **({'reported_cost': cost} if cost else {}))

    if path.suffix == '.json':
        row = obj(json.loads(path.read_text(encoding='utf-8')))
        if row.get('role') == 'assistant':
            yield parse(row, row.get('id') or path.stem, row.get('sessionID') or path.parent.name, None)
        return
    with database(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'session_message' in tables:
            for mid, sid, raw, created in db.execute("SELECT id,session_id,data,time_created FROM session_message WHERE type='assistant'"):
                yield parse(obj(json.loads(raw)), mid, sid, created)
        if 'message' in tables:
            for mid, sid, raw, created in db.execute("SELECT id,session_id,data,time_created FROM message WHERE json_valid(data) AND json_extract(data,'$.role')='assistant'"):
                yield parse(obj(json.loads(raw)), mid, sid, created)


def cursor(path):
    if path.suffix.lower() == '.csv':
        seen = defaultdict(int)
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                get = row.get
                usage = split_usage(get('Input (w/o Cache Write)'), get('Output Tokens'),
                                    get('Cache Read'), get('Input (w/ Cache Write)'))
                # Preserve repeated identical rows in one export, while deduplicating overlapping exports.
                key = (get('Date'), get('Model'), get('Cloud Agent ID'), get('Automation ID'),
                       get('User'), get('Kind'), tuple(usage.values()), get('Cost'))
                seen[key] += 1
                when = at(get('Date'))
                yield event(when, usage, get('Cloud Agent ID') or get('Automation ID') or 'Cursor CSV',
                            get('Model'), (key, seen[key]), reported_cost=dollars(get('Cost')), reasoning_unknown=True)
        return
    with database(path) as db:
        for key, raw in db.execute("SELECT key,value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' AND json_valid(value)"):
            row = obj(json.loads(raw))
            if row.get('type') != 2:
                continue
            tokens = obj(row.get('tokenCount'))
            usage = normalize(dict(input_tokens=tokens.get('inputTokens'), output_tokens=tokens.get('outputTokens')))
            model = obj(row.get('modelInfo')).get('modelName') or row.get('modelType')
            yield event(at(row.get('createdAt')), usage, key.split(':')[1], model, key,
                        reported_cost=None, reasoning_unknown=True, cache_unknown=True)


def dsh_rows(path):
    if path.suffix in ('.zstd', '.zst'):
        from compression import zstd
        try:
            with zstd.open(path, 'rt', encoding='utf-8') as stream:
                yield from stream
        except (EOFError, zstd.ZstdError):
            # A writer can be appending the final frame while we read.
            return
    else:
        with path.open(encoding='utf-8') as stream:
            yield from stream


def dsh(path):
    sid, project, inherited, samples = path.parent.name, path.parent.parent.name, 0, {}
    attempts = defaultdict(int)
    for line in dsh_rows(path):
        try:
            row = obj(json.loads(line))
        except ValueError:
            continue
        if row.get('type') == 'session':
            header = obj(row.get('header')) or row
            sid, project = header.get('id') or sid, header.get('cwd') or project
            inherited = number(header.get('seedLength'))
            continue
        row = obj(row.get('event')) or row
        kind, data = row.get('type'), obj(row.get('data'))
        if kind == 'session/end-seed':
            samples.clear()
            attempts.clear()
        if number(row.get('seq')) < inherited:
            continue
        turn_step = (data.get('turn', row.get('turn')), data.get('step', row.get('step')))
        if kind == 'llm/retry-started':
            attempts[turn_step] += 1
        if kind not in ('assistant/message', 'assistant/attempt', 'assistant/chunk'):
            continue
        message = obj(data.get('message'))
        source = obj(message.get('source')) or obj(data.get('source'))
        tokens = obj(data.get('usage')) or obj(obj(data.get('chunk')).get('usage'))
        if not tokens and isinstance(data.get('stream'), list):
            for chunk in reversed(data['stream']):
                chunk = obj(chunk)
                tokens = obj(chunk.get('usage')) or obj(obj(chunk.get('chunk')).get('usage'))
                if tokens:
                    break
        if not tokens:
            continue
        model = obj(obj(source.get('replayState')).get('response')).get('responseModel') or source.get('model')
        key = (*turn_step, attempts[turn_step]) if None not in turn_step else (row.get('seq'),)
        previous = samples.get(key)
        rank = {'assistant/chunk': 0, 'assistant/attempt': 1, 'assistant/message': 2}[kind]
        if previous and previous[0] > rank:
            continue
        usage = split_usage(tokens.get('inputTokens'), tokens.get('outputTokens'),
                            tokens.get('cacheReadTokens'), tokens.get('cacheWriteTokens'), tokens.get('reasoningTokens'))
        when = at(row.get('time') or row.get('timestamp')) or (previous[1]['at'] if previous else None)
        record = event(at(when) if isinstance(when, str) else when, usage, sid,
                       model or (previous[1]['model'] if previous else None), (sid, key), project,
                       reasoning_unknown='reasoningTokens' not in tokens)
        if record:
            samples[key] = rank, record
    yield from (record for _, record in samples.values())


def varint(blob, offset):
    value = 0
    for shift in range(0, 70, 7):
        byte = blob[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError('Invalid protobuf varint')


def fields(blob):
    result = defaultdict(list)
    offset = 0
    while offset < len(blob):
        tag, offset = varint(blob, offset)
        wire = tag & 7
        if wire == 0:
            value, offset = varint(blob, offset)
        elif wire in (1, 2, 5):
            size, offset = varint(blob, offset) if wire == 2 else (8 if wire == 1 else 4, offset)
            value = blob[offset:offset + size]
            offset += size
            if offset > len(blob):
                raise ValueError('Truncated protobuf field')
        else:
            raise ValueError('Unsupported protobuf field')
        result[tag >> 3].append(value)
    return result


def field(values, key, default):
    return next((v for v in values.get(key, ()) if isinstance(v, type(default))), default)


def proto_time(blob):
    values = fields(blob)
    seconds = field(values, 1, 0)
    return at(seconds + min(field(values, 2, 0), 999999999) / 1e9) if seconds else None


def antigravity(path):
    sid, seen = path.stem, set()
    with database(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        fallback = None
        if 'trajectory_metadata_blob' in tables:
            for (blob,) in db.execute('SELECT data FROM trajectory_metadata_blob'):
                fallback = proto_time(field(fields(blob), 2, b'')) or fallback
        has_steps = False
        for table, sql in (('steps', 'SELECT idx,metadata FROM steps WHERE metadata IS NOT NULL'),
                           ('gen_metadata', 'SELECT idx,data FROM gen_metadata')):
            if table not in tables:
                continue
            for idx, blob in db.execute(sql):
                if not isinstance(blob, bytes):
                    continue
                try:
                    meta = fields(blob)
                    if table == 'steps':
                        info = fields(field(meta, 24, b''))
                        label = field(info, 12, b'') or field(info, 8, b'')
                        model_id = field(info, 1, 0)
                        stamp = field(meta, 8, b'') or field(meta, 1, b'')
                        usage_field, retry_field = 9, 28
                    else:
                        meta = fields(field(meta, 1, b''))
                        label = field(meta, 19, b'') or field(meta, 21, b'')
                        model_id = field(meta, 3, 0)
                        stamp = field(fields(field(meta, 9, b'')), 4, b'')
                        usage_field, retry_field = 4, 17
                    when = proto_time(stamp) or fallback
                    blobs = [field(meta, usage_field, b'')] + [field(fields(b), 2, b'') for b in meta.get(retry_field, []) if isinstance(b, bytes)]
                    for index, raw in enumerate(blobs):
                        tokens = fields(raw)
                        ids = {(n, field(tokens, n, b'')) for n in (7, 11, 12) if field(tokens, n, b'')}
                        if ids & seen or (not ids and table == 'gen_metadata' and has_steps):
                            continue
                        reason = field(tokens, 9, 0)
                        usage = split_usage(field(tokens, 2, 0), max(field(tokens, 3, 0), field(tokens, 10, 0)+reason),
                                            field(tokens, 5, 0), field(tokens, 4, 0), reason)
                        mid = field(tokens, 1, 0) or model_id
                        known_ids = {246:'gemini-2.5-pro', 312:'gemini-2.5-flash', 330:'gemini-2.5-flash-lite', 1050:'gemini-3.1-flash-lite'}
                        model = label.decode('utf-8', 'replace').strip() or (known_ids.get(mid, f'antigravity-model-{mid}') if mid else None)
                        identity = (sid, min(ids) if ids else (table, idx, index))
                        record = event(when, usage, sid, model, identity)
                        if record:
                            seen.update(ids)
                            has_steps |= table == 'steps'
                            yield record
                except (ValueError, IndexError):
                    continue


def read_source(path, source):
    events, diagnostics = [], {}
    parser = {'OpenCode': opencode, 'Cursor': cursor, 'DSH': dsh, 'Antigravity': antigravity}[source]
    try:
        for record in parser(path):
            if record:
                record['source'] = source
                events.append(record)
    except (OSError, ValueError, TypeError, IndexError, sqlite3.Error, EOFError, ImportError):
        diagnostics['unreadable_files'] = 1
    # The envelope identifies the source file, not the sessions contained in it.
    return dict(session=str(path), parent=None, events=events, diagnostics=diagnostics)
