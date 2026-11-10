import json, sys
want = ["C:\\Users\\Jane Doe\\AVS\\inbox\\Mike's video & more.mp4", '{"text": "it\'s here", "n": 2}']
got = sys.argv[1:]
print('MATCH' if got == want else 'DIFF ' + json.dumps(got))
