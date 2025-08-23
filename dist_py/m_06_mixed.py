# Transpiled from sup
from sys import stdout
last_result = None


def __main__():
    x = (2 + 3)
    last_result = x
    print(last_result)
    y = (x - 3)
    last_result = y
    if (y > 1):
        for _ in range(int(2)):
            print((y * 10))
    print((y / 2))

if __name__ == '__main__':
    __main__()
