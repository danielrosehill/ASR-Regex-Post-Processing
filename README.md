# ASR Regex Post-Processing

A notebook of regular expressions for cleaning up speech-to-text output, plus
ideas for what regex can do in that role.

Android dictation apps are starting to offer a post-processing step after
transcription. [Whisperian](https://whisperian.app) is a good example: it
supports both small LLM post-processors and plain regex replacement rules.
Regex does more there than you'd expect. It can be a cheap, deterministic
pre-pass before an LLM step, or the only post-processing you run.

## Ground rule

**Every snippet must be a valid regular expression that works on Android.**

Android's regex engine is ICU, which differs from desktop Java's in a few ways
that matter. Where Linux tools (desktop Java/Kotlin, Python, Perl, `sed`) behave
differently, the snippet says so. [`docs/engines.md`](docs/engines.md) has the
full comparison.

## Topics

Each topic is one markdown file. Each snippet in it has the pattern, the
replacement, worked examples, and a risk rating.

| Topic | What it covers |
|---|---|
| [Disfluencies](topics/disfluencies.md) | Fillers (*um, uh, erm, hmm*), stutters, false starts, verbal tics, throat-clearing openers, and the cleanup that follows |

### Ideas not written up yet

- **Spoken punctuation and layout:** *comma*, *full stop*, *question mark*,
  *new line*, *new paragraph*.
- **Voice commands:** *scratch that* deletes back to the previous sentence
  boundary.
- **Numbers and entities:** *3 30 pm* → *3:30 pm*, *20 percent* → *20%*,
  *jane at example dot com* → an email address.
- **Whisper hallucinations:** a phrase looped three or more times, and
  *thanks for watching* tacked onto silence.
- **Normalisation:** curly quotes, a lowercase standalone *i*, and missing
  spaces after punctuation.

## Snippet format

~~~~text
## N. Name

```regex
<pattern exactly as you'd paste it>
```

```replace
<replacement — empty block means "delete"; $1 = group 1>
```

```tests
<input> => <expected output>
```
~~~~

The `tests` lines are machine-checked. `scripts/validate.py` runs every
snippet through four engines:

- Android's ICU, called directly;
- desktop JDK;
- Python `re`;
- Perl.

It then writes the results to
[`docs/compatibility.md`](docs/compatibility.md). It exits non-zero if any
snippet fails on Android.

```bash
python3 scripts/validate.py
```

Requirements: the ICU runtime library (`libicui18n.so.N`, present on any
desktop Linux), a JDK on `PATH`, and `perl`. No Python packages are needed.

A failure in another engine column is fine, as long as the snippet's notes
explain it. One example: the stutter rule collapses a repeated Hebrew word on
Android but not under desktop Java.

## License

MIT
