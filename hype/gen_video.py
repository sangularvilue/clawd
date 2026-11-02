"""Generate the Washington / Lincoln hero clips with a text-to-video model on Replicate.

    REPLICATE_API_TOKEN=... python3 gen_video.py                 # the two hero clips
    python3 gen_video.py --keys washington_jetski --model google/veo-3-fast

Clips land in hype/generated/<key>.mp4, where edits/main.py picks them up in
place of the drawn shots. The model's input schema is read at run time, so any
text-to-video model on Replicate works; if one refuses or fails, the next in
MODELS is tried.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'generated')
API = 'https://api.replicate.com/v1'
MODELS = ['google/veo-3-fast', 'google/veo-3', 'minimax/hailuo-02', 'kwaivgi/kling-v2.1-master',
          'bytedance/seedance-1-pro']

STYLE = ('Epic action-movie shot, photorealistic, anamorphic 35mm film look, dramatic backlight, lens flares, '
         'flying embers, slow motion, no text, no captions, no watermark.')
PROMPTS = {
    'washington_trex': (
        'Low-angle tracking shot: George Washington in his blue Continental Army coat and black tricorn hat rides a '
        'charging Tyrannosaurus rex across a burning battlefield at sunset, holding a huge American flag high so it '
        'whips in the wind. The T-rex roars. A volcano erupts behind them, explosions bloom on the horizon, dust '
        'kicks up from its feet. ' + STYLE),
    'lincoln_chopper': (
        'Tracking shot alongside Abraham Lincoln in his black frock coat, stovepipe hat and aviator sunglasses, '
        'riding a chrome chopper motorcycle with tall ape-hanger handlebars down a desert highway at golden hour. '
        'An American flag streams from the back of the bike, his coat tails flap, sparks fly off the exhaust and '
        'explosions erupt on the horizon behind him. ' + STYLE),
    # optional extras
    'washington_jetski': (
        'George Washington stands heroically on a roaring jet ski, one boot forward, crossing the icy Delaware River '
        'at dawn, spray exploding around him, a giant American flag flying behind, fireworks bursting in the sky. '
        + STYLE),
    'lincoln_eagle': (
        'Abraham Lincoln in his stovepipe hat rides a giant bald eagle soaring past Mount Rushmore, wings spread wide, '
        'fighter jets in formation behind them trailing red, white and blue smoke. ' + STYLE),
}
NEGATIVE = 'text, captions, watermark, logo, blurry, distorted face, extra limbs, cartoon'


def call(method, url, body=None):
    headers = {'Content-Type': 'application/json'}
    tok = os.environ.get('REPLICATE_API_TOKEN')
    if tok:
        headers['Authorization'] = 'Bearer ' + tok
    if method == 'POST':
        headers['Prefer'] = 'wait=60'
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError('%s %s -> HTTP %d: %s' % (method, url, e.code, e.read()[:300].decode('utf8', 'replace')))


def build_input(schema, prompt):
    props = schema.get('properties', {})
    enums = {k: (v.get('enum') or [s for a in v.get('allOf', []) for s in
                                    schema.get('_defs', {}).get(a.get('$ref', '').split('/')[-1], {}).get('enum', [])])
             for k, v in props.items()}
    inp = {'prompt': prompt}
    if 'aspect_ratio' in props:
        inp['aspect_ratio'] = '16:9'
    if 'negative_prompt' in props:
        inp['negative_prompt'] = NEGATIVE
    if 'duration' in props:
        opts = enums.get('duration') or []
        if opts:
            nums = [o for o in opts if isinstance(o, (int, float)) and o <= 8]
            inp['duration'] = max(nums) if nums else opts[0]
        else:
            inp['duration'] = min(8, props['duration'].get('maximum', 8))
    if 'resolution' in props:
        opts = enums.get('resolution') or []
        if '1080p' in opts or not opts:
            inp['resolution'] = '1080p'
    for k in ('generate_audio', 'audio', 'enable_audio'):
        if k in props:
            inp[k] = False
    missing = [k for k in schema.get('required', []) if k not in inp]
    return inp, missing


def generate(model, key, prompt):
    m = call('GET', '%s/models/%s' % (API, model))
    comp = m['latest_version']['openapi_schema']['components']['schemas']
    schema = dict(comp['Input'], _defs=comp)
    inp, missing = build_input(schema, prompt)
    if missing:
        raise RuntimeError('%s needs inputs this script does not provide: %s' % (model, missing))
    print('  %s: %s' % (model, {k: v for k, v in inp.items() if k != 'prompt'}), flush=True)
    p = call('POST', '%s/models/%s/predictions' % (API, model), {'input': inp})
    t0 = time.time()
    while p['status'] not in ('succeeded', 'failed', 'canceled'):
        time.sleep(5)
        p = call('GET', p['urls']['get'])
        print('\r  %s %ds' % (p['status'], time.time() - t0), end='', flush=True)
    print()
    if p['status'] != 'succeeded':
        raise RuntimeError('%s %s: %s' % (model, p['status'], p.get('error')))
    url = p['output'][0] if isinstance(p['output'], list) else p['output']
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, key + '.mp4')
    urllib.request.urlretrieve(url, path)
    with open(path + '.json', 'w') as f:
        json.dump(dict(model=model, prediction=p['id'], input=inp, metrics=p.get('metrics')), f, indent=1)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keys', nargs='+', default=['washington_trex', 'lincoln_chopper'], choices=list(PROMPTS))
    ap.add_argument('--model', help='try this model first')
    ap.add_argument('--force', action='store_true', help='regenerate even if the clip exists')
    a = ap.parse_args()
    models = ([a.model] if a.model else []) + [m for m in MODELS if m != a.model]
    for key in a.keys:
        if os.path.exists(os.path.join(OUT, key + '.mp4')) and not a.force:
            print(key, 'exists, skipping (--force to redo)')
            continue
        print(key)
        for model in models:
            try:
                print('  ->', generate(model, key, PROMPTS[key]))
                break
            except Exception as e:  # refusal, missing model, bad schema: try the next one
                print('  failed:', e)
        else:
            sys.exit('no model produced ' + key)


if __name__ == '__main__':
    main()
