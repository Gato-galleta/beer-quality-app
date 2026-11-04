import csv
p='quality/ml/data/beer_quality.csv'
with open(p, encoding='utf-8', errors='ignore') as f:
    reader=csv.reader(f)
    header=next(reader)
    print(len(header))
    print(header[:200])
