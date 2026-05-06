# CodeSense

A personal coding tutor that lives inside Claude Code. It teaches web development fundamentals from zero, using plain-English analogies, spaced repetition, and a progress tracker that adapts to what you already know.

It's especially geared toward people who already build in Webflow and want to understand what's actually happening under the hood (HTML, CSS, JavaScript, dev tools, file paths, the works).

## What you get

- A **slash command** `/codesense` inside Claude Code with subcommands: `start`, `learn`, `quiz`, `scan`, `explain [term]`, `progress`, `review`
- A **SQLite database** that tracks every concept you learn, your confidence on each one, and when each one is due for review
- A built-in **skill tree** with 26+ web dev concepts already loaded, plus the ability to add new ones on the fly when you hit something unfamiliar

You ask Claude something like `/codesense start` and it onboards you, assesses where you are, and starts teaching.

## File layout

This bundle mirrors where each file needs to live on your machine:

```
skills/codesense/SKILL.md      → ~/.claude/skills/codesense/SKILL.md
codesense/codesense_db.py      → ~/codesense/codesense_db.py
```

That's it. Two files. One is the skill definition Claude Code reads, the other is the Python helper that manages the SQLite database.

## Setup

1. **Drop the skill file** in your Claude Code skills folder:
   ```bash
   mkdir -p ~/.claude/skills/codesense
   cp skills/codesense/SKILL.md ~/.claude/skills/codesense/
   ```

2. **Drop the database helper** in your home directory:
   ```bash
   mkdir -p ~/codesense
   cp codesense/codesense_db.py ~/codesense/
   ```

3. **Initialize the database** (one-time, creates the SQLite file and seeds 26 concepts):
   ```bash
   python3 ~/codesense/codesense_db.py init
   ```

4. **Open Claude Code** and run:
   ```
   /codesense start
   ```

   It'll walk you through onboarding and start teaching.

## Path coupling

The skill assumes the Python helper lives at `~/codesense/codesense_db.py`. If you put it somewhere else, search SKILL.md for `~/codesense/codesense_db.py` and replace with your actual path before installing.

## Optional: set your name

The default user name in the database is "User". You can change it any time:

```bash
python3 ~/codesense/codesense_db.py profile set name "YourName"
```

## Troubleshooting

**`/codesense` doesn't show up in Claude Code.** Make sure the file is at `~/.claude/skills/codesense/SKILL.md` (not just `~/.claude/skills/codesense.md`). Restart Claude Code after dropping it in.

**Python errors when running `init`.** This needs Python 3 with the `sqlite3` module (which is built in to standard Python 3 on macOS, no install required). Try `python3 --version` to confirm Python 3 is available.

**Where's the database file?** It lives at `~/codesense/codesense.db` after you run `init`. That's where all your progress is stored. Back it up if you switch machines.

**I want to reset progress.** Delete `~/codesense/codesense.db` and run `init` again. You'll lose all progress.

## What's in the skill tree out of the box

Internet basics, HTML (div, h1-h6, p, a, etc.), CSS (selectors, classes, flexbox, grid, media queries), JavaScript (variables, functions), dev tools, file paths. The skill can also add new concepts whenever you encounter something it doesn't know.

## Notes

- **Webflow-aware.** A lot of the analogies bridge from Webflow's visual interface to the actual code underneath. If you don't use Webflow, the analogies still work but some references will feel extra.
- **No AI vibes.** The tutor's job is to teach, not to perform. It's encouraging when you make progress and direct when you don't. No condescension, no "great question!" filler.
- **Spaced repetition.** It uses the SM-2 algorithm (the same one Anki uses) to figure out when each concept is due for review. The more you get something right, the longer it waits before testing you on it again.
