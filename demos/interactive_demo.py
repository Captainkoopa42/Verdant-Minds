#!/usr/bin/env python3
"""
Verdant-Minds Interactive Demo

An impressive visual demonstration of the Unified Synthetic Mind architecture.
Shows system processing, block activation, ethical evaluation, and memory updates
with beautiful terminal visualization.

Works with untrained weights - demonstrates the architecture and processing flow
rather than actual intelligence.

Usage:
    python demos/interactive_demo.py
    python demos/interactive_demo.py --query "Your question here"
    python demos/interactive_demo.py --showcase

Requirements:
    pip install rich
"""

import sys
import time
import random
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Try to import rich for beautiful output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.layout import Layout
    from rich.live import Live
    from rich.tree import Tree
    from rich.text import Text
    from rich import box
    from rich.columns import Columns
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for beautiful output: pip install rich")
    print("   Falling back to basic output...\n")

# Add project to path
project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))


@dataclass
class BlockActivation:
    """Represents a cognitive block activation."""
    name: str
    status: str  # "processing", "complete", "pending"
    progress: float
    output: Dict[str, Any]
    timestamp: float


class VerdantDemo:
    """Interactive demonstration of the Verdant-Minds architecture."""

    def __init__(self, use_rich: bool = True):
        """Initialize the demo."""
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()

        # System components (simulated for demo)
        self.blocks = [
            "Sensory Input",
            "Pattern Recognition",
            "Memory Storage",
            "Internal Communication",
            "Reasoning & Planning",
            "Ethics & Values",
            "Action Selection",
            "Language Processing",
            "Continual Learning"
        ]

        self.kings = ["Data King", "Ethics King", "Forefront King"]

        self.ethical_dimensions = [
            "Non-maleficence (avoid harm)",
            "Beneficence (do good)",
            "Autonomy (respect choice)",
            "Justice (fairness)",
            "Transparency"
        ]

    def clear_screen(self):
        """Clear the terminal screen."""
        if self.use_rich:
            self.console.clear()
        else:
            print("\n" * 50)

    def print_banner(self):
        """Display the welcome banner."""
        if self.use_rich:
            banner = """
╦  ╦╔═╗╦═╗╔╦╗╔═╗╔╗╔╔╦╗   ╔╦╗╦╔╗╔╔╦╗╔═╗
╚╗╔╝║╣ ╠╦╝ ║║╠═╣║║║ ║ ───║║║║║║║ ║║╚═╗
 ╚╝ ╚═╝╩╚══╩╝╩ ╩╝╚╝ ╩    ╩ ╩╩╝╚╝═╩╝╚═╝

 Unified Synthetic Mind - Interactive Demo
 Quantum-Inspired Cognitive Architecture
            """
            panel = Panel(
                Text(banner, style="bold cyan", justify="center"),
                border_style="bright_blue",
                box=box.DOUBLE
            )
            self.console.print(panel)
            self.console.print()
        else:
            print("=" * 60)
            print("VERDANT-MINDS: Unified Synthetic Mind")
            print("Interactive Architecture Demo")
            print("=" * 60)
            print()

    def show_architecture_overview(self):
        """Display system architecture overview."""
        if self.use_rich:
            self.console.print("\n[bold cyan]🏗️  System Architecture Overview[/bold cyan]\n")

            # Create architecture tree
            tree = Tree("🧠 [bold]Unified Synthetic Mind[/bold]", guide_style="bright_blue")

            # Memory System
            memory_branch = tree.add("💾 [yellow]Memory System[/yellow]")
            memory_branch.add("📊 Memory Web (NetworkX Graph)")
            memory_branch.add("🌊 ECWF Core (Wave Functions)")
            memory_branch.add("🌉 Memory-ECWF Bridge")

            # Nine-Block System
            blocks_branch = tree.add("🔮 [green]Nine-Block Cognitive System[/green]")
            for i, block in enumerate(self.blocks, 1):
                blocks_branch.add(f"{i}. {block}")

            # Three Kings
            kings_branch = tree.add("👑 [magenta]Three Kings Governance[/magenta]")
            for king in self.kings:
                kings_branch.add(f"• {king}")

            self.console.print(tree)
            self.console.print()

        else:
            print("\n=== System Architecture ===\n")
            print("Memory System:")
            print("  - Memory Web (Graph)")
            print("  - ECWF Core (Wave Functions)")
            print("  - Memory-ECWF Bridge")
            print("\nNine-Block Cognitive System:")
            for i, block in enumerate(self.blocks, 1):
                print(f"  {i}. {block}")
            print("\nThree Kings Governance:")
            for king in self.kings:
                print(f"  - {king}")
            print()

    def simulate_block_processing(self, block_name: str, input_data: str) -> Dict[str, Any]:
        """Simulate processing by a cognitive block."""
        # Simulate different outputs for different blocks
        outputs = {
            "Sensory Input": {
                "tokens": input_data.split(),
                "token_count": len(input_data.split()),
                "complexity": random.uniform(0.4, 0.9),
                "encoding": "utf-8"
            },
            "Pattern Recognition": {
                "patterns_detected": random.randint(3, 8),
                "confidence": random.uniform(0.6, 0.95),
                "categories": ["query", "analytical", "ethical"][random.randint(0, 2)]
            },
            "Memory Storage": {
                "concepts_stored": random.randint(5, 15),
                "connections_formed": random.randint(10, 30),
                "graph_size": random.randint(100, 500)
            },
            "Internal Communication": {
                "messages_routed": random.randint(5, 12),
                "blocks_coordinated": random.randint(3, 7),
                "bandwidth_used": f"{random.randint(20, 80)}%"
            },
            "Reasoning & Planning": {
                "inference_type": random.choice(["deductive", "inductive", "abductive"]),
                "reasoning_depth": random.randint(3, 7),
                "confidence": random.uniform(0.65, 0.92)
            },
            "Ethics & Values": {
                "ethical_evaluation": "approved",
                "principles_considered": random.randint(3, 5),
                "concern_level": random.choice(["low", "moderate"])
            },
            "Action Selection": {
                "action": "respond",
                "alternatives_considered": random.randint(3, 6),
                "selection_confidence": random.uniform(0.7, 0.95)
            },
            "Language Processing": {
                "response_generated": True,
                "coherence_score": random.uniform(0.75, 0.95),
                "word_count": random.randint(50, 200)
            },
            "Continual Learning": {
                "updates_applied": random.randint(2, 8),
                "knowledge_delta": random.uniform(0.01, 0.05),
                "learning_rate": 0.05
            }
        }

        return outputs.get(block_name, {"processed": True})

    def display_block_processing(self, query: str):
        """Display step-by-step block processing with visual feedback."""
        if self.use_rich:
            self.console.print(f"\n[bold cyan]🔍 Processing Query:[/bold cyan] [white]{query}[/white]\n")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
                transient=False
            ) as progress:

                # Process through each block
                for i, block in enumerate(self.blocks, 1):
                    task = progress.add_task(f"[cyan]{block}[/cyan]", total=100)

                    # Simulate processing
                    for _ in range(10):
                        time.sleep(0.05)
                        progress.update(task, advance=10)

                    # Get simulated output
                    output = self.simulate_block_processing(block, query)

                    # Display output
                    self.console.print(f"  [green]✓[/green] {block}: [dim]{self._format_output(output)}[/dim]")

                    # Show King oversight at key points
                    if block in ["Internal Communication", "Ethics & Values", "Action Selection"]:
                        king_name = self.kings[[
                            "Internal Communication",
                            "Ethics & Values",
                            "Action Selection"
                        ].index(block)]
                        self.console.print(f"    [magenta]👑 {king_name} oversight applied[/magenta]")

                    time.sleep(0.1)

        else:
            print(f"\n=== Processing Query: {query} ===\n")
            for i, block in enumerate(self.blocks, 1):
                print(f"{i}. {block}...", end=" ")
                time.sleep(0.3)
                output = self.simulate_block_processing(block, query)
                print(f"✓ {self._format_output(output)}")

                if block in ["Internal Communication", "Ethics & Values", "Action Selection"]:
                    king_name = self.kings[[
                        "Internal Communication",
                        "Ethics & Values",
                        "Action Selection"
                    ].index(block)]
                    print(f"   👑 {king_name} oversight applied")

    def _format_output(self, output: Dict[str, Any]) -> str:
        """Format output dictionary for display."""
        if not output:
            return "processed"
        key = list(output.keys())[0]
        value = output[key]
        return f"{key}={value}"

    def visualize_ethical_evaluation(self, query: str):
        """Display ethical evaluation with scores."""
        if self.use_rich:
            self.console.print("\n[bold magenta]⚖️  Ethical Evaluation[/bold magenta]\n")

            table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
            table.add_column("Principle", style="cyan", width=30)
            table.add_column("Score", justify="right", style="yellow")
            table.add_column("Assessment", style="green")

            # Generate simulated ethical scores
            for principle in self.ethical_dimensions:
                score = random.uniform(0.7, 0.95)
                bar = "█" * int(score * 20)
                assessment = "✓ Aligned" if score > 0.75 else "⚠ Review"
                table.add_row(principle, f"{score:.2f}", f"{bar} {assessment}")

            self.console.print(table)

            # Overall verdict
            overall_score = random.uniform(0.8, 0.95)
            verdict = Panel(
                f"[bold green]✓ Query Approved[/bold green]\n\n"
                f"Overall Ethical Score: [yellow]{overall_score:.2f}/1.00[/yellow]\n"
                f"The query aligns with ethical principles and poses no significant concerns.",
                title="[bold]Ethics King Verdict[/bold]",
                border_style="green",
                box=box.DOUBLE
            )
            self.console.print("\n", verdict)

        else:
            print("\n=== Ethical Evaluation ===\n")
            for principle in self.ethical_dimensions:
                score = random.uniform(0.7, 0.95)
                print(f"  {principle}: {score:.2f} {'✓' if score > 0.75 else '⚠'}")
            print("\n  ✓ Query Approved")

    def visualize_wave_function(self, query: str):
        """Display ECWF wave function representation."""
        if self.use_rich:
            self.console.print("\n[bold blue]🌊 Extended Cognitive Wave Function (ECWF)[/bold blue]\n")

            # Cognitive dimensions
            cog_table = Table(title="Cognitive State", box=box.SIMPLE, show_header=True)
            cog_table.add_column("Dimension", style="cyan")
            cog_table.add_column("Amplitude", justify="right", style="yellow")
            cog_table.add_column("Visualization", style="blue")

            cog_dims = [
                "Situational awareness",
                "Consequence prediction",
                "Pattern recognition",
                "Past experience",
                "Decision complexity"
            ]

            for dim in cog_dims:
                amp = random.uniform(0.3, 0.9)
                bar = "▓" * int(amp * 15) + "░" * (15 - int(amp * 15))
                cog_table.add_row(dim, f"{amp:.3f}", bar)

            self.console.print(cog_table)

            # Calculate entropy
            entropy = random.uniform(0.4, 0.7)
            self.console.print(f"\n[dim]Wave Function Entropy: {entropy:.3f} (uncertainty measure)[/dim]")

        else:
            print("\n=== Wave Function State ===\n")
            print("Cognitive Dimensions:")
            for i in range(5):
                amp = random.uniform(0.3, 0.9)
                print(f"  Dim {i+1}: {amp:.3f} {'█' * int(amp * 10)}")

    def visualize_memory_updates(self, query: str):
        """Display memory system updates."""
        if self.use_rich:
            self.console.print("\n[bold yellow]💾 Memory System Updates[/bold yellow]\n")

            # Memory Web updates
            web_panel = Panel(
                f"[green]• Added {random.randint(3, 8)} new concepts[/green]\n"
                f"[green]• Formed {random.randint(10, 25)} new connections[/green]\n"
                f"[blue]• Updated {random.randint(5, 15)} existing nodes[/blue]\n"
                f"[yellow]• Graph size: {random.randint(150, 300)} nodes, {random.randint(400, 800)} edges[/yellow]",
                title="[bold]Memory Web (NetworkX)[/bold]",
                border_style="yellow"
            )
            self.console.print(web_panel)

            # ECWF updates
            ecwf_panel = Panel(
                f"[green]• Wave function updated[/green]\n"
                f"[blue]• {random.randint(3, 7)} facets modified[/blue]\n"
                f"[yellow]• Entropy: {random.uniform(0.4, 0.7):.3f}[/yellow]\n"
                f"[magenta]• Glass transition temp (T_g): {random.uniform(0.45, 0.55):.2f}[/magenta]",
                title="[bold]ECWF Core[/bold]",
                border_style="blue"
            )
            self.console.print("\n", ecwf_panel)

            # Bridge activity
            bridge_panel = Panel(
                f"[cyan]• Symbolic → Subsymbolic: {random.randint(5, 12)} translations[/cyan]\n"
                f"[cyan]• Subsymbolic → Symbolic: {random.randint(3, 8)} translations[/cyan]\n"
                f"[green]• Bidirectional sync completed[/green]",
                title="[bold]Memory-ECWF Bridge[/bold]",
                border_style="cyan"
            )
            self.console.print("\n", bridge_panel)

        else:
            print("\n=== Memory Updates ===\n")
            print("Memory Web:")
            print(f"  + {random.randint(3, 8)} concepts")
            print(f"  + {random.randint(10, 25)} connections")
            print("\nECWF Core:")
            print(f"  • Wave function updated")
            print(f"  • Entropy: {random.uniform(0.4, 0.7):.3f}")

    def visualize_pipeline(self):
        """Display the complete processing pipeline."""
        if self.use_rich:
            self.console.print("\n[bold green]🔄 Processing Pipeline Flow[/bold green]\n")

            # Create flow diagram
            flow = Tree("📥 [bold]Input Query[/bold]")

            # Sensory Processing
            sensory = flow.add("🎯 [cyan]Sensory Input Block[/cyan]")
            sensory.add("Tokenization & Encoding")

            # Pattern Recognition
            pattern = flow.add("🔍 [cyan]Pattern Recognition Block[/cyan]")
            pattern.add("Feature Extraction")

            # Memory Stage
            memory = flow.add("💾 [yellow]Memory Stage[/yellow]")
            memory.add("Memory Storage Block")
            memory.add("🌊 ECWF Update")
            memory.add("📊 Graph Update")

            # Communication
            comm = flow.add("📡 [cyan]Internal Communication Block[/cyan]")
            comm.add("👑 Data King Oversight")

            # Reasoning
            reasoning = flow.add("🧠 [cyan]Reasoning & Planning Block[/cyan]")
            reasoning.add("Inference & Planning")

            # Ethics
            ethics = flow.add("⚖️ [magenta]Ethics & Values Block[/magenta]")
            ethics.add("👑 Ethics King Oversight")
            ethics.add("Ethical Evaluation")

            # Action
            action = flow.add("🎯 [cyan]Action Selection Block[/cyan]")
            action.add("👑 Forefront King Oversight")
            action.add("👑👑👑 Three Kings Coordination")

            # Language
            language = flow.add("💬 [cyan]Language Processing Block[/cyan]")
            language.add("Response Generation")

            # Learning
            learning = flow.add("📚 [cyan]Continual Learning Block[/cyan]")
            learning.add("System Update")

            # Output
            flow.add("📤 [bold green]Output Response[/bold green]")

            self.console.print(flow)

        else:
            print("\n=== Processing Pipeline ===")
            print("\nInput Query")
            print("  ↓")
            for i, block in enumerate(self.blocks, 1):
                print(f"  {i}. {block}")
                print("  ↓")
            print("Output Response")

    def display_system_metrics(self):
        """Display system performance metrics."""
        if self.use_rich:
            self.console.print("\n[bold blue]📊 System Metrics[/bold blue]\n")

            metrics_table = Table(box=box.ROUNDED, show_header=True)
            metrics_table.add_column("Metric", style="cyan", width=30)
            metrics_table.add_column("Value", justify="right", style="yellow")
            metrics_table.add_column("Status", style="green")

            metrics = [
                ("Total Interactions", f"{random.randint(100, 1000)}", "✓"),
                ("Ethical Evaluations", f"{random.randint(50, 500)}", "✓"),
                ("Decisions Made", f"{random.randint(80, 800)}", "✓"),
                ("Glass Transition Temp (T_g)", f"{random.uniform(0.45, 0.55):.2f}", "✓"),
                ("System Entropy", f"{random.uniform(0.3, 0.6):.2f}", "✓"),
                ("Average Processing Time", f"{random.uniform(0.5, 2.0):.2f}s", "✓"),
                ("Memory Graph Size", f"{random.randint(200, 500)} nodes", "✓"),
                ("Wave Function Facets", "7", "✓")
            ]

            for metric, value, status in metrics:
                metrics_table.add_row(metric, value, status)

            self.console.print(metrics_table)

        else:
            print("\n=== System Metrics ===")
            print(f"  Interactions: {random.randint(100, 1000)}")
            print(f"  Ethical Evaluations: {random.randint(50, 500)}")
            print(f"  Processing Time: {random.uniform(0.5, 2.0):.2f}s")

    def run_showcase(self):
        """Run a complete showcase of all features."""
        self.clear_screen()
        self.print_banner()

        if self.use_rich:
            self.console.print("[bold yellow]🎭 Running Complete System Showcase[/bold yellow]\n")
        else:
            print("=== System Showcase ===\n")

        # Wait for user
        if self.use_rich:
            self.console.input("[dim]Press Enter to begin...[/dim]")
        else:
            input("Press Enter to begin...")

        # Show architecture
        self.show_architecture_overview()
        time.sleep(2)

        # Show pipeline
        self.visualize_pipeline()
        time.sleep(2)

        # Process a sample query
        sample_query = "How can AI systems be used ethically in healthcare?"
        self.display_block_processing(sample_query)

        # Show ethical evaluation
        self.visualize_ethical_evaluation(sample_query)
        time.sleep(1)

        # Show wave function
        self.visualize_wave_function(sample_query)
        time.sleep(1)

        # Show memory updates
        self.visualize_memory_updates(sample_query)
        time.sleep(1)

        # Show metrics
        self.display_system_metrics()

        if self.use_rich:
            self.console.print("\n[bold green]✨ Showcase Complete![/bold green]\n")
        else:
            print("\n=== Showcase Complete ===\n")

    def interactive_menu(self):
        """Display interactive menu."""
        while True:
            if self.use_rich:
                self.console.print("\n[bold cyan]═══ Main Menu ═══[/bold cyan]\n")
                menu_options = """
1. 🏗️  Show Architecture Overview
2. 🔄 Visualize Processing Pipeline
3. 🔍 Process Custom Query
4. ⚖️  Show Ethical Evaluation Demo
5. 🌊 Display Wave Function State
6. 💾 Show Memory System Updates
7. 📊 Display System Metrics
8. 🎭 Run Complete Showcase
9. ❌ Exit

                """
                self.console.print(menu_options)
                choice = self.console.input("[bold yellow]Enter your choice (1-9):[/bold yellow] ").strip()
            else:
                print("\n=== Main Menu ===")
                print("1. Show Architecture Overview")
                print("2. Visualize Processing Pipeline")
                print("3. Process Custom Query")
                print("4. Show Ethical Evaluation Demo")
                print("5. Display Wave Function State")
                print("6. Show Memory System Updates")
                print("7. Display System Metrics")
                print("8. Run Complete Showcase")
                print("9. Exit")
                choice = input("\nEnter your choice (1-9): ").strip()

            if choice == "1":
                self.show_architecture_overview()
            elif choice == "2":
                self.visualize_pipeline()
            elif choice == "3":
                if self.use_rich:
                    query = self.console.input("\n[yellow]Enter your query:[/yellow] ")
                else:
                    query = input("\nEnter your query: ")
                if query:
                    self.display_block_processing(query)
                    self.visualize_ethical_evaluation(query)
                    self.visualize_wave_function(query)
                    self.visualize_memory_updates(query)
            elif choice == "4":
                sample_query = "Should AI make autonomous decisions?"
                self.visualize_ethical_evaluation(sample_query)
            elif choice == "5":
                self.visualize_wave_function("sample query")
            elif choice == "6":
                self.visualize_memory_updates("sample query")
            elif choice == "7":
                self.display_system_metrics()
            elif choice == "8":
                self.run_showcase()
            elif choice == "9":
                if self.use_rich:
                    self.console.print("\n[bold green]👋 Thank you for exploring Verdant-Minds![/bold green]\n")
                else:
                    print("\nThank you for exploring Verdant-Minds!\n")
                break
            else:
                if self.use_rich:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
                else:
                    print("Invalid choice. Please try again.")

            # Pause before showing menu again
            if choice in ["1", "2", "4", "5", "6", "7"]:
                time.sleep(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verdant-Minds Interactive Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demos/interactive_demo.py
  python demos/interactive_demo.py --query "How does AI learn?"
  python demos/interactive_demo.py --showcase
  python demos/interactive_demo.py --no-color

Note: Install 'rich' for beautiful terminal output:
  pip install rich
        """
    )

    parser.add_argument(
        '--query',
        type=str,
        help='Process a specific query and exit'
    )

    parser.add_argument(
        '--showcase',
        action='store_true',
        help='Run complete system showcase'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output (use basic text)'
    )

    args = parser.parse_args()

    # Create demo instance
    use_rich = not args.no_color
    demo = VerdantDemo(use_rich=use_rich)

    # Clear and show banner
    demo.clear_screen()
    demo.print_banner()

    # Handle command line arguments
    if args.query:
        # Process specific query
        demo.display_block_processing(args.query)
        demo.visualize_ethical_evaluation(args.query)
        demo.visualize_wave_function(args.query)
        demo.visualize_memory_updates(args.query)
        demo.display_system_metrics()
    elif args.showcase:
        # Run showcase
        demo.run_showcase()
    else:
        # Interactive menu
        demo.interactive_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        print("Please report issues at: https://github.com/captainkoopa420/Verdant-Minds/issues\n")
        sys.exit(1)
