"""CLI for GTM Semantic Crawler"""
import click
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import init_db, get_opportunities, get_stats, get_category_trends

console = Console()

@click.group()
def cli():
    """GTM Semantic Crawler - Find PMF opportunities"""
    init_db()

@cli.command()
@click.option('--min-fit', default=5, help='Minimum fit score (0-10)')
@click.option('--min-urgency', default=0, help='Minimum urgency score (0-10)')
@click.option('--use-case', '-u', help='Filter by use case category')
@click.option('--days', '-d', default=7, help='Number of days to look back')
@click.option('--limit', '-n', default=20, help='Maximum results')
@click.option('--json-output', is_flag=True, help='Output as JSON')
def query(min_fit, min_urgency, use_case, days, limit, json_output):
    """Query opportunities with filters"""
    results = get_opportunities(
        min_fit=min_fit,
        min_urgency=min_urgency,
        use_case=use_case,
        days=days,
        limit=limit,
    )
    
    if json_output:
        # Convert datetime objects to strings
        for r in results:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        click.echo(json.dumps(results, indent=2))
        return
    
    if not results:
        console.print("[yellow]No opportunities found matching criteria[/yellow]")
        return
    
    table = Table(title=f"Top Opportunities (fit>={min_fit}, last {days} days)")
    table.add_column("Fit", justify="center", style="green")
    table.add_column("Urg", justify="center", style="yellow")
    table.add_column("Use Case", style="cyan")
    table.add_column("Source", style="blue")
    table.add_column("Summary", max_width=50)
    table.add_column("URL", max_width=40)
    
    for r in results:
        table.add_row(
            str(r.get('fit_score', 0)),
            str(r.get('urgency_score', 0)),
            r.get('use_case', 'other')[:15],
            r.get('source', 'unknown'),
            (r.get('problem_summary') or '')[:50],
            (r.get('url') or '')[:40],
        )
    
    console.print(table)

@cli.command()
def stats():
    """Show crawler statistics"""
    s = get_stats()
    
    panel_content = f"""
[bold]Total Posts:[/bold] {s.get('total_posts', 0)}
[bold]Analyzed:[/bold] {s.get('analyzed_posts', 0)}
[bold]High Fit (7+):[/bold] {s.get('high_fit_opportunities', 0)}

[bold]By Source:[/bold]
"""
    for source, count in s.get('by_source', {}).items():
        panel_content += f"  • {source}: {count}\n"
    
    panel_content += "\n[bold]By Use Case:[/bold]\n"
    for use_case, count in list(s.get('by_use_case', {}).items())[:10]:
        panel_content += f"  • {use_case}: {count}\n"
    
    console.print(Panel(panel_content, title="GTM Semantic Crawler Stats"))

@cli.command()
@click.option('--days', '-d', default=30, help='Days to analyze')
def trends(days):
    """Show category trends over time"""
    data = get_category_trends(days=days)
    
    if not data:
        console.print("[yellow]No trend data available[/yellow]")
        return
    
    # Aggregate by use case
    by_category = {}
    for row in data:
        cat = row['use_case']
        if cat not in by_category:
            by_category[cat] = {'count': 0, 'avg_fit': 0, 'dates': []}
        by_category[cat]['count'] += row['count']
        by_category[cat]['dates'].append(row['date'])
    
    table = Table(title=f"Category Trends (last {days} days)")
    table.add_column("Use Case", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Trend", style="green")
    
    sorted_cats = sorted(by_category.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for cat, info in sorted_cats[:15]:
        # Simple trend indicator
        trend = "→ stable"  # Could calculate actual trend
        table.add_row(cat, str(info['count']), trend)
    
    console.print(table)

@cli.command()
@click.argument('use_case')
@click.option('--days', '-d', default=7, help='Days to look back')
@click.option('--limit', '-n', default=10, help='Maximum results')
def export(use_case, days, limit):
    """Export opportunities for outreach"""
    results = get_opportunities(
        min_fit=6,
        use_case=use_case,
        days=days,
        limit=limit,
    )
    
    for r in results:
        console.print(f"\n[bold cyan]═══ Opportunity ═══[/bold cyan]")
        console.print(f"[bold]Fit:[/bold] {r.get('fit_score')}/10 | [bold]Urgency:[/bold] {r.get('urgency_score')}/10")
        console.print(f"[bold]Problem:[/bold] {r.get('problem_summary')}")
        console.print(f"[bold]URL:[/bold] {r.get('url')}")
        console.print(f"[dim]Reasoning: {r.get('reasoning')}[/dim]")

@cli.command()
@click.option('--days', '-d', default=1, help='Days to crawl back')
@click.option('--analyze/--no-analyze', default=True, help='Run analysis after crawl')
@click.option('--batch-size', '-b', default=50, help='Analysis batch size')
def crawl(days, analyze, batch_size):
    """Run crawlers and optionally analyze"""
    from crawlers import crawl_hn, crawl_reddit
    from analysis import run_analysis
    
    console.print("[bold]Starting HN crawl...[/bold]")
    hn_stats = crawl_hn(days_back=days)
    console.print(f"HN: {hn_stats}")
    
    console.print("[bold]Starting Reddit crawl...[/bold]")
    reddit_stats = crawl_reddit(days_back=days)
    console.print(f"Reddit: {reddit_stats}")
    
    if analyze:
        console.print("[bold]Running AI analysis...[/bold]")
        analysis_stats = run_analysis(batch_size=batch_size)
        console.print(f"Analysis: {analysis_stats}")

if __name__ == "__main__":
    cli()
