"""OpenJev REPL: a Claude Code style terminal for System One decisions.

Commands
  /state <text|json>          set the state (or paste JSON)
  /choice <id> "<q>" a,b,c    add a Choice question
  /score  <id> "<q>" 0:low,1:mid,2:high   add a Score question
  /noul   <id> "<q>"          add a Noul question
  /ask                        run all pending questions in one request
  /questions                  list pending questions
  /clear                      clear questions
  /backend <mock|hf> [model]  switch backend
  /help                       show help
  /exit
Free text (no leading slash) is treated as a Noul question against the current state.
"""

from __future__ import annotations

import json
import shlex
import sys

from rich.console import Console
from rich.panel import Panel

from openjev import __version__
from openjev.backends import Backend, get_backend
from openjev.cli.render import render_questions_table, render_response
from openjev.core.primitives import Choice, Noul, Question, Score, SystemOneRequest

BANNER = r"""
  ____                     __
 / __ \____  ___  ____    / /___ _   __
/ / / / __ \/ _ \/ __ \  / / __ \ | / /
/ /_/ / /_/ /  __/ / / / / / /_/ / |/ /
\____/ .___/\___/_/ /_/_/ /\___/|___/
    /_/            /___/
"""


class Repl:
    def __init__(self, backend: Backend, console: Console | None = None):
        self.console = console or Console()
        self.backend = backend
        self.state: object = ""
        self.questions: dict[str, Question] = {}

    # ------------------------------------------------------------------ commands
    def cmd_state(self, arg: str) -> None:
        arg = arg.strip()
        try:
            self.state = json.loads(arg)
            kind = "json"
        except json.JSONDecodeError:
            self.state = arg
            kind = "text"
        self.console.print(f"[dim]state set ({kind}, {len(arg)} chars)[/]")

    def cmd_choice(self, arg: str) -> None:
        parts = shlex.split(arg)
        if len(parts) < 3:
            self.console.print('[red]usage: /choice <id> "<question>" opt1,opt2,...[/]')
            return
        qid, q, opts = parts[0], parts[1], parts[2]
        self.questions[qid] = Choice(instructions=q, options=[o.strip() for o in opts.split(",")])
        self.console.print(f"[dim]+ choice {qid}[/]")

    def cmd_score(self, arg: str) -> None:
        parts = shlex.split(arg)
        if len(parts) < 3:
            self.console.print('[red]usage: /score <id> "<question>" 0:low,1:mid,2:high[/]')
            return
        qid, q, legend_s = parts[0], parts[1], parts[2]
        legend = dict(kv.split(":", 1) for kv in legend_s.split(","))
        self.questions[qid] = Score(instructions=q, legend=legend)
        self.console.print(f"[dim]+ score {qid}[/]")

    def cmd_noul(self, arg: str) -> None:
        parts = shlex.split(arg)
        if len(parts) < 2:
            self.console.print('[red]usage: /noul <id> "<question>"[/]')
            return
        self.questions[parts[0]] = Noul(instructions=parts[1])
        self.console.print(f"[dim]+ noul {parts[0]}[/]")

    def cmd_ask(self, _: str = "") -> None:
        if not self.questions:
            self.console.print("[yellow]no pending questions. add some with /choice /score /noul[/]")
            return
        req = SystemOneRequest(state=self.state, questions=self.questions)
        with self.console.status("[cyan]deciding…", spinner="dots"):
            resp = self.backend.decide(req)
        render_response(self.console, resp)

    def cmd_backend(self, arg: str) -> None:
        parts = arg.split()
        if not parts:
            self.console.print(f"[dim]current backend: {self.backend.name}[/]")
            return
        kwargs = {"model_id": parts[1]} if len(parts) > 1 else {}
        try:
            self.backend = get_backend(parts[0], **kwargs)
            with self.console.status("[cyan]loading model…"):
                self.backend.load()
            self.console.print(f"[green]backend → {self.backend.name}[/]")
        except Exception as e:  # noqa: BLE001
            self.console.print(f"[red]{e}[/]")

    def cmd_help(self, _: str = "") -> None:
        self.console.print(Panel(__doc__.strip(), title="help", border_style="grey50"))

    # ------------------------------------------------------------------ loop
    def dispatch(self, line: str) -> bool:
        line = line.strip()
        if not line:
            return True
        if not line.startswith("/"):
            self.questions["q"] = Noul(instructions=line)
            self.cmd_ask()
            self.questions.pop("q", None)
            return True
        cmd, _, arg = line[1:].partition(" ")
        table = {
            "state": self.cmd_state,
            "choice": self.cmd_choice,
            "score": self.cmd_score,
            "noul": self.cmd_noul,
            "ask": self.cmd_ask,
            "backend": self.cmd_backend,
            "help": self.cmd_help,
            "questions": lambda _: self.console.print(render_questions_table(self.questions)),
            "clear": lambda _: (self.questions.clear(), self.console.print("[dim]cleared[/]")),
        }
        if cmd in ("exit", "quit", "q"):
            return False
        fn = table.get(cmd)
        if fn is None:
            self.console.print(f"[red]unknown command /{cmd}. try /help[/]")
        else:
            fn(arg)
        return True

    def run(self) -> None:
        self.console.print(f"[bold cyan]{BANNER}[/]")
        self.console.print(
            f"[dim]OpenJev v{__version__} · backend {self.backend.name} · /help for commands[/]\n"
        )
        try:
            from prompt_toolkit import PromptSession

            session = PromptSession()
            read = lambda: session.prompt("❯ ")
        except ImportError:  # pragma: no cover
            read = lambda: input("❯ ")
        while True:
            try:
                line = read()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]bye[/]")
                return
            if not self.dispatch(line):
                self.console.print("[dim]bye[/]")
                return


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="openjev", description="OpenJev REPL")
    p.add_argument("--backend", default="mock", help="mock | hf")
    p.add_argument("--model", default=None, help="model id for hf backend")
    p.add_argument("--file", default=None, help="run a JSON request file (state + questions) and exit")
    p.add_argument("--version", action="version", version=f"openjev {__version__}")
    args = p.parse_args(argv)
    kwargs = {"model_id": args.model} if args.model else {}
    backend = get_backend(args.backend, **kwargs)
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            req = SystemOneRequest.model_validate_json(fh.read())
        console = Console()
        with console.status("[cyan]deciding…", spinner="dots"):
            backend.load()
            resp = backend.decide(req)
        render_response(console, resp)
        return 0
    Repl(backend).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
