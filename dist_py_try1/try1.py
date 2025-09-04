# Transpiled from sup

last_result = None


def __main__():
    global n
    n = 3
    last_result = n
    if n > 2:
        print("n is big")
    else:
        print("n is small")
    for _ in range(int(3)):
        print("loop")


if __name__ == "__main__":
    __main__()
else:
    # Initialize module state on import
    __main__()
