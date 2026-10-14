# Disfluencies

Hesitation sounds, stutters and false starts that the ASR model transcribed
faithfully but that you don't want in the text you're writing.

Each snippet below is a find pattern plus a replacement. Paste the pattern
exactly as written. Nothing needs escaping for a Java or Kotlin string, because
an app's regex field takes the raw pattern. An empty `replace` block means
"replace with nothing".

Run them in the order listed, then run the [cleanup](#cleanup-after-removal)
rules, because every deletion leaves stray spaces and commas behind.

---

## 1. Catch-all hesitation sounds

One expression for the common English fillers: *um, umm, uh, uhh, uhm, erm,
hmm, hmmm, ah, ahh*. It also removes any comma or period the model attached to
the filler, plus the space after it.

```regex
(?i)\b(?:u+[hm]+|e+r+m+|h+m+|a+h+)\b[,.]?\s*
```

```replace
```

```tests
So um, I think uh we should go => So I think we should go
Ummm the umbrella is ahead => the umbrella is ahead
Uhm, hmm. Okay => Okay
```

- **How it works:** `u+[hm]+` covers um, uh, uhm and their stretched forms
  (`ummm`). `e+r+m+` covers erm, `h+m+` covers hmm, and `a+h+` covers ah. The
  `\b` on each side keeps real words that start with these letters intact, such
  as *umbrella*, *ahead* and *hmmingbird* typos.
- **Risk: low.** Bare *er* and *mm* are left out on purpose; see variants 2
  and 3.

## 2. Add bare "er"

```regex
(?i)\b(?:u+[hm]+|e+r+m*|h+m+|a+h+)\b[,.]?\s*
```

```replace
```

```tests
I er think so => I think so
Go to the ER now => Go to the now
```

- **Risk: medium.** Because the pattern ignores case, it also deletes *ER*
  (emergency room), as the second test shows. Use this variant only if you never
  dictate that abbreviation.

## 3. Add "mm" / "mhm" / "mm-hmm"

```regex
(?i)\b(?:m+-?h*m+|u+h-huh)\b[,.]?\s*
```

```replace
```

```tests
Mm-hmm, that works => that works
Mhm I agree => I agree
uh-huh sure => sure
It is 5 mm wide => It is 5 wide
```

- **Risk: medium.** It also deletes the unit *mm* (millimetres), as the last
  test shows. Run it as its own rule so you can switch it off.
- **Order:** run it before snippet 1. Otherwise snippet 1 removes the *uh* of
  *uh-huh* first and leaves *-huh* behind.

## 4. Stutters: an immediately repeated word

Turns *I I think the the plan* into *I think the plan*.

```regex
(?i)\b(\w+)(?:[\s,]+\1\b)+
```

```replace
$1
```

```tests
I I think the the plan is fine => I think the plan is fine
The the theory => The theory
we, we, we should => we should
שלום שלום עולם => שלום עולם
```

- **Risk: medium.** It also collapses doubles that are correct English, such as
  *had had* and *that that*.
- **Engine difference:** on Android, `\w` follows Unicode (ICU), so the Hebrew
  test passes. On desktop Java (JDK), `\w` is ASCII-only unless the pattern
  starts with `(?U)`, so the Hebrew line is left unchanged there.

## 5. False starts: a cut-off word fragment

Some models mark an abandoned word with a trailing hyphen: *I wa- I want*.

```regex
\b\w+-\s+(?=\w)
```

```replace
```

```tests
I wa- I want to go => I I want to go
pre- and post-war => and post-war
```

- **Risk: medium.** It removes only the fragment, so run snippet 4 afterwards
  to collapse the *I I* that's left. It also breaks suspended hyphens such as
  *pre- and post-war*.

## 6. Verbal tics: "you know", "I mean", "like"

Opt-in. These are real words, and regex can't tell a tic from meaning. Only
the form followed by a comma is targeted, because that's how ASR punctuates a
tic. Any punctuation before the tic is kept, so you may get *It was, fine*.
That's safer than also deleting a comma that belonged to the sentence.

```regex
(?i)\b(?:you know|I mean|like),\s+
```

```replace
```

```tests
It was, you know, fine => It was, fine
Fine, I mean, it works => Fine, it works
I like, really like it => I really like it
I like it => I like it
```

- **Risk: high.** It also eats a literal *I mean,* ("I mean, the blue one"),
  and every *like,* that's followed by a comma.

## 7. Throat-clearing openers

Opt-in. Drops *So,* / *Okay so* / *Well,* / *Right,* at the very start of a
dictation.

```regex
(?i)^\s*(?:okay|ok|so|well|right|alright)\b[,.]?(?:\s+so\b,?)?\s*
```

```replace
```

```tests
Okay so, the meeting moved => the meeting moved
So the meeting moved => the meeting moved
Sounds good => Sounds good
```

- **Risk: medium.** It only fires at the start of the text, which is usually
  what you want from dictation.

---

## Cleanup after removal

These aren't disfluency rules. They tidy up the spaces and punctuation that the
rules above leave behind, and should run last, in this order.

### Comma left before sentence-ending punctuation

```regex
,\s*([.!?])
```

```replace
$1
```

```tests
that is all,. => that is all.
```

### Space before punctuation

```regex
[ \t]+([,.!?;:])
```

```replace
$1
```

```tests
Hello , world ! => Hello, world!
```

### Runs of spaces

```regex
[ \t]{2,}
```

```replace
 
```

```tests
too    many  spaces => too many spaces
```

### Trim

```regex
^\s+|\s+$
```

```replace
```

```tests
  hello   => hello
```

## What regex can't do here

- **Re-capitalise after a removal.** *Um, so we…* becomes *so we…*. Java and
  ICU replacement strings have no case-conversion escape (Perl's `\u` / `\U`
  don't exist on Android), so the new first letter stays lowercase. That fix
  needs code or an LLM post-processing pass.
- **Tell a tic from meaning.** *Like* and *I mean* are both, depending on
  context. That's the job an LLM post-processing step is good at, which is why
  snippets 6 and 7 are opt-in.
