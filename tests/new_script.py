from random import randint
from typing import List

gtz: List[int] = [x for i in range(10) if (x := randint(0, 9)) != 0]

print(f"numbers greater than zero: {gtz}")
print(f"number filtering: {list(filter(lambda x: x % 2 == 0, gtz))}")
