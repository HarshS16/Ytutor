p = 'generators/pdf_export.py'
s = open(p, encoding='utf-8').read()

start = s.index('    # Repair common mojibake sequences')
end = s.index('    text = re.sub(r"[\\U00010000-\\U0010ffff]"', start)

# Build the replacement pairs using explicit codepoints so nothing
# depends on literal mojibake characters in this script.
pairs = [
    ("\\u00e2\\u20ac\\u009d", '"'), ("\\u00e2\\u20ac\\u0153", '"'),
    ("\\u00e2\\u20ac\\u02dc", "'"), ("\\u00e2\\u20ac\\u2122", "'"),
    ("\\u00e2\\u20ac\\u201c", '"'), ("\\u00e2\\u20ac\\u201d", '"'),
    ("\\u00e2\\u20ac\\u201e", '"'), ("\\u00e2\\u20ac\\u201a", "'"),
    ("\\u00e2\\u20ac\\u2013", "-"), ("\\u00e2\\u20ac\\u2014", "-"),
    ("\\u00e2\\u20ac\\u2026", "..."), ("\\u00e2\\u20ac\\u2022", "-"),
    ("\\u00c3\\u00a9", "e"), ("\\u00c3\\u00a8", "e"), ("\\u00c3\\u00a1", "a"),
    ("\\u00c3\\u00b1", "+/-"),
]
dict_src = ", ".join(f'"{k}": "{v}"' for k, v in pairs)

new = (
    "    # Repair common mojibake sequences (UTF-8 text decoded as cp1252)\n"
    f"    _MOJIBAKE = {{{dict_src}}}\n"
    "    for bad, good in _MOJIBAKE.items():\n"
    "        if bad in text:\n"
    "            text = text.replace(bad, good)\n"
)

s = s[:start] + new + s[end:]
open(p, 'w', encoding='utf-8').write(s)
print("patched")
