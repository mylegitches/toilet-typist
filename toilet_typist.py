import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

SCORES_FILE = "typing_teacher_scores.json"
STORY_PROGRESS_FILE = "story_progress.json"

POTTY_WORDS = [
    "toilet",
    "fart",
    "burp",
    "poop",
    "flush",
    "plunger",
    "stinky",
    "diaper",
    "noodle",
    "banana",
    "giggle",
    "meme",
    "keyboard",
    "wifi",
    "yeet",
    "cringe",
    "sauce",
    "drip",
    "ratio",
    "skibidi",
    "toilet-core",
]

SILLY_SENTENCES = [
    "Skibidi toilet took my Wi‑Fi and left a fart cloud.",
    "My keyboard screams YEET every time I miss a key.",
    "Burps are just mouth farts, argue with the science.",
    "Flush fear, type fierce, win snacks.",
    "I type so fast the letters need seatbelts.",
    "Coach says: posture up or the chair will file a complaint.",
    "Plungers are just wrenches for toilets.",
    "Hydrate or dydrate; also moisturize your keyboard.",
    "This sentence contains zero cringe and three giggles.",
    "When in doubt, backspace like a ninja, not a woodpecker.",
]

WITTY_PRAISE = [
    "Cleaner than a triple flush!",
    "That was minty fresh.",
    "Keyboard go brrr.",
    "NASA called; they want their WPM back.",
    "Your accuracy slapped, respectfully.",
]

WITTY_ROASTS = [
    "Typos spilled everywhere — get the plunger.",
    "That accuracy stinks. Air out those fingers.",
    "More fumbles than my phone at 3am.",
    "Keyboard crying in lowercase.",
    "Bro typed like the Wi‑Fi was buffering his fingers.",
]


@dataclass
class AttemptStats:
    expected: str
    typed: str
    seconds: float
    gross_wpm: float
    accuracy_pct: float
    net_wpm: float


@dataclass
class StoryNode:
    id: str
    title: str
    lesson_keys: str  # allowed characters for this lesson (excluding space)
    success_text: str
    failure_text: str
    choices: List[Tuple[
        str, str]]  # (choice_text, next_node_id) shown only on success
    failure_next: Optional[
        str]  # auto-follow when failing; if None, repeat node


def load_scores() -> List[dict]:
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


def save_score(mode: str, net_wpm: float, accuracy_pct: float) -> None:
    scores = load_scores()
    scores.append({
        "timestamp": int(time.time()),
        "mode": mode,
        "net_wpm": round(net_wpm, 2),
        "accuracy_pct": round(accuracy_pct, 1),
    })
    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
    except Exception:
        pass


def compute_stats(expected: str, typed: str, seconds: float) -> AttemptStats:
    if seconds <= 0:
        seconds = 1e-6
    correct_chars = sum(1 for i, c in enumerate(typed)
                        if i < len(expected) and expected[i] == c)
    total_chars = max(len(expected), 1)
    accuracy_pct = (correct_chars / total_chars) * 100.0
    gross_wpm = (len(typed) / 5.0) / (seconds / 60.0)
    net_wpm = gross_wpm * (accuracy_pct / 100.0)
    return AttemptStats(
        expected=expected,
        typed=typed,
        seconds=seconds,
        gross_wpm=gross_wpm,
        accuracy_pct=accuracy_pct,
        net_wpm=net_wpm,
    )


def format_stats(stats: AttemptStats) -> str:
    return (
        f"Time: {stats.seconds:.1f}s | Gross WPM: {stats.gross_wpm:.1f} | "
        f"Accuracy: {stats.accuracy_pct:.1f}% | Net WPM: {stats.net_wpm:.1f}")


def witty_comment(stats: AttemptStats) -> str:
    good = stats.net_wpm >= 35 and stats.accuracy_pct >= 92
    pool = WITTY_PRAISE if good else WITTY_ROASTS
    return random.choice(pool)


def prompt_enter(message: str = "Press Enter to continue...") -> None:
    try:
        input(message)
    except EOFError:
        pass


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def count_down(seconds: int) -> None:
    for i in range(seconds, 0, -1):
        print(f"Starting in {i}...", end="\r", flush=True)
        time.sleep(1)
    print(" " * 40, end="\r")


def run_single_prompt(prompt_text: str) -> AttemptStats:
    print("Type this exactly. Backspaces allowed. Then hit Enter.")
    print("-")
    print(prompt_text)
    print("-")
    start = time.time()
    try:
        typed = input("> ")
    except EOFError:
        typed = ""
    end = time.time()
    stats = compute_stats(prompt_text, typed, end - start)
    print(format_stats(stats))
    print(witty_comment(stats))
    return stats


def generate_practice_line(
    allowed_chars: str,
    num_words: int = 6,
    word_len_range: Tuple[int, int] = (2, 6)) -> str:
    """Generate a practice line containing only allowed characters (plus space).

    This produces nonsense-but-typeable words using the current lesson set.
    """
    chars = list(allowed_chars)
    words: List[str] = []
    for _ in range(num_words):
        length = random.randint(*word_len_range)
        word = "".join(random.choice(chars) for _ in range(length))
        words.append(word)
    return " ".join(words)


def generate_prompts_for_lesson(allowed_chars: str,
                                rounds: int = 5) -> List[str]:
    prompts: List[str] = []
    # Include some structured patterns to build rhythm
    patterns = [
        " ".join(["asdf", "jkl;", "asdf", "jkl;"]),
        " ".join(["jj kk", "ll ;;", "aa ss", "dd ff"]),
        "asdf asdf asdf jkl; jkl; jkl;",
    ]
    # Only keep patterns that use subset of allowed chars
    filtered_patterns = []
    for p in patterns:
        if all((c == " " or c in allowed_chars) for c in p):
            filtered_patterns.append(p)
    if filtered_patterns:
        prompts.extend(filtered_patterns[:2])
    # Fill remaining with generated lines
    while len(prompts) < rounds:
        prompts.append(generate_practice_line(allowed_chars))
    return prompts[:rounds]


def load_story_progress() -> Dict:
    if not os.path.exists(STORY_PROGRESS_FILE):
        return {"current_node": "start", "history": []}
    try:
        with open(STORY_PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"current_node": "start", "history": []}
            return data
    except Exception:
        return {"current_node": "start", "history": []}


def save_story_progress(progress: Dict) -> None:
    try:
        with open(STORY_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)
    except Exception:
        pass


def reset_story_progress() -> None:
    save_story_progress({"current_node": "start", "history": []})


GOOD_ACC_THRESHOLD = 90.0
GOOD_NET_WPM_THRESHOLD = 20.0


def play_story_node(node: StoryNode) -> Tuple[float, float]:
    clear_screen()
    print(f"Story Mode — {node.title}")
    print("Lesson keys:", " ".join(list(node.lesson_keys)))
    print("Type the prompts as cleanly as you can. Backspaces allowed.\n")
    prompts = generate_prompts_for_lesson(node.lesson_keys, rounds=5)
    total_net, total_acc = 0.0, 0.0
    for i, prompt_text in enumerate(prompts, start=1):
        print(f"Round {i}/{len(prompts)}")
        stats = run_single_prompt(prompt_text)
        total_net += stats.net_wpm
        total_acc += stats.accuracy_pct
        print("")
    avg_net = total_net / len(prompts)
    avg_acc = total_acc / len(prompts)
    print("Lesson result:")
    print(f"Net WPM: {avg_net:.1f} | Accuracy: {avg_acc:.1f}%")
    save_score(f"Story: {node.id}", avg_net, avg_acc)
    return avg_net, avg_acc


def story_passed(avg_net: float, avg_acc: float) -> bool:
    return avg_acc >= GOOD_ACC_THRESHOLD and avg_net >= GOOD_NET_WPM_THRESHOLD


def story_mode_menu(story_nodes: Dict[str, StoryNode]) -> None:
    while True:
        clear_screen()
        print("Toilet Typist — Story Mode")
        progress = load_story_progress()
        current_id = progress.get("current_node", "start")
        node = story_nodes.get(current_id)
        print(f"Current chapter: {node.title if node else current_id}")
        print("\n1) Continue Story")
        print("2) Reset Story Progress")
        print("3) Back to Main Menu")
        try:
            choice = input("Select an option: ").strip()
        except EOFError:
            choice = "3"
        if choice == "1":
            play_story(story_nodes)
        elif choice == "2":
            reset_story_progress()
            print("Progress reset.")
            time.sleep(0.8)
        elif choice == "3":
            return
        else:
            print("Invalid choice.")
            time.sleep(0.8)


def play_story(story_nodes: Dict[str, StoryNode]) -> None:
    progress = load_story_progress()
    while True:
        current_id = progress.get("current_node", "start")
        node = story_nodes.get(current_id)
        if not node:
            print("Story node missing. Resetting story progress.")
            reset_story_progress()
            prompt_enter()
            return

        avg_net, avg_acc = play_story_node(node)
        passed = story_passed(avg_net, avg_acc)
        print("")
        if passed:
            print(node.success_text)
            if not node.choices:
                print("The story concludes for now. Congrats!")
                progress["history"].append({
                    "node": node.id,
                    "avg_net": round(avg_net, 1),
                    "avg_acc": round(avg_acc, 1),
                    "result": "success",
                })
                save_story_progress(progress)
                prompt_enter()
                return
            # Present choices
            print("\nChoices:")
            for idx, (label, _) in enumerate(node.choices, start=1):
                print(f"{idx}) {label}")
            try:
                sel = input("Pick your path: ").strip()
                sel_idx = int(sel) - 1
            except Exception:
                sel_idx = -1
            if sel_idx < 0 or sel_idx >= len(node.choices):
                print("Finger slip! We'll pick the first option for you.")
                sel_idx = 0
            _, next_id = node.choices[sel_idx]
            progress["history"].append({
                "node": node.id,
                "avg_net": round(avg_net, 1),
                "avg_acc": round(avg_acc, 1),
                "result": "success",
                "choice": node.choices[sel_idx][0],
            })
            progress["current_node"] = next_id
            save_story_progress(progress)
        else:
            print(node.failure_text)
            next_id = node.failure_next or node.id
            progress["history"].append({
                "node": node.id,
                "avg_net": round(avg_net, 1),
                "avg_acc": round(avg_acc, 1),
                "result": "fail",
            })
            progress["current_node"] = next_id
            save_story_progress(progress)
        print("")
        # Let the player catch a breath
        try:
            cont = input(
                "Continue? (Enter to proceed, Q to quit) ").strip().lower()
        except EOFError:
            cont = "q"
        if cont == "q":
            return


# Define the story graph with progressive lessons
STORY_NODES: Dict[str, StoryNode] = {
    "start":
    StoryNode(
        id="start",
        title="The Bathroom Quest Begins",
        lesson_keys="asdfjkl;",
        success_text=
        ("You steady your stance on the home row. The stall doors creak open."
         ),
        failure_text=
        ("Whoops! You slipped on a mysterious puddle. A splat of goop hits your shoe."
         ),
        choices=[
            ("Enter the left stall with the golden handle", "stall_left"),
            ("Enter the right stall with the neon sign", "stall_right"),
        ],
        failure_next="gross1",
    ),
    "gross1":
    StoryNode(
        id="gross1",
        title="Oopsie Puddle",
        lesson_keys="asdfjkl;",
        success_text=(
            "You wipe off the gunk and regain composure. The path splits again."
        ),
        failure_text=(
            "Another splash! Now there's stink on your socks. Keep at it."),
        choices=[
            ("Sneak into the left stall cautiously", "stall_left"),
            ("Boldly kick open the right stall", "stall_right"),
        ],
        failure_next=None,
    ),
    "stall_left":
    StoryNode(
        id="stall_left",
        title="Golden Handle Stall",
        lesson_keys="asdfjkl;ei",
        success_text=(
            "Inside, a shiny plunger rests like Excalibur. You feel stronger."
        ),
        failure_text=("A rogue drip plops onto your sleeve. Ew. Focus up!"),
        choices=[
            ("Claim the shiny plunger", "plunger"),
            ("Grab the soap of swiftness", "soap"),
        ],
        failure_next="gross2",
    ),
    "stall_right":
    StoryNode(
        id="stall_right",
        title="Neon Sign Stall",
        lesson_keys="asdfjkl;ei",
        success_text=(
            "The neon hum syncs with your keystrokes. Confidence rises."),
        failure_text=("The neon flickers and a splatter lands nearby. Yikes!"),
        choices=[
            ("Collect the towel of precision", "towel"),
            ("Don the goggles of focus", "goggles"),
        ],
        failure_next="gross2",
    ),
    "gross2":
    StoryNode(
        id="gross2",
        title="Stinky Splash",
        lesson_keys="asdfjkl;ei",
        success_text=(
            "You dodge the next splash. The air clears a bit. Choices await."),
        failure_text=(
            "Ploop. Right on the shoulder. That's just rude. Try again."),
        choices=[
            ("Seek the plunger's power", "plunger"),
            ("Equip cleaning supplies", "soap"),
        ],
        failure_next=None,
    ),
    "plunger":
    StoryNode(
        id="plunger",
        title="Plunger of Power",
        lesson_keys="asdfjkl;eiur",
        success_text=(
            "You wield the plunger like a knight. Pipes cheer silently."),
        failure_text=(
            "The plunger slips, splashing a bit of mystery sauce. Gross."),
        choices=[
            ("Advance to the Pipe Maze", "maze"),
            ("Inspect the mirror for hints", "mirror"),
        ],
        failure_next="gross3",
    ),
    "soap":
    StoryNode(
        id="soap",
        title="Soap of Swiftness",
        lesson_keys="asdfjkl;eiur",
        success_text=(
            "Hands glide! Your letters feel squeaky clean and speedy."),
        failure_text=("Soap slips! A sudsy blob lands on your shirt. Oof."),
        choices=[
            ("Dash to the Pipe Maze", "maze"),
            ("Study the warning poster", "poster"),
        ],
        failure_next="gross3",
    ),
    "towel":
    StoryNode(
        id="towel",
        title="Towel of Precision",
        lesson_keys="asdfjkl;eiur",
        success_text=(
            "You dab away distractions. Every keystroke lands crisp."),
        failure_text=(
            "Missed a dab! Drip marks your sleeve. Compose yourself."),
        choices=[
            ("Navigate the Pipe Maze", "maze"),
            ("Check under the sink", "poster"),
        ],
        failure_next="gross3",
    ),
    "goggles":
    StoryNode(
        id="goggles",
        title="Goggles of Focus",
        lesson_keys="asdfjkl;eiur",
        success_text=(
            "Tunnel vision engaged. The keys glow in your mind's eye."),
        failure_text=("Foggy lens! A drip sneaks onto your cheek. Bleh."),
        choices=[
            ("Enter the Pipe Maze", "maze"),
            ("Examine the graffiti", "mirror"),
        ],
        failure_next="gross3",
    ),
    "gross3":
    StoryNode(
        id="gross3",
        title="Mystery Sauce",
        lesson_keys="asdfjkl;eiur",
        success_text=("You dodge the sauce this time. Forward!"),
        failure_text=(
            "Splurt. Right on the back. That's a laundry problem for later."),
        choices=[
            ("Brave the Pipe Maze", "maze"),
            ("Gather clues from the mirror", "mirror"),
        ],
        failure_next=None,
    ),
    "maze":
    StoryNode(
        id="maze",
        title="Pipe Maze",
        lesson_keys="asdfjkl;eiurty",
        success_text=(
            "You weave through valves with nimble fingers. The exit shimmers."
        ),
        failure_text=(
            "A pipe burps. You get a fine mist of toilet perfume. Keep going."
        ),
        choices=[
            ("Exit to the Clean Throne", "throne"),
            ("Search a side tunnel", "poster"),
        ],
        failure_next="gross4",
    ),
    "mirror":
    StoryNode(
        id="mirror",
        title="Mirror Messages",
        lesson_keys="asdfjkl;eiurty",
        success_text=(
            "Hidden letters reveal a path forward. Confidence surges."),
        failure_text=(
            "Smudge attack! A drip trails down the glass onto your hand."),
        choices=[
            ("Follow the letters to the Throne", "throne"),
            ("Take the maintenance hatch", "poster"),
        ],
        failure_next="gross4",
    ),
    "poster":
    StoryNode(
        id="poster",
        title="Warning Poster",
        lesson_keys="asdfjkl;eiurtygh",
        success_text=(
            "You decode the fine print. Your technique levels up again."),
        failure_text=("Paper cut? Nope—just a ketchup-looking splat. Eww."),
        choices=[
            ("Final march to the Clean Throne", "throne"),
        ],
        failure_next="gross4",
    ),
    "gross4":
    StoryNode(
        id="gross4",
        title="Puke Puddle Detour",
        lesson_keys="asdfjkl;eiurtygh",
        success_text=("You sidestep the puddle gracefully. Almost there."),
        failure_text=("You step in it. Shoes make sad squish. Power through."),
        choices=[
            ("Head to the Clean Throne", "throne"),
        ],
        failure_next=None,
    ),
    "throne":
    StoryNode(
        id="throne",
        title="The Clean Throne",
        lesson_keys="asdfjkl;eiurtyghop",
        success_text=(
            "You claim the Clean Throne! Your typing quest shines brilliantly."
        ),
        failure_text=("A final prank squirt. But you made it anyway."),
        choices=[],  # End
        failure_next=None,
    ),
}


def word_drills(potty_mode: bool) -> None:
    clear_screen()
    print("Toilet Typist — Word Drills")
    print("Warm up those finger noodles.\n")
    words = POTTY_WORDS if potty_mode else [
        "river",
        "planet",
        "galaxy",
        "python",
        "keyboard",
        "coffee",
        "pepper",
        "window",
        "music",
        "garden",
        "novel",
        "signal",
    ]
    rounds = 10
    total_net, total_acc = 0.0, 0.0
    for i in range(1, rounds + 1):
        prompt_text = " ".join(random.sample(words, k=min(4, len(words))))
        print(f"\nRound {i}/{rounds}")
        stats = run_single_prompt(prompt_text)
        total_net += stats.net_wpm
        total_acc += stats.accuracy_pct
    avg_net = total_net / rounds
    avg_acc = total_acc / rounds
    print("\nAverages across drills:")
    print(f"Net WPM: {avg_net:.1f} | Accuracy: {avg_acc:.1f}%")
    save_score("Word Drills", avg_net, avg_acc)
    prompt_enter()


def sentence_sprints(potty_mode: bool) -> None:
    clear_screen()
    print("Toilet Typist — Sentence Sprints")
    print("Type full sentences without spraying typos everywhere.\n")
    sentences = SILLY_SENTENCES if potty_mode else [
        "Practice makes progress, not perfection.",
        "Fast is fine, but accuracy is final.",
        "Steady hands, focused mind, smooth typing.",
        "Breathe, relax, and trust your muscle memory.",
    ]
    rounds = min(6, len(sentences))
    picks = random.sample(sentences, k=rounds)
    total_net, total_acc = 0.0, 0.0
    for i, sentence in enumerate(picks, start=1):
        print(f"\nSprint {i}/{rounds}")
        stats = run_single_prompt(sentence)
        total_net += stats.net_wpm
        total_acc += stats.accuracy_pct
    avg_net = total_net / rounds
    avg_acc = total_acc / rounds
    print("\nAverages across sprints:")
    print(f"Net WPM: {avg_net:.1f} | Accuracy: {avg_acc:.1f}%")
    save_score("Sentence Sprints", avg_net, avg_acc)
    prompt_enter()


def timed_boss_battle(potty_mode: bool, duration_seconds: int = 60) -> None:
    clear_screen()
    print("Toilet Typist — Boss Battle (60s)")
    print(
        "Type as many prompts as you can in the time limit. Accuracy matters.\n"
    )
    bank = (POTTY_WORDS + SILLY_SENTENCES) if potty_mode else (POTTY_WORDS + [
        "Practice daily and your speed will rise.",
        "Accuracy first, then speed follows.",
        "Consistency beats intensity over time.",
    ])
    random.shuffle(bank)
    count_down(3)
    end_time = time.time() + duration_seconds
    total_chars_typed = 0
    total_correct_chars = 0
    prompts_attempted = 0
    while time.time() < end_time:
        prompt_text = random.choice(bank)
        print("-")
        print(prompt_text)
        print("-")
        start = time.time()
        remaining = max(0.0, end_time - start)
        try:
            # No built-in input timeout; just encourage fast typing.
            typed = input("> ")
        except EOFError:
            typed = ""
        now = time.time()
        elapsed = now - start
        total_chars_typed += len(typed)
        correct = sum(1 for i, c in enumerate(typed)
                      if i < len(prompt_text) and prompt_text[i] == c)
        total_correct_chars += correct
        prompts_attempted += 1
        print(f"Good hustle. {max(0, int(end_time - now))}s left.\n")
    seconds = float(duration_seconds)
    accuracy_pct = (total_correct_chars / max(1, total_chars_typed)
                    ) * 100.0 if total_chars_typed else 0.0
    gross_wpm = (total_chars_typed / 5.0) / (seconds / 60.0)
    net_wpm = gross_wpm * (accuracy_pct / 100.0)
    print("Time! Boss defeated? Let's see:")
    print(
        f"Prompts: {prompts_attempted} | Gross WPM: {gross_wpm:.1f} | Accuracy: {accuracy_pct:.1f}% | Net WPM: {net_wpm:.1f}"
    )
    if net_wpm >= 40 and accuracy_pct >= 95:
        print(random.choice(WITTY_PRAISE))
    else:
        print(random.choice(WITTY_ROASTS))
    save_score("Boss Battle 60s", net_wpm, accuracy_pct)
    prompt_enter()


def view_scores() -> None:
    clear_screen()
    scores = load_scores()
    print("Toilet Typist — High Scores")
    if not scores:
        print("No scores yet. The scoreboard is dryer than a desert toilet.")
        prompt_enter()
        return
    # Show last 10
    last = scores[-10:]
    for s in last:
        ts = time.strftime("%Y-%m-%d %H:%M:%S",
                           time.localtime(s.get("timestamp", 0)))
        print(
            f"{ts} | {s.get('mode','?'):<18} | Net {s.get('net_wpm',0):>5} WPM | Acc {s.get('accuracy_pct',0):>5}%"
        )
    prompt_enter()


def main_menu() -> None:
    potty_mode = True  # potty humor on by default
    while True:
        clear_screen()
        print("Toilet Typist — The Witty Typing Trainer")
        print("- Where typos get flushed and WPM goes up -\n")
        print("1) Word Drills")
        print("2) Sentence Sprints")
        print("3) Boss Battle (60s test)")
        print("4) Story Mode")
        print(f"5) Toggle Potty Humor: {'ON' if potty_mode else 'OFF'}")
        print("6) View High Scores")
        print("7) Quit")
        try:
            choice = input("Select an option: ").strip()
        except EOFError:
            choice = "7"
        if choice == "1":
            word_drills(potty_mode)
        elif choice == "2":
            sentence_sprints(potty_mode)
        elif choice == "3":
            timed_boss_battle(potty_mode, duration_seconds=60)
        elif choice == "4":
            story_mode_menu(STORY_NODES)
        elif choice == "5":
            potty_mode = not potty_mode
            print(f"Potty humor {'enabled' if potty_mode else 'disabled'}. ✨")
            time.sleep(0.8)
        elif choice == "6":
            view_scores()
        elif choice == "7":
            print("Goodbye! May your typos be few and your snacks abundant.")
            break
        else:
            print("Invalid choice. Keyboard slipped? Try again.")
            time.sleep(1.0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nSee ya!")
