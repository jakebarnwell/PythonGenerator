import glob, pymongo

index = open('index.txt', 'r')

conn = pymongo.Connection()
db = conn.mml

samples = []
for line in index.readlines():
  sample = line.strip().split(':')
  if not sample:
    continue
  name, instrument, game = sample
  samples.append({'name': name, 'instrument': instrument, 'game': game, 'tags': []})

db.samples.insert(samples)

print [s for s in db.samples.find()]


