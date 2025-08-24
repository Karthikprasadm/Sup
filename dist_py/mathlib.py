# Transpiled from sup
from sys import stdout
last_result = None

def square(x):
    global last_result
    return (x * x)


def __main__():
    global pi
    pi = 3.1415
    last_result = pi

if __name__ == '__main__':
    __main__()
else:
    # Initialize module state on import
    __main__()
