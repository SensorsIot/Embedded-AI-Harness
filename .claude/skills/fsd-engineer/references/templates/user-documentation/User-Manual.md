# {{PROJECT}} — User Manual

How to install and run {{PROJECT}}. Human procedures, present-state. Step-by-step
operational detail lives here and nowhere else — the FSD says what the system
does, this says how you make it do it.

**Status: <nothing is deployable yet / partial / complete>.**

Keep that line honest and current. This manual exists from the first commit even
when there is nothing to operate yet, because an OPERATE plane that was never
created is invisible: nobody notices a directory that does not exist, and the
first person to install the system discovers there are no instructions at the
moment they need them. A stub saying "nothing is deployable yet" is a promise with
a due date; an absent one is an oversight nobody can see.

**One manual, chapters not files.** Everything operational belongs here as a
numbered chapter — installation, configuration, each routine task, diagnostics,
recovery. Do not split operations across several documents in this directory: a
reader looking for "how do I do X" must have exactly one place to start, and a
second operations file is where the first one goes stale. The directory exists to
name the plane, not to be filled.

Delete this paragraph and the status line once the chapters below are real.

## Contents

<Generate from the chapters. A manual long enough to need chapters is long enough
to need a table of contents.>

## 1. What you need

<Hardware, accounts, tools, and access needed before starting. Where credentials
live — the location, never the secret itself.>

## 2. Installation and first run

<From bare metal or an empty environment to a working system. One recommended
path, not three variants. Anything that will brick or corrupt if skipped is
flagged here explicitly, along with any decision that cannot be changed later.>

## 3. Configuration

<What is configurable, where it lives, the defaults, and how to read the current
settings. Say when configuration is optional — if the system auto-detects, say so,
so nobody edits a file they did not need to.>

## 4..n Routine operations

<One chapter per recurring task, named for the task rather than the subsystem: a
reader searches for what they want to do. Give the exact command or API call, with
real values — a reader should be able to copy a line and run it.>

## n+1. Troubleshooting

<Symptom → cause → fix, as a table. Every failure that has cost someone an hour
earns a row. Include the diagnostic commands to run on the system itself.>

## n+2. Recovery

<What to do when it breaks: restart, roll back, re-provision, restore. Separate
what happens automatically from what needs a person, so nobody intervenes in a
recovery already under way.>

---

**Contract:** `{{FSD_PATH}}` · **Build rules:** `{{HARNESS_PATH}}`
