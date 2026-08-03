# {{PROJECT}} — Handbook (OPERATE)

How to run {{PROJECT}}. Human procedures, present-state. Step-by-step operational
detail lives here and nowhere else — the FSD says what the system does, this says
how you make it do it.

## Access and prerequisites

<How to reach the system; what hardware, accounts, or tools are needed first;
where credentials live — the location, never the secret itself.>

## Installation and first run

<From bare metal or empty environment to a working system. One recommended path,
not three variants. Anything that will brick or corrupt if skipped goes here with
an explicit warning.>

## Configuration

<What is configurable, where the file lives, what the defaults are, and how to
discover current settings. State when configuration is optional — if the system
auto-detects, say so, so nobody edits a file they did not need to.>

## Routine operations

<One section per recurring task: what to do, and the exact command or API call
that does it. Real values, not placeholders — a reader should be able to copy a
line and run it.>

## Diagnostics and troubleshooting

<Symptom → cause → fix, as a table. Every failure that has cost someone an hour
earns a row. Include the diagnostic commands to run on the system itself.>

## Recovery

<What to do when it breaks: restart, roll back, re-provision, restore. Who to
notify, if anyone.>

---

**Contract:** `{{FSD_PATH}}` · **Build rules:** `{{HARNESS_PATH}}`
