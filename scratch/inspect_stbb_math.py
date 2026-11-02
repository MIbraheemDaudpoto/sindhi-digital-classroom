import json

with open('data/stbb_math_6_complete.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

with open('scratch/math_exercises_sample.json', 'w', encoding='utf-8') as out:
    json.dump(d.get('exercises', [])[:3], out, ensure_ascii=False, indent=2)

print('Wrote sample exercises to scratch/math_exercises_sample.json')
