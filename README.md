## Toilet Typist

A tiny, terminal‑based typing trainer with a mischievous sense of humor. Build your speed and accuracy through drills, sprints, a timed boss battle, and a branching Story Mode where great scores unlock choices—and bad ones splatter your character with comedic consequences.

Repo: `https://github.com/mylegitches/toilet-typist`

### Features
- **Word Drills**: Quick rounds built from themed word banks.
- **Sentence Sprints**: Practice full sentences for flow and rhythm.
- **Boss Battle (60s)**: Type as much as you can in 60 seconds; accuracy matters.
- **Story Mode**: Progressive lessons that start on the home row and add a few keys at a time. Each chapter is timed and scored with accuracy tracking. Good results branch the story with choose‑your‑own‑adventure style choices; poor results lead to funny, “messy” setbacks and retries. Progress is saved.
- **Scores & Progress**: Attempts are persisted to `typing_teacher_scores.json` and Story Mode progress to `story_progress.json`.

### Requirements
- Python 3.11+ recommended
- Works on Windows, macOS, and Linux terminals. No extra dependencies.

### Quickstart
1) Clone the repo:

```bash
git clone https://github.com/mylegitches/toilet-typist.git
cd toilet-typist
```

2) (Optional) Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3) Run the app:

```bash
python toilet_typist.py
```

### Usage
From the main menu:
- 1) **Word Drills**
- 2) **Sentence Sprints**
- 3) **Boss Battle (60s)**
- 4) **Story Mode** (continue/reset, then play chapters)
- 5) **Toggle Potty Humor** (on/off)
- 6) **View High Scores**
- 7) **Quit**

During prompts, type freely (backspace allowed) and press Enter to submit. Stats shown per attempt include time, WPM, accuracy, and a witty comment.

### Story Mode Details
- Lessons begin with home row (`asdfjkl;`) and gradually add keys across chapters.
- Each chapter consists of multiple short prompts generated from its allowed keys.
- Chapter result = average Net WPM and Accuracy across prompts.
- Pass criteria (defaults): **≥ 90% accuracy** and **≥ 20 Net WPM**.
  - Pass: You’ll see success narrative and get to choose a path forward.
  - Fail: You’ll get a humorous “gross” setback; you may retry or be routed to a detour node.
- Progress is saved to `story_progress.json` so you can quit and resume later.

### Data Files
- `typing_teacher_scores.json`: Appends attempt summaries (mode, timestamp, Net WPM, Accuracy).
- `story_progress.json`: Stores current node and story history.

If you delete these files, scores/progress will reset.

### Customization
- Tune pass thresholds by editing `GOOD_ACC_THRESHOLD` and `GOOD_NET_WPM_THRESHOLD` in `toilet_typist.py`.
- Add/modify story chapters by extending `STORY_NODES` in `toilet_typist.py`.

### Troubleshooting
- If your terminal shows odd characters, set a UTF‑8 locale.
- On Windows PowerShell, execution policy may restrict venv activation; you can run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before activating.
- If Git complains about a “dubious ownership” repo, mark the folder as safe: `git config --global --add safe.directory "<path-to-repo>"`.

### Roadmap
- Optional per‑chapter time limits and streak bonuses.
- Configurable lesson plans and thresholds from a config file.
- Optional sound effects and color output where supported.

### License
No license specified yet. Add a `LICENSE` file to choose one (e.g., MIT).


