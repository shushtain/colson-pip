import colson

with open("test_in.colson", encoding="utf-8") as f:
    raw_data = f.read()

data = colson.loads(raw_data)
print(data)

with open("test_out.colson", "w", encoding="utf-8") as f:
    f.write(colson.dumps(data))
