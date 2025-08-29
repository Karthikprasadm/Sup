# Transpiled from sup

last_result = None


def fact(n):
    global last_result
    if n <= 1:
        return 1
    return n * fact(n - 1)


def __main__():
    print(fact(5))


if __name__ == "__main__":
    __main__()
else:
    # Initialize module state on import
    __main__()
