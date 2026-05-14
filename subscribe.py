#!/usr/bin/env python3
"""
subscribe.py — Newsletter Automation CLI

Rich-powered dashboard showing live progress, active workers,
status counts per newsletter, and a rolling event stream.
"""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List

import click
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from core.models import NewsletterResult, Status
from core.orchestrator import Orchestrator
from utils.file_loader import load_emails, load_newsletters, load_proxies

console = Console()

_STATUS_STYLE = {
    Status.SUCCESS: ("SUCCESS", "bold green"),
    Status.FAILED:  ("FAILED",  "bold red"),
    Status.ERROR:   ("ERROR",   "bold yellow"),
    Status.CAPTCHA: ("CAPTCHA", "bold magenta"),
}


# ---------------------------------------------------------------------------
# Dashboard builder
# ---------------------------------------------------------------------------

def _elapsed_str(since: float) -> str:
    secs = int(time.time() - since)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _build_header(
    start_time: float,
    emails_done: int,
    total_emails: int,
    concurrency: int,
) -> Panel:
    pct = int(emails_done / total_emails * 100) if total_emails else 0
    bar_filled = int(pct / 5)
    bar = "[" + "█" * bar_filled + "░" * (20 - bar_filled) + "]"
    t = Text(justify="center")
    t.append("  ⚡ NEWSLETTER AUTOMATION  ", style="bold white on dark_blue")
    t.append("   ")
    t.append(_elapsed_str(start_time), style="bold cyan")
    t.append("   ")
    t.append(f"{bar} {pct}%  {emails_done}/{total_emails} emails", style="green")
    t.append(f"   workers={concurrency}", style="dim")
    return Panel(Align.center(t), style="dark_blue", height=3)


def _build_stats_table(snapshot: dict, newsletters: List[str]) -> Panel:
    counts = snapshot["counts"]
    tbl = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        expand=True,
        show_edge=True,
        padding=(0, 1),
    )
    tbl.add_column("Newsletter", style="bold white", min_width=16)
    tbl.add_column("✓ SUCCESS", style="green",   justify="center", min_width=9)
    tbl.add_column("✗ FAILED",  style="red",     justify="center", min_width=9)
    tbl.add_column("! ERROR",   style="yellow",  justify="center", min_width=8)
    tbl.add_column("⊘ CAPTCHA", style="magenta", justify="center", min_width=9)
    tbl.add_column("TOTAL",     style="cyan",    justify="center", min_width=7)

    for nl in newsletters:
        c = counts.get(nl, {})
        s = c.get("SUCCESS", 0)
        f = c.get("FAILED", 0)
        e = c.get("ERROR", 0)
        ca = c.get("CAPTCHA", 0)
        total = s + f + e + ca
        tbl.add_row(
            nl,
            str(s)  if s  else "[dim]—[/]",
            str(f)  if f  else "[dim]—[/]",
            str(e)  if e  else "[dim]—[/]",
            str(ca) if ca else "[dim]—[/]",
            f"[bold]{total}[/]" if total else "[dim]0[/]",
        )

    return Panel(tbl, title="[bold cyan]Status Counts[/]", border_style="cyan")


def _build_active_table(snapshot: dict) -> Panel:
    active = snapshot["active"]
    tbl = Table(
        box=box.SIMPLE_HEAD,
        header_style="bold yellow",
        expand=True,
        padding=(0, 1),
    )
    tbl.add_column("Email", style="white", min_width=28)
    tbl.add_column("Newsletter", style="bold")
    tbl.add_column("Step", style="dim")
    tbl.add_column("Age", justify="right", style="dim")

    rows = list(active.items())[:18]
    for email, info in rows:
        since = info.get("since", datetime.now())
        age = int((datetime.now() - since).total_seconds())
        tbl.add_row(
            email[:32],
            info.get("newsletter", "—"),
            info.get("step", "—"),
            f"{age}s",
        )

    if not rows:
        tbl.add_row("[dim]No active workers yet[/]", "", "", "")

    return Panel(
        tbl,
        title=f"[bold yellow]Active Workers[/] [dim]({len(active)})[/]",
        border_style="yellow",
    )


def _build_events_panel(snapshot: dict) -> Panel:
    events = snapshot["events"]
    t = Text()
    for ev in events[-14:]:
        ts = ev["ts"].strftime("%H:%M:%S")
        st: Status = ev["status"]
        label, style = _STATUS_STYLE[st]
        t.append(f"  {ts} ", style="dim")
        t.append(f"[{ev['newsletter']}]", style="bold white")
        t.append(f"  {ev['email'][:26]}", style="white")
        t.append(f"  →  ", style="dim")
        t.append(f"{label}\n", style=style)

    if not events:
        t.append("  Waiting for first results…", style="dim italic")

    return Panel(t, title="[bold]Recent Events[/]", border_style="dim white")


def _build_dashboard(
    orchestrator: Orchestrator,
    start_time: float,
    emails_done: int,
    total_emails: int,
    newsletters: List[str],
    concurrency: int,
) -> Layout:
    snapshot = orchestrator.status_manager.get_snapshot()

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="events", size=16),
    )
    layout["body"].split_row(
        Layout(name="stats", ratio=2),
        Layout(name="active", ratio=3),
    )

    layout["header"].update(
        _build_header(start_time, emails_done, total_emails, concurrency)
    )
    layout["stats"].update(_build_stats_table(snapshot, newsletters))
    layout["active"].update(_build_active_table(snapshot))
    layout["events"].update(_build_events_panel(snapshot))

    return layout


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--emails",       default="emails.txt",       show_default=True, help="Path to emails file")
@click.option("--proxies",      default="proxies.txt",      show_default=True, help="Path to proxies file")
@click.option("--newsletters",  default="newsletters.txt",  show_default=True, help="Path to newsletters file")
@click.option("--concurrency",  default=10, type=int,       show_default=True, help="Max concurrent email workers")
@click.option("--headless/--no-headless", default=False,    show_default=True, help="Run browsers headless")
@click.option("--profiles-dir", default="profiles",         show_default=True, help="Persistent browser profiles dir")
@click.option("--output-dir",   default="output",           show_default=True, help="Output directory")
def main(
    emails: str,
    proxies: str,
    newsletters: str,
    concurrency: int,
    headless: bool,
    profiles_dir: str,
    output_dir: str,
) -> None:
    """Subscribe emails to newsletters using stealth browser automation."""

    # -- Splash --
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Newsletter Automation[/bold cyan]\n"
            "[dim]Camoufox · Playwright · Rich CLI[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    console.print()

    # -- Load inputs --
    email_list      = load_emails(emails)
    proxy_list      = load_proxies(proxies)
    newsletter_list = load_newsletters(newsletters)

    if not email_list:
        console.print(f"[bold red]No emails found in {emails!r}[/]")
        sys.exit(1)
    if not newsletter_list:
        console.print(f"[bold red]No newsletters found in {newsletters!r}[/]")
        sys.exit(1)

    console.print(f"  [green]Emails:[/]       {len(email_list)}")
    console.print(f"  [green]Proxies:[/]      {len(proxy_list)}")
    console.print(f"  [green]Newsletters:[/]  {', '.join(newsletter_list)}")
    console.print(f"  [green]Concurrency:[/]  {concurrency}")
    console.print(f"  [green]Headless:[/]     {headless}")
    console.print()

    orchestrator = Orchestrator(
        emails=email_list,
        proxies=proxy_list,
        newsletters=newsletter_list,
        concurrency=concurrency,
        profiles_dir=Path(profiles_dir),
        output_dir=Path(output_dir),
        headless=headless,
    )

    start_time = time.time()
    total_emails = len(email_list)
    all_results: List[NewsletterResult] = []
    finished = threading.Event()

    def _worker():
        nonlocal all_results
        all_results = orchestrator.run()
        finished.set()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    # -- Live dashboard --
    with Live(console=console, refresh_per_second=2, screen=True) as live:
        while not finished.is_set():
            snap = orchestrator.status_manager.get_snapshot()
            emails_done = snap["emails_completed"]

            live.update(
                _build_dashboard(
                    orchestrator,
                    start_time,
                    emails_done,
                    total_emails,
                    newsletter_list,
                    concurrency,
                )
            )
            time.sleep(0.5)

        # Final frame
        live.update(
            _build_dashboard(
                orchestrator,
                start_time,
                total_emails,
                total_emails,
                newsletter_list,
                concurrency,
            )
        )
        time.sleep(1.5)

    # -- Summary --
    _print_summary(all_results, newsletter_list, start_time)


def _print_summary(
    results: List[NewsletterResult],
    newsletters: List[str],
    start_time: float,
) -> None:
    console.print()
    console.print(Rule("[bold cyan]Run Summary[/]"))
    console.print()

    total = len(results)
    by_status = {s: 0 for s in Status}
    for r in results:
        by_status[r.status] += 1

    summary = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    summary.add_column("Status",  style="bold")
    summary.add_column("Count",   justify="right")
    summary.add_column("% of Total", justify="right")

    order = [Status.SUCCESS, Status.FAILED, Status.CAPTCHA, Status.ERROR]
    styles = ["green", "red", "magenta", "yellow"]
    for st, sty in zip(order, styles):
        cnt = by_status[st]
        pct = f"{cnt/total*100:.1f}%" if total else "—"
        summary.add_row(st.value, str(cnt), pct, style=sty if cnt else "dim")

    summary.add_row("TOTAL", str(total), "100%", style="bold cyan")
    console.print(summary)

    elapsed = int(time.time() - start_time)
    h, rem = divmod(elapsed, 3600)
    m, s   = divmod(rem, 60)
    console.print()
    console.print(f"  [dim]Elapsed:[/] {h:02d}:{m:02d}:{s:02d}")
    console.print(f"  [dim]Output:[/]  output/")
    console.print()


if __name__ == "__main__":
    main()
