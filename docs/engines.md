# Regex engines: Android vs Linux

The snippets in `topics/` target **Android first**. This page records where other
engines behave differently, and says what was tested on a machine and what comes
from documentation.

## Android: ICU

Android's `java.util.regex.Pattern`, and `kotlin.text.Regex` on top of it, is
backed by **ICU4C**, not the OpenJDK engine. Android's `Pattern` reference says so
in its documentation. Any Android app written in Java or Kotlin that offers
"regex" rules almost certainly uses this engine.

`scripts/validate.py` therefore calls ICU directly, through `ctypes` on
`libicui18n.so.N`, and counts a snippet as Android-compatible only if it passes
under ICU.

> **Not verified on a phone.** No snippet has been run inside a real app
> through `adb`. ICU on desktop (ICU 78, tested 2026-10-14) stands in for the
> phone, and Android ships its own ICU version, which differs by OS release.
> Basic syntax hasn't changed between ICU releases for years, but treat edge
> cases as unconfirmed.

### App-level unknowns: Whisperian

Whisperian is closed source and doesn't document its rule engine on
<https://whisperian.app> (checked 2026-10-14). The following are **inferred, not
confirmed**:

- that its regex rules compile with `kotlin.text.Regex` / `java.util.regex`;
- that replacements use `$1` for capture groups (the Java/ICU syntax);
- whether its rule editor lets you type a real line break into a replacement.

If a snippet misbehaves in the app, these are the first things to suspect.

## Differences that matter for these snippets

| Feature | Android (ICU) | Desktop Java (JDK) | Python `re` | Perl | GNU `sed -E` |
|---|---|---|---|---|---|
| `\w` matches non-ASCII letters (Hebrew, accented, …) | **yes** | **no** (needs `(?U)`) | yes | yes (Unicode strings) | yes, in a UTF-8 locale |
| `(?i)` inline flag | yes | yes | yes (must be at the very start) | yes | **no**: use the `I` flag (`s/…/…/gI`) |
| Lookahead `(?=…)` / `(?!…)` | yes | yes | yes | yes | **no** |
| `\p{Lu}` Unicode classes | yes | yes | **no** (use the `regex` package) | yes | no |
| Backreference in pattern | `\1` | `\1` | `\1` | `\1` | `\1` |
| Group in replacement | `$1` | `$1` | `\1` or `\g<1>` | `$1` | `\1` |
| Case conversion in replacement (`\u`, `\U`) | **no** | **no** | no | yes | yes (GNU extension) |
| Literal `\n` typed in replacement | gives `n` (backslash escapes next char) | gives `n` | newline | newline | newline |

**Tested on 2026-10-14** (Ubuntu, ICU 78, OpenJDK 25.0.4.1, Python 3, Perl 5,
GNU sed 4.9):

- the `\w` row for ICU, JDK, Python, Perl and sed;
- sed rejecting `(?i)` and lookahead;
- Python rejecting `\p{Lu}`.

The replacement-syntax rows are what `validate.py` translates between, so every
passing test exercises them. The case-conversion and literal-`\n` rows come from
the engines' documentation.

`grep -P` (PCRE2) isn't covered. On the machine that ran these tests, `grep`
resolves to ugrep, so the result wouldn't describe GNU grep.

## The practical upshot

- **Moving a snippet from Android to desktop Java/Kotlin:** add `(?U)` to the
  front of any pattern that uses `\w`, `\b` or `[^\W…]`, or it will ignore
  non-English words.
- **Moving a snippet to `sed`:** strip `(?i)` and add the `I` flag. Change `$1`
  to `\1` in the replacement. Any snippet with a lookahead has no `sed`
  equivalent; use `perl -pe` instead, which takes the pattern unchanged.
- **Capitalising after a removal** can't be done with a regex on Android. It
  needs code or an LLM pass.
