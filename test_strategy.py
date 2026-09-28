import os
import sys

print("=" * 60)
print("🔍 DIAGNOSTIC MODE")
print("=" * 60)

print("\n📍 Current working directory:")
print("  ", os.getcwd())

print("\n📁 Files in current dir:")
for f in sorted(os.listdir(".")):
    print("  -", f)

print("\n📁 Files in src/:")
for f in sorted(os.listdir("src")):
    print("  -", f)

print("\n📄 Content of src/config.py (first 800 chars):")
with open("src/config.py", "r", encoding="utf-8") as fh:
    content = fh.read()
    print(content[:800])
    print("  ...")
    print(f"\n📏 Total length: {len(content)} chars")

print("\n🔎 Searching for TIMEFRAMES in src/config.py:")
with open("src/config.py", "r", encoding="utf-8") as fh:
    for i, line in enumerate(fh, 1):
        if "TIMEFRAMES" in line:
            print(f"  Line {i}: {line.rstrip()}")

print("\n🐍 Trying to import src.config:")
try:
    import importlib
    import src.config as cfg
    importlib.reload(cfg)
    print("  ✅ Import successful")
    print("  File:", cfg.__file__)
    print("  Has TIMEFRAMES:", hasattr(cfg, "TIMEFRAMES"))
    if hasattr(cfg, "TIMEFRAMES"):
        print("  Value:", cfg.TIMEFRAMES)
    print("  All public attrs:", [x for x in dir(cfg) if not x.startswith("_")])
except Exception as e:
    print(f"  ❌ Import failed: {e}")

print("\n" + "=" * 60)