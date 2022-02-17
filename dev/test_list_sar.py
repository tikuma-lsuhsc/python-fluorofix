from fractions import Fraction
import re

s = input("Enter decimal aspect ratio (e.g., 5.02/4.44, 1.1306306306306304): ")
try:
    x = eval(s)
except:
    raise ValueError(f"{s} is not a valid Python expression")

s = input("Enter frame size (e.g., 1920x1080): ")
try:
    m = re.match(r'(\d+)x(\d+)',s)
    w = int(m[1])
    h = int(m[2])
except:
    raise ValueError(f"{s} is not a valid frame size expression")

s = input("Enter maximum denominator [100]: ")
if s:
    try:
        den = int(eval(s))
    except:
        raise ValueError(f"{s} is not a valid Python expression")
else:
    den = 100

print("Following are possible candidates:")

f = Fraction(x)
den = den + 1
while den > 1:
    g = f.limit_denominator(den - 1)
    den = g.denominator
    print(f"{g.numerator}/{g.denominator} : size = {w}x{float(h/g):0.2f} or {float(w*g):0.2f}x{h}")
