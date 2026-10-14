#!/usr/bin/env python3
"""Validate every snippet in topics/*.md against four regex engines.

A snippet is a ```regex block followed by a ```replace block and an optional
```tests block (one `input => expected` per line). Engines:

  icu     ICU 4C via ctypes — the engine behind java.util.regex / kotlin.text.Regex
          on Android. This is the one that decides "works on Android".
  jdk     desktop java.util.regex (scripts/JdkRunner.java) — Kotlin/Java on Linux.
  python  Python `re`.
  perl    Perl 5 with Unicode strings — stands in for PCRE (grep -P, most editors).

Writes docs/compatibility.md and exits non-zero if any ICU (Android) case fails.
Needs: libicui18n.so.<N> on the system, a JDK (java on PATH), perl.
"""
import base64, ctypes, ctypes.util, glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENCE = re.compile(r"^```(regex|replace|tests)\n(.*?)^```\s*$", re.M | re.S)
HEAD = re.compile(r"^#{2,3} (.+)$", re.M)


def parse(path):
    text = open(path, encoding="utf-8").read()
    heads = [(m.start(), m.group(1)) for m in HEAD.finditer(text)]
    snippets, cur = [], None
    for m in FENCE.finditer(text):
        kind, body = m.group(1), m.group(2)
        body = body[:-1] if body.endswith("\n") else body
        if kind == "regex":
            title = [h for pos, h in heads if pos < m.start()][-1]
            cur = {"file": os.path.relpath(path, ROOT), "title": title, "pattern": body, "replace": "", "tests": []}
            snippets.append(cur)
        elif kind == "replace":
            cur["replace"] = body
        else:
            for line in body.split("\n"):
                if " => " in line:
                    i, o = line.split(" => ", 1)
                    cur["tests"].append((i, o))
    return snippets


# --- ICU via ctypes -------------------------------------------------------------
def load_icu():
    for n in range(90, 50, -1):
        try:
            return ctypes.CDLL(f"libicui18n.so.{n}"), f"_{n}", n
        except OSError:
            continue
    raise SystemExit("ICU runtime (libicui18n.so.N) not found")


ICU, SUF, ICU_VER = load_icu()


class UParseError(ctypes.Structure):
    _fields_ = [("line", ctypes.c_int32), ("offset", ctypes.c_int32),
                ("pre", ctypes.c_uint16 * 16), ("post", ctypes.c_uint16 * 16)]


def _u16(s):
    b = s.encode("utf-16-le")
    return (ctypes.c_uint16 * (len(b) // 2 + 1)).from_buffer_copy(b + b"\0\0"), len(b) // 2


def icu(pat, rep, text):
    fn = lambda n: getattr(ICU, n + SUF)
    err, pe = ctypes.c_int(0), UParseError()
    p, pl = _u16(pat)
    op = fn("uregex_open"); op.restype = ctypes.c_void_p
    rx = ctypes.c_void_p(op(p, pl, 0, ctypes.byref(pe), ctypes.byref(err)))
    if err.value > 0:
        raise ValueError(f"ICU compile error {err.value} at offset {pe.offset}")
    t, tl = _u16(text)
    fn("uregex_setText")(rx, t, tl, ctypes.byref(err))
    r, rl = _u16(rep)
    cap = tl * 8 + 256
    out = (ctypes.c_uint16 * cap)()
    n = fn("uregex_replaceAll")(rx, r, rl, out, cap, ctypes.byref(err))
    fn("uregex_close")(rx)
    if err.value > 0:
        raise ValueError(f"ICU replace error {err.value}")
    return bytes(out)[: n * 2].decode("utf-16-le")


# --- Python re ------------------------------------------------------------------
def python(pat, rep, text):
    # Java/ICU replacement syntax -> Python: $n -> \g<n>, \x -> literal x
    out, i = [], 0
    while i < len(rep):
        c = rep[i]
        if c == "\\" and i + 1 < len(rep):
            out.append(rep[i + 1].replace("\\", "\\\\")); i += 2
        elif c == "$" and i + 1 < len(rep) and rep[i + 1].isdigit():
            j = i + 1
            while j < len(rep) and rep[j].isdigit():
                j += 1
            out.append(f"\\g<{rep[i+1:j]}>"); i = j
        else:
            out.append("\\\\" if c == "\\" else c); i += 1
    return re.sub(pat, "".join(out), text)


# --- batch engines (JDK, Perl) ----------------------------------------------------
PERL = r'''
use strict; use utf8; use MIME::Base64; use Encode;
binmode STDOUT;
while (my $l = <STDIN>) { chomp $l; my ($p,$r,$t) = map { decode("UTF-8", decode_base64($_)) } split /\t/, $l, -1;
  my $res = eval { my $rx = qr/$p/; (my $s = $t) =~ s/$rx/my @c=(undef, @{^CAPTURE}); (my $x=$r) =~ s{\\(.)|\$(\d+)}{defined $1 ? $1 : ($c[$2] \/\/ "")}ge; $x/ge; $s };
  if ($@) { print "ERR ", encode_base64(encode("UTF-8",$@),""), "\n" } else { print "OK ", encode_base64(encode("UTF-8",$res),""), "\n" } }
'''


def batch(cmd, cases):
    b64 = lambda s: base64.b64encode(s.encode()).decode()
    stdin = "".join(f"{b64(p)}\t{b64(r)}\t{b64(t)}\n" for p, r, t in cases)
    proc = subprocess.run(cmd, input=stdin.encode(), capture_output=True, cwd=ROOT)
    lines = proc.stdout.decode().splitlines()
    if len(lines) != len(cases):
        raise SystemExit(f"{cmd[0]} runner failed:\n{proc.stderr.decode()}")
    out = []
    for l in lines:
        status, payload = l.split(" ", 1)
        val = base64.b64decode(payload).decode()
        out.append(val if status == "OK" else ValueError(val.strip()))
    return out


def main():
    snippets = [s for f in sorted(glob.glob(os.path.join(ROOT, "topics", "*.md"))) for s in parse(f)]
    cases = [(s["pattern"], s["replace"], i) for s in snippets for i, _ in s["tests"]]
    results = {
        "jdk": batch(["java", "scripts/JdkRunner.java"], cases),
        "perl": batch(["perl", "-e", PERL], cases),
    }
    for name, fn in (("icu", icu), ("python", python)):
        res = []
        for p, r, t in cases:
            try:
                res.append(fn(p, r, t))
            except Exception as e:  # compile errors are a result, not a crash
                res.append(ValueError(str(e)))
        results[name] = res

    engines = ["icu", "jdk", "python", "perl"]
    k, android_fail, rows, failures = 0, 0, [], []
    for s in snippets:
        verdict = {}
        for e in engines:
            ok = 0
            for idx, (_, exp) in enumerate(s["tests"]):
                got = results[e][k + idx]
                if not isinstance(got, Exception) and got == exp:
                    ok += 1
                else:
                    failures.append((e, s["file"], s["title"], s["tests"][idx][0], exp, got))
            verdict[e] = f"{ok}/{len(s['tests'])}"
        if verdict["icu"] != f"{len(s['tests'])}/{len(s['tests'])}":
            android_fail += 1
        k += len(s["tests"])
        rows.append((s, verdict))

    md = ["# Engine compatibility", "",
          "Generated by `scripts/validate.py` — do not edit by hand. Each cell is tests passed / tests defined.", "",
          f"| File | Snippet | Android (ICU {ICU_VER}) | JDK | Python `re` | Perl |", "|---|---|---|---|---|---|"]
    for s, v in rows:
        cells = [v[e] if v[e].split("/")[0] == v[e].split("/")[1] else f"**{v[e]}**" for e in engines]
        md.append(f"| `{s['file']}` | {s['title']} | " + " | ".join(cells) + " |")
    md += ["", "## Failing cases", ""]
    if not failures:
        md.append("None.")
    for e, f, title, i, exp, got in failures:
        md.append(f"- **{e}** · {title} · input `{json.dumps(i, ensure_ascii=False)}` → expected `{json.dumps(exp, ensure_ascii=False)}`, got `{json.dumps(got if isinstance(got, str) else 'ERROR: ' + str(got), ensure_ascii=False)}`")
    open(os.path.join(ROOT, "docs", "compatibility.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    print("\n".join(md[4:]))
    sys.exit(1 if android_fail else 0)


if __name__ == "__main__":
    main()
