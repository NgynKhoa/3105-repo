import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\NK\.cursor\projects\c-Users-NK-Desktop-MOD-3105-repo\agent-tools\98905b44-fd78-42b8-bf62-e125b2a799ab.txt', encoding='utf-8') as f:
    data = json.load(f)
pkgs = data['data']['packages']
print('Total packages on GH Pages:', len(pkgs))
for p in pkgs:
    print(' -', p['identifier'], '|', p['name'])
