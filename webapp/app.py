from __future__ import annotations

import os
import sys
import random
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Ensure project root is on sys.path so we can import toilet_typist.py when running this file directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Reuse core logic from the terminal app
from toilet_typist import (
    POTTY_WORDS,
    SILLY_SENTENCES,
    STORY_NODES,
    compute_stats,
    load_scores,
    generate_prompts_for_lesson,
    load_story_progress,
    reset_story_progress,
    save_score,
    save_story_progress,
    story_passed,
    witty_comment,
)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # NOTE: For production, override via environment variable
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

    # ----- Helpers -----
    def get_potty_mode() -> bool:
        return bool(session.get("potty_mode", True))

    def set_potty_mode(enabled: bool) -> None:
        session["potty_mode"] = bool(enabled)

    # ----- Pages -----
    @app.get("/")
    def index():
        return render_template("index.html", potty_mode=get_potty_mode())

    @app.post("/toggle_potty")
    def toggle_potty():
        set_potty_mode(not get_potty_mode())
        return redirect(url_for("index"))

    @app.get("/drills")
    def drills_page():
        return render_template("drills.html")

    @app.get("/sprints")
    def sprints_page():
        return render_template("sprints.html")

    @app.get("/boss")
    def boss_page():
        return render_template("boss.html")

    @app.get("/story")
    def story_page():
        return render_template("story.html")

    @app.get("/scores")
    def scores_page():
        # No server-side render of data; page fetches via API
        return render_template("scores.html")

    # ----- Settings API -----
    @app.get("/api/settings")
    def api_settings():
        return jsonify({"potty_mode": get_potty_mode()})

    # ----- Scores API -----
    @app.get("/api/scores/last")
    def api_scores_last():
        last = (load_scores() or [])[-10:]
        return jsonify({"scores": last})

    # ----- Word Drills API -----
    @app.post("/api/drills/start")
    def api_drills_start():
        rounds = int(request.json.get("rounds", 10))
        session["drills"] = {
            "rounds": rounds,
            "current": 0,
            "total_net": 0.0,
            "total_acc": 0.0,
        }
        return jsonify({"ok": True, "rounds": rounds})

    @app.get("/api/drills/next")
    def api_drills_next():
        state = session.get("drills") or {}
        rounds = int(state.get("rounds", 10))
        current = int(state.get("current", 0))
        if current >= rounds:
            return jsonify({"done": True})

        potty = get_potty_mode()
        words = POTTY_WORDS if potty else [
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
        sample_count = min(4, len(words))
        prompt_text = " ".join(random.sample(words, k=sample_count))
        # Store the prompt to validate on submit
        state["current_prompt"] = prompt_text
        session["drills"] = state
        return jsonify({
            "done": False,
            "round": current + 1,
            "rounds": rounds,
            "prompt": prompt_text,
        })

    @app.post("/api/drills/submit")
    def api_drills_submit():
        data = request.json or {}
        typed = str(data.get("typed", ""))
        seconds = float(data.get("seconds", 0.0))
        state = session.get("drills") or {}
        expected = str(state.get("current_prompt", ""))
        stats = compute_stats(expected, typed, seconds)
        state["current"] = int(state.get("current", 0)) + 1
        state["total_net"] = float(state.get("total_net", 0.0)) + stats.net_wpm
        state["total_acc"] = float(state.get("total_acc", 0.0)) + stats.accuracy_pct
        session["drills"] = state

        done = state["current"] >= int(state.get("rounds", 10))
        if done:
            rounds = int(state.get("rounds", 10))
            avg_net = state["total_net"] / max(1, rounds)
            avg_acc = state["total_acc"] / max(1, rounds)
            save_score("Word Drills", avg_net, avg_acc)
            return jsonify({
                "done": True,
                "stats": asdict(stats),
                "summary": {
                    "avg_net": round(avg_net, 1),
                    "avg_acc": round(avg_acc, 1),
                },
                "comment": witty_comment(stats),
            })
        else:
            return jsonify({
                "done": False,
                "stats": asdict(stats),
                "comment": witty_comment(stats),
            })

    # ----- Sentence Sprints API -----
    @app.post("/api/sprints/start")
    def api_sprints_start():
        potty = get_potty_mode()
        sentences = SILLY_SENTENCES if potty else [
            "Practice makes progress, not perfection.",
            "Fast is fine, but accuracy is final.",
            "Steady hands, focused mind, smooth typing.",
            "Breathe, relax, and trust your muscle memory.",
        ]
        rounds = min(6, len(sentences))
        picks = random.sample(sentences, k=rounds)
        session["sprints"] = {
            "rounds": rounds,
            "current": 0,
            "total_net": 0.0,
            "total_acc": 0.0,
            "picks": picks,
        }
        return jsonify({"ok": True, "rounds": rounds})

    @app.get("/api/sprints/next")
    def api_sprints_next():
        state = session.get("sprints") or {}
        rounds = int(state.get("rounds", 0))
        current = int(state.get("current", 0))
        if current >= rounds:
            return jsonify({"done": True})
        sentence = (state.get("picks") or [""])[current]
        state["current_prompt"] = sentence
        session["sprints"] = state
        return jsonify({
            "done": False,
            "round": current + 1,
            "rounds": rounds,
            "prompt": sentence,
        })

    @app.post("/api/sprints/submit")
    def api_sprints_submit():
        data = request.json or {}
        typed = str(data.get("typed", ""))
        seconds = float(data.get("seconds", 0.0))
        state = session.get("sprints") or {}
        expected = str(state.get("current_prompt", ""))
        stats = compute_stats(expected, typed, seconds)
        state["current"] = int(state.get("current", 0)) + 1
        state["total_net"] = float(state.get("total_net", 0.0)) + stats.net_wpm
        state["total_acc"] = float(state.get("total_acc", 0.0)) + stats.accuracy_pct
        session["sprints"] = state

        done = state["current"] >= int(state.get("rounds", 0))
        if done:
            rounds = int(state.get("rounds", 1))
            avg_net = state["total_net"] / max(1, rounds)
            avg_acc = state["total_acc"] / max(1, rounds)
            save_score("Sentence Sprints", avg_net, avg_acc)
            return jsonify({
                "done": True,
                "stats": asdict(stats),
                "summary": {
                    "avg_net": round(avg_net, 1),
                    "avg_acc": round(avg_acc, 1),
                },
                "comment": witty_comment(stats),
            })
        else:
            return jsonify({
                "done": False,
                "stats": asdict(stats),
                "comment": witty_comment(stats),
            })

    # ----- Boss Battle (60s) API -----
    @app.post("/api/boss/start")
    def api_boss_start():
        duration_seconds = int(request.json.get("duration", 60))
        potty = get_potty_mode()
        bank = (POTTY_WORDS + SILLY_SENTENCES) if potty else (POTTY_WORDS + [
            "Practice daily and your speed will rise.",
            "Accuracy first, then speed follows.",
            "Consistency beats intensity over time.",
        ])
        random.shuffle(bank)
        state = {
            "end_time": time.time() + duration_seconds,
            "totals": {
                "chars_typed": 0,
                "correct_chars": 0,
                "prompts": 0,
            },
            "bank": bank,
        }
        session["boss"] = state
        return jsonify({
            "ok": True,
            "ends_in": duration_seconds,
            "now": time.time(),
        })

    @app.get("/api/boss/next")
    def api_boss_next():
        state = session.get("boss") or {}
        end_time = float(state.get("end_time", 0))
        remaining = max(0, int(end_time - time.time()))
        if remaining <= 0:
            return jsonify({"done": True})
        bank = state.get("bank") or []
        prompt_text = random.choice(bank) if bank else ""
        state["current_prompt"] = prompt_text
        session["boss"] = state
        return jsonify({"done": False, "prompt": prompt_text, "remaining": remaining})

    @app.post("/api/boss/submit")
    def api_boss_submit():
        data = request.json or {}
        typed = str(data.get("typed", ""))
        state = session.get("boss") or {}
        expected = str(state.get("current_prompt", ""))
        end_time = float(state.get("end_time", 0))
        remaining = max(0.0, end_time - time.time())
        totals = state.get("totals") or {"chars_typed": 0, "correct_chars": 0, "prompts": 0}

        # Update totals
        totals["chars_typed"] += len(typed)
        correct = sum(1 for i, c in enumerate(typed) if i < len(expected) and expected[i] == c)
        totals["correct_chars"] += correct
        totals["prompts"] += 1
        state["totals"] = totals
        session["boss"] = state

        if remaining <= 0:
            seconds = float(max(1, int(data.get("duration", 60))))
            accuracy_pct = (totals["correct_chars"] / max(1, totals["chars_typed"])) * 100.0 if totals["chars_typed"] else 0.0
            gross_wpm = (totals["chars_typed"] / 5.0) / (seconds / 60.0)
            net_wpm = gross_wpm * (accuracy_pct / 100.0)
            save_score("Boss Battle 60s", net_wpm, accuracy_pct)
            return jsonify({
                "done": True,
                "summary": {
                    "prompts": totals["prompts"],
                    "gross_wpm": round(gross_wpm, 1),
                    "accuracy_pct": round(accuracy_pct, 1),
                    "net_wpm": round(net_wpm, 1),
                },
            })
        else:
            return jsonify({"done": False, "remaining": int(remaining)})

    # ----- Story Mode API -----
    @app.get("/api/story/current")
    def api_story_current():
        progress = load_story_progress()
        current_id = progress.get("current_node", "start")
        node = STORY_NODES.get(current_id)
        if not node:
            return jsonify({"error": "missing_node", "current": current_id}), 400
        return jsonify({
            "current": current_id,
            "node": {
                "id": node.id,
                "title": node.title,
                "lesson_keys": node.lesson_keys,
                "success_text": node.success_text,
                "failure_text": node.failure_text,
                "choices": node.choices,
                "failure_next": node.failure_next,
            },
        })

    @app.post("/api/story/reset")
    def api_story_reset():
        reset_story_progress()
        return jsonify({"ok": True})

    @app.post("/api/story/start")
    def api_story_start():
        progress = load_story_progress()
        current_id = progress.get("current_node", "start")
        node = STORY_NODES.get(current_id)
        if not node:
            return jsonify({"error": "missing_node"}), 400
        prompts = generate_prompts_for_lesson(node.lesson_keys, rounds=5)
        session["story_run"] = {
            "node_id": node.id,
            "prompts": prompts,
            "current": 0,
            "total_net": 0.0,
            "total_acc": 0.0,
        }
        return jsonify({"ok": True, "rounds": len(prompts)})

    @app.get("/api/story/next")
    def api_story_next():
        state = session.get("story_run") or {}
        prompts: List[str] = state.get("prompts") or []
        current = int(state.get("current", 0))
        if current >= len(prompts):
            return jsonify({"done": True})
        prompt_text = prompts[current]
        state["current_prompt"] = prompt_text
        session["story_run"] = state
        return jsonify({
            "done": False,
            "round": current + 1,
            "rounds": len(prompts),
            "prompt": prompt_text,
        })

    @app.post("/api/story/submit")
    def api_story_submit():
        data = request.json or {}
        typed = str(data.get("typed", ""))
        seconds = float(data.get("seconds", 0.0))
        state = session.get("story_run") or {}
        expected = str(state.get("current_prompt", ""))
        stats = compute_stats(expected, typed, seconds)
        state["current"] = int(state.get("current", 0)) + 1
        state["total_net"] = float(state.get("total_net", 0.0)) + stats.net_wpm
        state["total_acc"] = float(state.get("total_acc", 0.0)) + stats.accuracy_pct
        session["story_run"] = state

        done = state["current"] >= len(state.get("prompts") or [])
        if not done:
            return jsonify({
                "done": False,
                "stats": asdict(stats),
                "comment": witty_comment(stats),
            })

        # Chapter complete: compute averages and update narrative
        avg_net = state["total_net"] / max(1, len(state.get("prompts") or [1]))
        avg_acc = state["total_acc"] / max(1, len(state.get("prompts") or [1]))
        progress = load_story_progress()
        node_id = str(state.get("node_id"))
        node = STORY_NODES.get(node_id)
        if not node:
            return jsonify({"error": "missing_node"}), 400
        passed = story_passed(avg_net, avg_acc)

        # Save overall chapter score
        save_score(f"Story: {node.id}", avg_net, avg_acc)

        if passed:
            # End of story path?
            if not node.choices:
                progress.setdefault("history", []).append({
                    "node": node.id,
                    "avg_net": round(avg_net, 1),
                    "avg_acc": round(avg_acc, 1),
                    "result": "success",
                })
                save_story_progress(progress)
                return jsonify({
                    "done": True,
                    "chapter_result": "end",
                    "avg_net": round(avg_net, 1),
                    "avg_acc": round(avg_acc, 1),
                    "success_text": node.success_text,
                })

            # Present choices client-side
            progress.setdefault("history", []).append({
                "node": node.id,
                "avg_net": round(avg_net, 1),
                "avg_acc": round(avg_acc, 1),
                "result": "success",
            })
            save_story_progress(progress)
            return jsonify({
                "done": True,
                "chapter_result": "passed",
                "avg_net": round(avg_net, 1),
                "avg_acc": round(avg_acc, 1),
                "success_text": node.success_text,
                "choices": node.choices,
            })
        else:
            next_id = node.failure_next or node.id
            progress.setdefault("history", []).append({
                "node": node.id,
                "avg_net": round(avg_net, 1),
                "avg_acc": round(avg_acc, 1),
                "result": "fail",
            })
            progress["current_node"] = next_id
            save_story_progress(progress)
            return jsonify({
                "done": True,
                "chapter_result": "failed",
                "avg_net": round(avg_net, 1),
                "avg_acc": round(avg_acc, 1),
                "failure_text": node.failure_text,
                "next_id": next_id,
            })

    @app.post("/api/story/choose")
    def api_story_choose():
        data = request.json or {}
        label = str(data.get("label", ""))
        next_id = str(data.get("next_id", ""))
        progress = load_story_progress()
        current_id = progress.get("current_node", "start")
        node = STORY_NODES.get(current_id)
        if not node:
            return jsonify({"error": "missing_node"}), 400
        # If invalid, default to first choice
        choice_ids = [cid for _, cid in node.choices]
        if next_id not in choice_ids:
            next_id = node.choices[0][1]
            label = node.choices[0][0]
        progress.setdefault("history", []).append({
            "node": node.id,
            "result": "choice",
            "choice": label or next_id,
        })
        progress["current_node"] = next_id
        save_story_progress(progress)
        return jsonify({"ok": True, "current_node": next_id})

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)


