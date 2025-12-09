"""
Log Analysis Tools for Verdant-Minds

This module provides tools for analyzing logs and extracting insights.

Features:
- Parse structured JSON logs
- Extract performance metrics
- Identify errors and warnings
- Generate reports
- Visualize trends (optional)

Usage:
    python -m src.utils.monitoring.log_analyzer logs/verdant_minds_structured.jsonl --report
"""

import json
import argparse
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import statistics


class LogAnalyzer:
    """Analyze structured JSON logs."""

    def __init__(self, log_file: str):
        """
        Initialize log analyzer.

        Args:
            log_file: Path to structured JSON log file (.jsonl)
        """
        self.log_file = log_file
        self.entries: List[Dict[str, Any]] = []
        self.load_logs()

    def load_logs(self):
        """Load log entries from file."""
        if not Path(self.log_file).exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file}")

        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    self.entries.append(entry)
                except json.JSONDecodeError:
                    continue

        print(f"Loaded {len(self.entries)} log entries from {self.log_file}")

    def get_entries_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get all entries with specified log level."""
        return [e for e in self.entries if e.get("level") == level]

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all ERROR and CRITICAL entries."""
        return [
            e for e in self.entries
            if e.get("level") in ["ERROR", "CRITICAL"]
        ]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Extract performance metrics from logs.

        Returns:
            Dictionary with timing, memory, and throughput metrics
        """
        timings = defaultdict(list)
        memory = defaultdict(list)
        throughput = {}

        for entry in self.entries:
            extra_data = entry.get("extra_data", {})
            metric_type = extra_data.get("metric_type")

            if metric_type == "timing":
                operation = extra_data.get("operation")
                duration = extra_data.get("duration_ms")
                if operation and duration is not None:
                    timings[operation].append(duration)

            elif metric_type == "memory":
                operation = extra_data.get("operation")
                mem = extra_data.get("memory_mb")
                if operation and mem is not None:
                    memory[operation].append(mem)

            elif metric_type == "throughput":
                operation = extra_data.get("operation")
                tput = extra_data.get("items_per_sec")
                if operation and tput is not None:
                    throughput[operation] = tput

        # Compute statistics
        timing_stats = {}
        for operation, values in timings.items():
            if values:
                timing_stats[operation] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                }

        memory_stats = {}
        for operation, values in memory.items():
            if values:
                memory_stats[operation] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "max": max(values),
                }

        return {
            "timing": timing_stats,
            "memory": memory_stats,
            "throughput": throughput
        }

    def get_block_statistics(self) -> Dict[str, Any]:
        """Get statistics about block processing."""
        block_events = defaultdict(int)
        block_errors = defaultdict(int)

        for entry in self.entries:
            extra_data = entry.get("extra_data", {})

            if extra_data.get("event_type") == "chunk_processing":
                block_name = extra_data.get("block_name")
                if block_name:
                    block_events[block_name] += 1

                    if entry.get("level") in ["ERROR", "CRITICAL"]:
                        block_errors[block_name] += 1

        return {
            "events_per_block": dict(block_events),
            "errors_per_block": dict(block_errors)
        }

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors."""
        errors = self.get_errors()

        error_types = Counter()
        error_locations = Counter()

        for error in errors:
            if "exception" in error:
                exc_type = error["exception"].get("type")
                if exc_type:
                    error_types[exc_type] += 1

            module = error.get("module")
            if module:
                error_locations[module] += 1

        return {
            "total_errors": len(errors),
            "error_types": dict(error_types),
            "error_locations": dict(error_locations),
            "recent_errors": errors[-10:] if errors else []
        }

    def generate_report(self) -> str:
        """
        Generate comprehensive analysis report.

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("VERDANT-MINDS LOG ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Log file: {self.log_file}")
        report.append(f"Total entries: {len(self.entries)}")
        report.append("")

        # Log level distribution
        level_counts = Counter(e.get("level") for e in self.entries)
        report.append("Log Level Distribution:")
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            count = level_counts.get(level, 0)
            report.append(f"  {level:<10}: {count:>6}")
        report.append("")

        # Performance metrics
        perf_metrics = self.get_performance_metrics()

        report.append("Performance Metrics:")
        report.append("\n  Timing Statistics:")
        if perf_metrics["timing"]:
            report.append(f"  {'Operation':<30} {'Mean (ms)':>12} {'Median (ms)':>12} {'Min':>12} {'Max':>12}")
            report.append("  " + "-" * 78)
            for operation, stats in sorted(perf_metrics["timing"].items()):
                report.append(
                    f"  {operation:<30} "
                    f"{stats['mean']:>12.3f} "
                    f"{stats['median']:>12.3f} "
                    f"{stats['min']:>12.3f} "
                    f"{stats['max']:>12.3f}"
                )
        else:
            report.append("  No timing data found")
        report.append("")

        # Memory stats
        report.append("  Memory Statistics:")
        if perf_metrics["memory"]:
            report.append(f"  {'Operation':<30} {'Mean (MB)':>15} {'Max (MB)':>15}")
            report.append("  " + "-" * 60)
            for operation, stats in sorted(perf_metrics["memory"].items()):
                report.append(
                    f"  {operation:<30} "
                    f"{stats['mean']:>15.2f} "
                    f"{stats['max']:>15.2f}"
                )
        else:
            report.append("  No memory data found")
        report.append("")

        # Block statistics
        block_stats = self.get_block_statistics()

        report.append("Block Processing Statistics:")
        if block_stats["events_per_block"]:
            report.append(f"  {'Block':<30} {'Events':>15} {'Errors':>15}")
            report.append("  " + "-" * 60)
            for block in sorted(block_stats["events_per_block"].keys()):
                events = block_stats["events_per_block"].get(block, 0)
                errors = block_stats["errors_per_block"].get(block, 0)
                report.append(
                    f"  {block:<30} "
                    f"{events:>15} "
                    f"{errors:>15}"
                )
        else:
            report.append("  No block processing data found")
        report.append("")

        # Error summary
        error_summary = self.get_error_summary()

        report.append("Error Summary:")
        report.append(f"  Total errors: {error_summary['total_errors']}")
        if error_summary["error_types"]:
            report.append("\n  Error Types:")
            for error_type, count in sorted(
                error_summary["error_types"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                report.append(f"    {error_type}: {count}")
        if error_summary["error_locations"]:
            report.append("\n  Error Locations:")
            for location, count in sorted(
                error_summary["error_locations"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]:
                report.append(f"    {location}: {count}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def export_metrics(self, output_file: str):
        """
        Export performance metrics to JSON.

        Args:
            output_file: Path to output JSON file
        """
        metrics = {
            "log_file": self.log_file,
            "total_entries": len(self.entries),
            "performance_metrics": self.get_performance_metrics(),
            "block_statistics": self.get_block_statistics(),
            "error_summary": self.get_error_summary()
        }

        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"Metrics exported to {output_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Analyze Verdant-Minds logs")
    parser.add_argument("log_file", help="Path to structured JSON log file (.jsonl)")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--export", type=str, help="Export metrics to JSON file")
    parser.add_argument("--errors", action="store_true", help="Show errors only")

    args = parser.parse_args()

    # Create analyzer
    analyzer = LogAnalyzer(args.log_file)

    # Generate report
    if args.report:
        report = analyzer.generate_report()
        print(report)

    # Show errors
    if args.errors:
        errors = analyzer.get_errors()
        print(f"\nFound {len(errors)} errors:")
        for i, error in enumerate(errors[-20:], 1):  # Show last 20
            print(f"\n{i}. {error.get('timestamp')} - {error.get('message')}")
            if "exception" in error:
                exc = error["exception"]
                print(f"   Type: {exc.get('type')}")
                print(f"   Message: {exc.get('message')}")

    # Export metrics
    if args.export:
        analyzer.export_metrics(args.export)


if __name__ == "__main__":
    main()
