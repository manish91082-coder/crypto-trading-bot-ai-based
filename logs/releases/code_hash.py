# Read-only: print "path,bytes,sha256" for every code/config file under src/ and deploy/ (no __pycache__). Writes nothing.
import hashlib, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
os.chdir(root)
for top in ("src", "deploy"):
    for d, dirs, fs in os.walk(top):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        for f in sorted(fs):
            p = os.path.join(d, f).replace("\\", "/")
            b = open(p, "rb").read()
            print(f"{p},{len(b)},{hashlib.sha256(b).hexdigest()}")
