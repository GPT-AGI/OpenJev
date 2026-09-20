"""Live experiments against the real Jev API, rendered as charts and animations.

Reads TYPESAFE_API_KEY from .env / environment. Results (raw JSON) go to
``results/`` and figures go to ``docs/assets/experiments/``.

    .venv/bin/python scripts/experiments.py all
    .venv/bin/python scripts/experiments.py pelican | surface | latency | maze

Experiments
  pelican   "Pelican → Bicycle" morph: 13 descriptions sliding from pure pelican to pure
            bicycle; Jev answers "is this a bird?" / "is this a vehicle?" / "could it ride?".
            Shows calibrated probabilities crossing over as the description morphs.
  surface   3D decision landscape: sweep (days down × revenue lost) and plot P(urgent) and
            expected frustration as surfaces.
  latency   Latency vs number of questions in one request (1..27), 3 repeats, with a fan chart.
            The "adding questions barely changes latency" claim, measured.
  maze      Jev plays a gridworld: every step is a single Choice over {up,down,left,right}
            with the ASCII map as state. Rendered as a GIF with the probability of each move.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OUT = ROOT / "docs" / "assets" / "experiments"
RES = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("OPENJEV_REF_MODEL", "jev-latest")
REPLOT = "--replot" in sys.argv

BG = "#0d1117"
PANEL = "#161b22"
FG = "#e6edf3"
DIM = "#8b949e"
CYAN = "#38bdf8"
MAGENTA = "#e879f9"
YELLOW = "#facc15"
GREEN = "#4ade80"
RED = "#f87171"

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": PANEL,
        "axes.edgecolor": "#30363d",
        "axes.labelcolor": FG,
        "xtick.color": DIM,
        "ytick.color": DIM,
        "text.color": FG,
        "grid.color": "#30363d",
        "font.family": "monospace",
        "font.size": 11,
    }
)


def client() -> TypeSafeClient:
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY not set (put it in .env)")
    return TypeSafeClient(model=MODEL, timeout=60)


def timed(c: TypeSafeClient, state, questions):
    t0 = time.perf_counter()
    r = c.system_one(state=state, questions=questions)
    return r, (time.perf_counter() - t0) * 1000


def dump(name: str, payload) -> None:
    (RES / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))


# ============================================================================ 1. pelican morph
PELICAN_MORPH = [
    "A large white pelican with a long orange bill and a throat pouch, standing on a pier.",
    "A pelican spreading its wings, webbed feet planted on wooden planks.",
    "A pelican perched awkwardly on a bicycle seat, wings folded.",
    "A pelican sitting on a bicycle, one webbed foot resting on a pedal.",
    "A pelican gripping the handlebars of a bicycle with its bill, feet on the pedals.",
    "A pelican riding a bicycle down a boardwalk, wings out for balance.",
    "A bicycle being ridden by a pelican, the wheels spinning fast.",
    "A bicycle with a pelican-shaped bell mounted on the handlebars.",
    "A bicycle painted white and orange, leaning against a pier railing.",
    "A red road bicycle with drop handlebars and thin tyres.",
    "A steel-frame bicycle with two wheels, a chain and pedals, parked by a wall.",
]


def exp_pelican() -> None:
    c = client()
    qs = {
        "bird": Noul(instructions="The description is primarily about a bird."),
        "vehicle": Noul(instructions="The description is primarily about a vehicle."),
        "riding": Noul(instructions="Something in the description is riding a bicycle."),
        "subject": Choice(
            instructions="What is the main subject?",
            criteria={
                "pelican": "A pelican or bird is the main subject",
                "bicycle": "A bicycle is the main subject",
                "both": "A pelican and a bicycle share the spotlight equally",
            },
        ),
        "absurdity": Score(
            instructions="How absurd or surreal is the scene?",
            criteria=["Completely ordinary", "Slightly odd", "Clearly surreal", "Internet meme material"],
        ),
    }
    rows = []
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda s: timed(c, s, qs), PELICAN_MORPH))
    for s, (r, ms) in zip(PELICAN_MORPH, results):
        a = r.answers
        rows.append(
            {
                "state": s,
                "bird": a["bird"].noul,
                "vehicle": a["vehicle"].noul,
                "riding": a["riding"].noul,
                "subject": a["subject"].choice,
                "subject_probs": a["subject"].probabilities,
                "absurdity": a["absurdity"].score,
                "latency_ms": ms,
            }
        )
    dump("pelican", rows)

    x = np.arange(len(rows))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8.5), gridspec_kw={"height_ratios": [3, 2]})
    fig.suptitle(
        "Jev's pelican test: morphing a pelican into a bicycle, one sentence at a time", fontsize=14, color=FG
    )

    for key, color, label in [
        ("bird", GREEN, "P(bird)"),
        ("vehicle", CYAN, "P(vehicle)"),
        ("riding", MAGENTA, "P(riding a bicycle)"),
    ]:
        y = [r[key] for r in rows]
        ax1.plot(x, y, "-o", color=color, lw=2.5, ms=7, label=label)
        ax1.fill_between(x, y, alpha=0.08, color=color)
    ax1.set_ylim(-0.03, 1.03)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"#{i}" for i in x])
    ax1.set_ylabel("probability (noul)")
    ax1.grid(True, alpha=0.4)
    ax1.legend(loc="center right", facecolor=PANEL, edgecolor="#30363d")
    ax1.axvspan(2.5, 6.5, color=YELLOW, alpha=0.06)
    ax1.text(4.5, 0.5, "pelican riding a bicycle\nzone", ha="center", color=YELLOW, fontsize=10)

    ax2.bar(x, [r["absurdity"] for r in rows], color=YELLOW, alpha=0.85, width=0.6)
    ax2.set_ylim(0, 3.2)
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_yticklabels(["ordinary", "odd", "surreal", "meme"])
    ax2.set_ylabel("absurdity (score)")
    ax2.set_xticks(x)
    ax2.set_xticklabels([r["subject"] for r in rows], rotation=0, color=DIM)
    ax2.set_xlabel("Jev's chosen main subject per description")
    ax2.grid(True, axis="y", alpha=0.4)
    med = statistics.median(r["latency_ms"] for r in rows)
    fig.text(
        0.99,
        0.01,
        f"model {MODEL} · {len(rows)} states × 5 questions · median {med:.0f} ms/request",
        ha="right",
        color=DIM,
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(OUT / "pelican.png", dpi=130)
    print("pelican ->", OUT / "pelican.png")


# ============================================================================ 2. 3D surface
DAYS = [0, 1, 2, 3, 5, 7, 10, 14]
REVENUE = [0, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000]


def exp_surface() -> None:
    c = client()
    qs = {
        "urgent": Noul(instructions="This ticket requires immediate escalation to an on-call engineer."),
        "frustration": Score(
            instructions="How frustrated is the customer?",
            criteria=["Calm", "Annoyed but polite", "Angry", "Threatening to churn"],
        ),
        "priority": Choice(
            instructions="Which support priority should this ticket get?",
            criteria={"P3": "Normal queue", "P2": "Same day", "P1": "Drop everything"},
        ),
    }
    grid = [(d, rv) for d in DAYS for rv in REVENUE]

    def state(d, rv):
        return {
            "ticket": (
                f"Our Stripe integration has been failing for {d} day{'s' if d != 1 else ''}. "
                f"We estimate we have lost about ${rv:,} in revenue so far."
            ),
            "plan": "enterprise",
        }

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda g: timed(c, state(*g), qs), grid))
    rows = []
    for (d, rv), (r, ms) in zip(grid, results):
        a = r.answers
        rows.append(
            {
                "days": d,
                "revenue": rv,
                "urgent": a["urgent"].noul,
                "frustration": a["frustration"].score,
                "priority": a["priority"].choice,
                "priority_probs": a["priority"].probabilities,
                "latency_ms": ms,
            }
        )
    dump("surface", rows)

    U = np.array([r["urgent"] for r in rows]).reshape(len(DAYS), len(REVENUE))
    F = np.array([r["frustration"] for r in rows]).reshape(len(DAYS), len(REVENUE))
    P1 = np.array([r["priority_probs"]["P1"] for r in rows]).reshape(len(DAYS), len(REVENUE))
    X, Y = np.meshgrid(np.arange(len(REVENUE)), np.arange(len(DAYS)))

    fig = plt.figure(figsize=(16, 6.5))
    fig.suptitle("Decision landscape: 64 tickets, 3 questions each, one Jev call per ticket", fontsize=14)
    for i, (Z, title, cmap, zl) in enumerate(
        [
            (U, "P(urgent)", "viridis", (0, 1)),
            (F, "expected frustration", "magma", (0, 3)),
            (P1, "P(priority = P1)", "plasma", (0, 1)),
        ]
    ):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        ax.set_facecolor(BG)
        ax.plot_surface(X, Y, Z, cmap=cmap, edgecolor="#30363d", lw=0.3, alpha=0.95, antialiased=True)
        ax.contour(X, Y, Z, zdir="z", offset=zl[0], cmap=cmap, alpha=0.6)
        ax.set_xticks(range(len(REVENUE)))
        ax.set_xticklabels([f"{v // 1000}k" if v >= 1000 else str(v) for v in REVENUE], fontsize=8, color=DIM)
        ax.set_yticks(range(len(DAYS)))
        ax.set_yticklabels(DAYS, fontsize=8, color=DIM)
        ax.set_xlabel("revenue lost ($)", color=DIM, labelpad=8)
        ax.set_ylabel("days down", color=DIM, labelpad=8)
        ax.set_zlim(*zl)
        ax.set_title(title, color=FG, pad=10)
        ax.xaxis.pane.set_facecolor(PANEL)
        ax.yaxis.pane.set_facecolor(PANEL)
        ax.zaxis.pane.set_facecolor(PANEL)
        ax.grid(False)
        ax.view_init(elev=28, azim=-135)
    med = statistics.median(r["latency_ms"] for r in rows)
    fig.text(
        0.99,
        0.01,
        f"model {MODEL} · median {med:.0f} ms/request · 8 concurrent",
        ha="right",
        color=DIM,
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    fig.savefig(OUT / "surface.png", dpi=130)
    print("surface ->", OUT / "surface.png")

    # rotating GIF of the urgency surface
    frames = []
    from PIL import Image

    for az in range(-180, 180, 6):
        f2 = plt.figure(figsize=(7, 6))
        ax = f2.add_subplot(111, projection="3d")
        ax.set_facecolor(BG)
        ax.plot_surface(X, Y, U, cmap="viridis", edgecolor="#30363d", lw=0.3, alpha=0.95)
        ax.set_zlim(0, 1)
        ax.set_xticks(range(len(REVENUE)))
        ax.set_xticklabels([f"{v // 1000}k" if v >= 1000 else str(v) for v in REVENUE], fontsize=7, color=DIM)
        ax.set_yticks(range(len(DAYS)))
        ax.set_yticklabels(DAYS, fontsize=7, color=DIM)
        ax.set_xlabel("revenue lost", color=DIM)
        ax.set_ylabel("days down", color=DIM)
        ax.set_title("P(urgent) — Jev decision surface", color=FG)
        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.set_facecolor(PANEL)
        ax.grid(False)
        ax.view_init(elev=28, azim=az)
        f2.tight_layout()
        f2.canvas.draw()
        frames.append(
            Image.frombuffer(
                "RGBA", f2.canvas.get_width_height(), f2.canvas.buffer_rgba(), "raw", "RGBA", 0, 1
            ).convert("P", palette=Image.ADAPTIVE)
        )
        plt.close(f2)
    frames[0].save(OUT / "surface-rotate.gif", save_all=True, append_images=frames[1:], duration=70, loop=0)
    print("surface ->", OUT / "surface-rotate.gif")


# ============================================================================ 3. latency scaling
TICKET = (
    "Hi, our Stripe integration has been failing for 3 days and payments are completely down. "
    "We're an enterprise customer and losing roughly $5,000 a day. Two previous tickets were closed "
    "without a fix. If this is not resolved today we will have to evaluate alternatives."
)
Q_POOL = [
    ("revenue_impacted", Noul(instructions="Revenue is currently impacted.")),
    ("integration_issue", Noul(instructions="An integration issue is present.")),
    ("security_concern", Noul(instructions="A security concern is present.")),
    ("duplicate_charge", Noul(instructions="A duplicate charge is reported.")),
    ("human_needed", Noul(instructions="Human attention is needed.")),
    ("feature_request", Noul(instructions="This is primarily a feature request.")),
    ("churn_risk", Noul(instructions="There is a credible churn risk.")),
    ("prod_down", Noul(instructions="Production capability is down.")),
    ("server_error", Noul(instructions="A server error is reported.")),
    ("threatening", Noul(instructions="The language is personally threatening.")),
    ("deadline", Noul(instructions="A concrete deadline is stated.")),
    ("prior_tickets", Noul(instructions="Previous tickets are mentioned.")),
    ("enterprise", Noul(instructions="The customer is on an enterprise plan.")),
    (
        "impact",
        Choice(
            instructions="What business impact?",
            criteria={"none": "No impact", "degraded": "Degraded service", "down": "Fully down"},
        ),
    ),
    (
        "health",
        Choice(
            instructions="Account health status?",
            criteria={"healthy": "Fine", "watch": "Needs attention", "at_risk": "Likely to churn"},
        ),
    ),
    (
        "scope",
        Choice(
            instructions="Incident scope?",
            criteria={"single_account": "One customer", "many": "Many customers", "unknown": "Cannot tell"},
        ),
    ),
    (
        "department",
        Choice(
            instructions="Primary department?",
            criteria={"billing": "Billing", "technical": "Technical", "sales": "Sales"},
        ),
    ),
    (
        "resolution",
        Choice(
            instructions="Requested resolution?",
            criteria={"restore_service": "Restore service", "refund": "Refund", "explanation": "Explanation"},
        ),
    ),
    (
        "response_deadline",
        Choice(
            instructions="Response deadline?",
            criteria={"today": "Today", "this_week": "This week", "none": "None"},
        ),
    ),
    (
        "category",
        Choice(
            instructions="Issue category?",
            criteria={
                "integration_failure": "Integration failure",
                "billing_error": "Billing error",
                "question": "Question",
            },
        ),
    ),
    ("churn_level", Score(instructions="Churn likelihood?", criteria=["Low", "Medium", "High"])),
    (
        "certainty",
        Score(instructions="Sentiment certainty?", criteria=["Unclear", "Somewhat clear", "Very clear"]),
    ),
    ("security_level", Score(instructions="Security risk level?", criteria=["None", "Low", "High"])),
    ("financial", Score(instructions="Financial impact level?", criteria=["None", "Minor", "Major"])),
    (
        "specificity",
        Score(instructions="Technical specificity?", criteria=["Vague", "Some detail", "Very specific"]),
    ),
    ("complexity", Score(instructions="Resolution complexity?", criteria=["Trivial", "Moderate", "Hard"])),
    ("frustration", Score(instructions="Customer frustration?", criteria=["Calm", "Annoyed", "Furious"])),
]


def exp_latency(repeats: int = 3) -> None:
    ns = [1, 2, 3, 5, 8, 12, 16, 20, 24, 27]
    cached = RES / "latency.json"
    if REPLOT and cached.exists():
        rows = json.loads(cached.read_text())
    else:
        c = client()
        rows = []
        for n in ns:
            qs = dict(Q_POOL[:n])
            for rep in range(repeats):
                r, ms = timed(c, TICKET, qs)
                rows.append(
                    {
                        "n": n,
                        "rep": rep,
                        "latency_ms": ms,
                        "in": r.usage.input_tokens,
                        "out": r.usage.output_tokens,
                    }
                )
                print(
                    f"n={n:2d} rep={rep} {ms:7.1f} ms  in={r.usage.input_tokens} out={r.usage.output_tokens}"
                )
        dump("latency", rows)

    fig, ax = plt.subplots(figsize=(12, 6))
    med = [statistics.median(r["latency_ms"] for r in rows if r["n"] == n) for n in ns]
    lo = [min(r["latency_ms"] for r in rows if r["n"] == n) for n in ns]
    hi = [max(r["latency_ms"] for r in rows if r["n"] == n) for n in ns]
    ax.fill_between(ns, lo, hi, color=CYAN, alpha=0.15, label="min–max")
    ax.plot(ns, med, "-o", color=CYAN, lw=2.5, ms=7, label=f"Jev ({MODEL}) median")
    for n, m in zip(ns, med):
        ax.annotate(
            f"{m:.0f}", (n, m), textcoords="offset points", xytext=(0, 9), ha="center", color=FG, fontsize=9
        )
    # reference: autoregressive JSON at ~25 output tokens/question, 40 tok/s, 600 ms TTFT
    ar = [600 + n * 25 / 40 * 1000 for n in ns]
    ax.plot(
        ns,
        ar,
        "--",
        color=MAGENTA,
        lw=2,
        label="autoregressive JSON, modelled (600 ms TTFT + 25 tok/q @ 40 tok/s), not measured",
    )
    ax.set_yscale("log")
    ax.set_ylim(100, 30000)
    ax.set_yticks([100, 300, 1000, 3000, 10000, 30000])
    ax.set_yticklabels(["100 ms", "300 ms", "1 s", "3 s", "10 s", "30 s"])
    ax.set_xlabel("questions in one request")
    ax.set_ylabel("latency (log scale)")
    ax.set_title(
        "Does adding questions cost latency? 1 → 27 questions, same state, 3 repeats, measured live", color=FG
    )
    ax.grid(True, alpha=0.4)
    ax.legend(facecolor=PANEL, edgecolor="#30363d", loc="upper left")
    ax.set_xticks(ns)
    fig.tight_layout()
    fig.savefig(OUT / "latency.png", dpi=130)
    print("latency ->", OUT / "latency.png")


# ============================================================================ 4. maze
MAZE = [
    "##########",
    "#S.....#.#",
    "#.####.#.#",
    "#.#..#.#.#",
    "#.#.##.#.#",
    "#.#....#.#",
    "#.######.#",
    "#........#",
    "#.######G#",
    "##########",
]
MOVES = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def exp_maze(max_steps: int = 40) -> None:
    grid = [list(r) for r in MAZE]
    pos = next((i, j) for i, r in enumerate(MAZE) for j, ch in enumerate(r) if ch == "S")
    goal = next((i, j) for i, r in enumerate(MAZE) for j, ch in enumerate(r) if ch == "G")
    path = [pos]
    steps = []
    visited = {pos}
    cached = RES / "maze.json"
    if REPLOT and cached.exists():
        steps = json.loads(cached.read_text())
        for st in steps:
            st["pos"] = tuple(st["pos"])
            d = MOVES[st["move"]]
            pos = (pos[0] + d[0], pos[1] + d[1])
            path.append(pos)
        max_steps = 0
    else:
        c = client()
    for step in range(max_steps):
        legal = {m: (pos[0] + d[0], pos[1] + d[1]) for m, d in MOVES.items()}
        legal = {m: p for m, p in legal.items() if grid[p[0]][p[1]] != "#"}
        view = [
            "".join(
                "@" if (i, j) == pos else ("·" if (i, j) in visited and ch == "." else ch)
                for j, ch in enumerate(r)
            )
            for i, r in enumerate(grid)
        ]
        state = {
            "map": view,
            "legend": "# wall, . open, · already visited, @ you, G goal",
            "you": {"row": pos[0], "col": pos[1]},
            "goal": {"row": goal[0], "col": goal[1]},
            "legal_moves": list(legal),
            "rule": "Reach G in as few moves as possible. Prefer unvisited cells. Never walk into walls.",
        }
        q = Choice(
            instructions="Which move brings you closer to G?",
            criteria={m: f"Move {m} to row {p[0]}, col {p[1]}" for m, p in legal.items()},
        )
        r, ms = timed(c, state, {"move": q})
        a = r.answers["move"]
        move = a.choice
        steps.append(
            {
                "step": step,
                "pos": pos,
                "move": move,
                "probs": a.probabilities,
                "confidence": a.confidence,
                "latency_ms": ms,
            }
        )
        print(f"step {step:2d} at {pos} -> {move:5s} conf={a.confidence:.2f} {ms:.0f} ms")
        pos = legal[move]
        visited.add(pos)
        path.append(pos)
        if pos == goal:
            print("reached goal in", step + 1, "moves")
            break
    if not REPLOT:
        dump("maze", steps)

    # render GIF
    from PIL import Image

    frames = []
    H, W = len(MAZE), len(MAZE[0])
    for k, st in enumerate(steps + [None]):
        fig, (ax, axp) = plt.subplots(1, 2, figsize=(10.5, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
        img = np.zeros((H, W, 3))
        for i in range(H):
            for j in range(W):
                img[i, j] = (0.09, 0.11, 0.14) if MAZE[i][j] == "#" else (0.16, 0.18, 0.22)
        for p in path[: k + 1]:
            img[p] = (0.22, 0.55, 0.75)
        img[goal] = (0.29, 0.87, 0.5)
        cur = path[min(k, len(path) - 1)]
        img[cur] = (0.91, 0.47, 0.98)
        ax.imshow(img, interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"Jev plays a maze · step {min(k, len(steps))}/{len(steps)}", color=FG)
        ax.text(
            0.0,
            -0.06,
            "■ path   ■ Jev   ■ goal    one Choice(up/down/left/right) per step, ASCII map as state",
            transform=ax.transAxes,
            color=DIM,
            fontsize=8,
        )
        for spine in ax.spines.values():
            spine.set_visible(False)
        axp.set_facecolor(PANEL)
        if st is not None:
            labels = list(st["probs"])
            vals = [st["probs"][m] for m in labels]
            colors = [MAGENTA if m == st["move"] else "#484f58" for m in labels]
            axp.barh(labels, vals, color=colors)
            axp.set_xlim(0, 1)
            axp.set_title(
                f"→ {st['move']}   confidence {st['confidence']:.2f}   {st['latency_ms']:.0f} ms",
                color=FG,
                fontsize=11,
            )
            for y, v in enumerate(vals):
                axp.text(min(v + 0.02, 0.9), y, f"{v:.2f}", va="center", color=FG, fontsize=10)
        else:
            axp.text(
                0.5,
                0.5,
                f"GOAL\n{len(steps)} moves\n{sum(s['latency_ms'] for s in steps) / 1000:.1f} s total",
                ha="center",
                va="center",
                fontsize=20,
                color=GREEN,
                transform=axp.transAxes,
            )
            axp.set_xticks([])
            axp.set_yticks([])
        axp.tick_params(colors=DIM)
        axp.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        fig.canvas.draw()
        frames.append(
            Image.frombuffer(
                "RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba(), "raw", "RGBA", 0, 1
            ).convert("P", palette=Image.ADAPTIVE)
        )
        plt.close(fig)
    durations = [450] * (len(frames) - 1) + [3000]
    frames[0].save(OUT / "maze.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0)
    print("maze ->", OUT / "maze.gif")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = {"pelican": exp_pelican, "surface": exp_surface, "latency": exp_latency, "maze": exp_maze}
    for name, fn in todo.items():
        if which in ("all", name):
            print(f"\n=== {name} ===")
            fn()
