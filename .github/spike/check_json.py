import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print('MATCH' if d == {'text': "it's here", 'n': 2} else 'DIFF ' + json.dumps(d))
