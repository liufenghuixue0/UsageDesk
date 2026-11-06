"""Download a build-time offline snapshot, using the same public source as ccusage."""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from engine import PRICE_URL

if __name__ == '__main__':
    with urllib.request.urlopen(PRICE_URL,timeout=60) as response:
        raw = json.load(response)
    models = {k:v for k,v in raw.items() if isinstance(v,dict) and any(x in k.lower() for x in ('gpt','claude','o1','o3','o4','codex','gemini','deepseek')) and 'input_cost_per_token' in v}
    if len(models)<10: raise ValueError('Invalid pricing response')
    Path(__file__).with_name('prices.json').write_text(json.dumps(dict(updated_at=datetime.now(timezone.utc).isoformat(),source=PRICE_URL,models=models),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Saved {len(models)} model prices')
