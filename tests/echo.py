from sys import argv, stderr, stdout
from time import sleep

where = argv[2] if len(argv) > 2 else "out"
stop = int(argv[3]) if len(argv) > 3 else 9
file = stderr if where.startswith("e") else stdout

for i in range(stop):
    print(argv[1], i, flush=True, file=file)
    sleep(2)
