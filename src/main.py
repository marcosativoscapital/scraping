"""CLI principal."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

from .output.csv_writer import write_apollo_csv, write_leads_csv
from .pipeline import run_pipeline

console = Console()


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False)],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="solve-scraper",
        description="Motor de prospecção B2B da Solvefy (KR2 CPaaS)",
    )
    parser.add_argument(
        "--vertical",
        choices=["betting", "pagamentos", "cobranca", "saas_b2b", "all"],
        default="all",
        help="Vertical a processar",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limite de empresas")
    parser.add_argument(
        "--enrich-email",
        action="store_true",
        help="Enriquece e-mails via Hunter (requer HUNTER_API_KEY)",
    )
    parser.add_argument(
        "--output",
        choices=["csv", "apollo", "both"],
        default="csv",
        help="Formato de saída",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/output"),
        help="Pasta de saída",
    )
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args(argv)
    load_dotenv()
    setup_logging(args.log_level)

    console.rule("[bold cyan]Solve Scraper — KR2 CPaaS[/bold cyan]")
    console.print(f"Vertical: [yellow]{args.vertical}[/yellow]")
    console.print(f"Limite: [yellow]{args.limit or 'sem limite'}[/yellow]")
    console.print(f"Enrich e-mail: [yellow]{args.enrich_email}[/yellow]\n")

    try:
        leads = run_pipeline(
            vertical=args.vertical,
            limit=args.limit,
            enrich_email=args.enrich_email,
            output_dir=args.output_dir,
        )
    except KeyboardInterrupt:
        console.print("\n[red]Interrompido pelo usuário[/red]")
        return 130
    except Exception as e:
        console.print(f"\n[red]Erro:[/red] {e}")
        logging.exception("Falha no pipeline")
        return 1

    if not leads:
        console.print("[yellow]Nenhum lead processado.[/yellow]")
        return 0

    # Outputs
    if args.output in ("csv", "both"):
        path = write_leads_csv(leads, args.output_dir, vertical_tag=args.vertical)
        console.print(f"\n[bold green]✓ CSV:[/bold green] {path}")

    if args.output in ("apollo", "both"):
        path = write_apollo_csv(leads, args.output_dir)
        console.print(f"[bold green]✓ Apollo CSV:[/bold green] {path}")

    # Resumo
    console.print(f"\n[bold]Total de leads:[/bold] {len(leads)}")
    by_vertical: dict[str, int] = {}
    for lead in leads:
        v = lead.get("vertical", "unknown")
        by_vertical[v] = by_vertical.get(v, 0) + 1
    for v, n in by_vertical.items():
        console.print(f"  • {v}: {n}")

    high_score = sum(1 for l in leads if (l.get("score_icp") or 0) >= 70)
    console.print(f"\n[bold]Score ≥ 70:[/bold] {high_score} leads quentes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
