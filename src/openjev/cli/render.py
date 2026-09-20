"""Rich rendering for decisions: probability bars, confidence, latency."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from openjev.core.primitives import (
    Answer,
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
    SystemOneResponse,
)

BAR_WIDTH = 24


def bar(p: float, width: int = BAR_WIDTH, color: str = "cyan") -> Text:
    filled = int(round(p * width))
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="grey37")
    t.append(f" {p:5.1%}", style="bold" if p >= 0.5 else "dim")
    return t


def render_answer(qid: str, answer: Answer) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", style="bold white", no_wrap=True)
    table.add_column()

    if isinstance(answer, ChoiceAnswer):
        title = f"[bold magenta]choice[/] {qid}"
        for opt, p in sorted(answer.probabilities.items(), key=lambda kv: -kv[1]):
            marker = "▸ " if opt == answer.choice else "  "
            table.add_row(f"{marker}{opt}", bar(p, color="magenta" if opt == answer.choice else "grey62"))
        footer = f"→ [bold]{answer.choice}[/]  confidence [bold]{answer.confidence:.2f}[/]"
    elif isinstance(answer, ScoreAnswer):
        title = f"[bold yellow]score[/] {qid}"
        for lvl, p in answer.probabilities.items():
            table.add_row(f"{lvl} · {answer.legend[lvl]}", bar(p, color="yellow"))
        footer = f"→ score [bold]{answer.score:.2f}[/]  confidence [bold]{answer.confidence:.2f}[/]"
    elif isinstance(answer, NoulAnswer):
        title = f"[bold green]noul[/] {qid}"
        table.add_row("true", bar(answer.noul, color="green"))
        table.add_row("false", bar(1 - answer.noul, color="red"))
        verdict = "TRUE" if answer.noul >= 0.5 else "FALSE"
        footer = f"→ [bold]{verdict}[/]  P(true) [bold]{answer.noul:.2f}[/]"
    else:  # pragma: no cover
        raise TypeError(type(answer))

    return Panel(
        Group(table, Text.from_markup(footer)), title=title, title_align="left", border_style="grey50"
    )


def render_response(console: Console, resp: SystemOneResponse) -> None:
    for qid, ans in resp.answers.items():
        console.print(render_answer(qid, ans))
    meta = Text()
    meta.append(f"{len(resp.answers)} decisions", style="bold")
    meta.append("  ·  ")
    meta.append(f"{resp.latency_ms:.1f} ms", style="bold cyan")
    meta.append("  ·  ")
    meta.append(f"{resp.usage.input_tokens} in / {resp.usage.output_tokens} out tokens", style="dim")
    meta.append("  ·  ")
    meta.append(resp.model, style="dim")
    console.print(meta)


def render_questions_table(questions: dict[str, object]) -> Table:
    t = Table(title="Pending questions", show_lines=False, header_style="bold")
    t.add_column("id")
    t.add_column("type")
    t.add_column("instructions")
    t.add_column("options / legend")
    for qid, q in questions.items():
        qtype = getattr(q, "type", "?")
        extra = ""
        if qtype == "choice":
            extra = ", ".join(q.option_keys())
        elif qtype == "score":
            extra = " < ".join(f"{k}:{v}" for k, v in q.legend.items())
        t.add_row(qid, qtype, q.instructions, extra)
    return t
