from sup.parser import Parser
from sup.vm import run as vm_run

path = r"D:\sup2\sup-lang\examples\try1.sup"
with open(path, encoding="utf-8") as f:
    src = f.read()
prog = Parser().parse(src)
out = vm_run(prog)
if out:
    print(out, end="")
