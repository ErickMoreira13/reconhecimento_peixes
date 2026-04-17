from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table


# uma "camada" visual que centraliza print bonito pra nao ficar espalhando rich.Console
# se um dia quiser tirar o rich (ou trocar por outra lib) mexe so aqui

_console = Console()


def info(msg: str):
    _console.print(f"[cyan]{msg}[/]")


def ok(msg: str):
    _console.print(f"[green]{msg}[/]")


def aviso(msg: str):
    _console.print(f"[yellow]{msg}[/]")


def erro(msg: str):
    _console.print(f"[red]{msg}[/]")


def titulo(msg: str):
    _console.rule(f"[bold cyan]{msg}[/]")


@contextmanager
def progresso(total: int, descricao: str):
    # progress bar padrao, com tempo decorrido e estimativa de fim
    cols = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    ]
    with Progress(*cols, console=_console, transient=False) as prog:
        task = prog.add_task(descricao, total=total)
        yield prog, task


def tabela_status(rows: list[tuple[str, int]]):
    # tabelinha de resumo no comando status
    t = Table(title="pipeline status", show_header=True)
    t.add_column("etapa", style="cyan")
    t.add_column("videos", style="magenta", justify="right")

    ordem = ["pendente", "baixado", "transcrito", "extraido", "verificado", "falhou"]
    mapa = dict(rows)

    for etapa in ordem:
        if etapa in mapa:
            t.add_row(etapa, str(mapa[etapa]))
    # se aparecer status que nao ta na ordem acima, joga no final
    for st, n in rows:
        if st not in ordem:
            t.add_row(st, str(n))

    _console.print(t)


def console():
    return _console
