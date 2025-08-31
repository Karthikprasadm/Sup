# Transpiled from sup
from sys import stdout
last_result = None


def __main__():
    import mathlib
    print(mathlib.pi)
    print(mathlib.square(7))
    from mathlib import square
    print(square(3))

if __name__ == '__main__':
    __main__()
else:
    # Initialize module state on import
    __main__()

# sourceMappingURL=m_12_imports.py.map
