"""
Performance Benchmarking Suite for Verdant-Minds

This module provides comprehensive performance testing and benchmarking
for the Verdant-Minds cognitive architecture.

Measurements:
- Processing time per cognitive block
- Memory usage during operation
- Throughput (chunks/second)
- Bottleneck identification
- Configuration comparisons

Usage:
    python -m benchmarks.performance_tests --mode full --output results.json
    python -m benchmarks.performance_tests --quick
"""

import time
import psutil
import gc
import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.cognitive_chunk import CognitiveChunk
from src.blocks.sensory_input_block import SensoryInputBlock
from src.blocks.pattern_recognition_block import PatternRecognitionBlock
from src.blocks.memory_storage_block import MemoryStorageBlock
from src.blocks.internal_communication_block import InternalCommunicationBlock
from src.blocks.reasoning_planning_block import ReasoningPlanningBlock
from src.blocks.ethics_values_block import EthicsValuesBlock
from src.blocks.action_selection_block import ActionSelectionBlock
from src.blocks.language_processing_block import LanguageProcessingBlock
from src.blocks.continual_learning_block import ContinualLearningBlock


@dataclass
class BlockPerformance:
    """Performance metrics for a single block."""
    block_name: str
    mean_time_ms: float
    median_time_ms: float
    std_dev_ms: float
    min_time_ms: float
    max_time_ms: float
    total_time_ms: float
    executions: int
    memory_delta_mb: float


@dataclass
class SystemPerformance:
    """Overall system performance metrics."""
    total_time_s: float
    throughput_chunks_per_sec: float
    mean_chunk_time_ms: float
    total_chunks: int
    peak_memory_mb: float
    avg_memory_mb: float
    block_performances: List[BlockPerformance]
    bottleneck_block: str
    configuration: str


class PerformanceBenchmark:
    """
    Comprehensive performance benchmarking for Verdant-Minds.
    """

    def __init__(
        self,
        config_name: str = "default",
        memory_bridge=None
    ):
        """
        Initialize benchmark suite.

        Args:
            config_name: Configuration identifier
            memory_bridge: Optional memory bridge instance
        """
        self.config_name = config_name
        self.memory_bridge = memory_bridge

        # Initialize blocks
        self.blocks = {
            "SensoryInput": SensoryInputBlock(),
            "PatternRecognition": PatternRecognitionBlock(memory_bridge=memory_bridge),
            "MemoryStorage": MemoryStorageBlock(memory_bridge=memory_bridge),
            "InternalCommunication": InternalCommunicationBlock(),
            "ReasoningPlanning": ReasoningPlanningBlock(),
            "EthicsValues": EthicsValuesBlock(),
            "ActionSelection": ActionSelectionBlock(),
            "LanguageProcessing": LanguageProcessingBlock(),
            "ContinualLearning": ContinualLearningBlock()
        }

        # Performance tracking
        self.block_timings: Dict[str, List[float]] = {
            name: [] for name in self.blocks.keys()
        }
        self.block_memory: Dict[str, List[float]] = {
            name: [] for name in self.blocks.keys()
        }
        self.memory_samples: List[float] = []

        # Process for memory monitoring
        self.process = psutil.Process()

    def run_full_benchmark(
        self,
        num_iterations: int = 100,
        test_inputs: Optional[List[str]] = None
    ) -> SystemPerformance:
        """
        Run comprehensive benchmark with multiple iterations.

        Args:
            num_iterations: Number of chunks to process
            test_inputs: Custom test inputs (optional)

        Returns:
            SystemPerformance metrics
        """
        print(f"\n{'='*70}")
        print(f"Verdant-Minds Performance Benchmark")
        print(f"Configuration: {self.config_name}")
        print(f"Iterations: {num_iterations}")
        print(f"{'='*70}\n")

        # Generate test inputs if not provided
        if test_inputs is None:
            test_inputs = self._generate_test_inputs(num_iterations)
        else:
            # Repeat inputs to reach desired iterations
            test_inputs = (test_inputs * (num_iterations // len(test_inputs) + 1))[:num_iterations]

        # Force garbage collection before starting
        gc.collect()

        # Record start metrics
        start_time = time.time()
        start_memory = self._get_memory_mb()

        # Run benchmark
        print("Running benchmark...")
        for i, input_text in enumerate(test_inputs):
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{num_iterations} chunks...")

            self._process_single_chunk(input_text)

        # Record end metrics
        end_time = time.time()
        end_memory = self._get_memory_mb()

        total_time_s = end_time - start_time

        print(f"\nBenchmark complete!")
        print(f"Total time: {total_time_s:.2f}s")
        print(f"Memory delta: {end_memory - start_memory:.2f} MB\n")

        # Compute metrics
        performance = self._compute_metrics(
            total_time_s=total_time_s,
            num_chunks=num_iterations
        )

        # Print results
        self._print_results(performance)

        return performance

    def run_quick_benchmark(self) -> SystemPerformance:
        """
        Run quick benchmark with reduced iterations.

        Returns:
            SystemPerformance metrics
        """
        print("\nRunning QUICK benchmark (10 iterations)...")
        return self.run_full_benchmark(num_iterations=10)

    def compare_configurations(
        self,
        config_names: List[str],
        num_iterations: int = 50
    ) -> Dict[str, SystemPerformance]:
        """
        Compare performance across different configurations.

        Args:
            config_names: List of configuration names to compare
            num_iterations: Number of iterations per config

        Returns:
            Dictionary mapping config name to performance
        """
        results = {}

        for config_name in config_names:
            print(f"\n{'='*70}")
            print(f"Testing configuration: {config_name}")
            print(f"{'='*70}")

            # TODO: Load actual config and reinitialize blocks
            # For now, just run with current config
            self.config_name = config_name
            results[config_name] = self.run_full_benchmark(num_iterations)

        # Print comparison
        self._print_comparison(results)

        return results

    def benchmark_single_block(
        self,
        block_name: str,
        num_iterations: int = 1000
    ) -> BlockPerformance:
        """
        Benchmark a single block in isolation.

        Args:
            block_name: Name of block to benchmark
            num_iterations: Number of iterations

        Returns:
            BlockPerformance metrics
        """
        if block_name not in self.blocks:
            raise ValueError(f"Unknown block: {block_name}")

        print(f"\nBenchmarking {block_name} block ({num_iterations} iterations)...")

        block = self.blocks[block_name]
        timings = []
        memory_deltas = []

        # Create a test chunk
        chunk = CognitiveChunk(chunk_id=f"bench_test")

        # Add sensory input section for pattern recognition
        if block_name == "PatternRecognition":
            chunk.update_section("sensory_input_section", {
                "input_text": "What are the ethical implications of AI in healthcare?",
                "tokens": ["What", "are", "the", "ethical", "implications", "of", "AI", "in", "healthcare"],
                "complexity": 0.6
            })

        # Benchmark
        for i in range(num_iterations):
            gc.collect()
            mem_before = self._get_memory_mb()
            start = time.perf_counter()

            block.process_chunk(chunk)

            end = time.perf_counter()
            mem_after = self._get_memory_mb()

            timings.append((end - start) * 1000)  # Convert to ms
            memory_deltas.append(mem_after - mem_before)

            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{num_iterations} iterations...")

        # Compute statistics
        performance = BlockPerformance(
            block_name=block_name,
            mean_time_ms=statistics.mean(timings),
            median_time_ms=statistics.median(timings),
            std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
            min_time_ms=min(timings),
            max_time_ms=max(timings),
            total_time_ms=sum(timings),
            executions=num_iterations,
            memory_delta_mb=statistics.mean(memory_deltas)
        )

        print(f"\nResults for {block_name}:")
        print(f"  Mean time: {performance.mean_time_ms:.3f} ms")
        print(f"  Median time: {performance.median_time_ms:.3f} ms")
        print(f"  Std dev: {performance.std_dev_ms:.3f} ms")
        print(f"  Range: [{performance.min_time_ms:.3f}, {performance.max_time_ms:.3f}] ms")
        print(f"  Memory delta: {performance.memory_delta_mb:.3f} MB")

        return performance

    def identify_bottleneck(self) -> str:
        """
        Identify the slowest block (bottleneck).

        Returns:
            Name of bottleneck block
        """
        mean_times = {
            name: statistics.mean(timings) if timings else 0
            for name, timings in self.block_timings.items()
        }

        bottleneck = max(mean_times, key=mean_times.get)
        return bottleneck

    def _process_single_chunk(self, input_text: str):
        """Process a single chunk through all blocks."""
        chunk = CognitiveChunk(chunk_id=f"bench_{time.time()}")

        for block_name, block in self.blocks.items():
            gc.collect()

            # Measure memory before
            mem_before = self._get_memory_mb()

            # Measure time
            start = time.perf_counter()
            chunk = block.process_chunk(chunk)
            end = time.perf_counter()

            # Measure memory after
            mem_after = self._get_memory_mb()

            # Record metrics
            elapsed_ms = (end - start) * 1000
            self.block_timings[block_name].append(elapsed_ms)
            self.block_memory[block_name].append(mem_after - mem_before)
            self.memory_samples.append(mem_after)

    def _compute_metrics(
        self,
        total_time_s: float,
        num_chunks: int
    ) -> SystemPerformance:
        """Compute overall performance metrics."""
        # Compute block performances
        block_performances = []
        for block_name, timings in self.block_timings.items():
            if not timings:
                continue

            performance = BlockPerformance(
                block_name=block_name,
                mean_time_ms=statistics.mean(timings),
                median_time_ms=statistics.median(timings),
                std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
                min_time_ms=min(timings),
                max_time_ms=max(timings),
                total_time_ms=sum(timings),
                executions=len(timings),
                memory_delta_mb=statistics.mean(self.block_memory[block_name])
            )
            block_performances.append(performance)

        # Overall metrics
        throughput = num_chunks / total_time_s if total_time_s > 0 else 0
        mean_chunk_time_ms = (total_time_s / num_chunks) * 1000 if num_chunks > 0 else 0

        peak_memory_mb = max(self.memory_samples) if self.memory_samples else 0
        avg_memory_mb = statistics.mean(self.memory_samples) if self.memory_samples else 0

        bottleneck = self.identify_bottleneck()

        return SystemPerformance(
            total_time_s=total_time_s,
            throughput_chunks_per_sec=throughput,
            mean_chunk_time_ms=mean_chunk_time_ms,
            total_chunks=num_chunks,
            peak_memory_mb=peak_memory_mb,
            avg_memory_mb=avg_memory_mb,
            block_performances=block_performances,
            bottleneck_block=bottleneck,
            configuration=self.config_name
        )

    def _print_results(self, performance: SystemPerformance):
        """Print formatted results."""
        print(f"\n{'='*70}")
        print(f"BENCHMARK RESULTS")
        print(f"{'='*70}")
        print(f"\nOverall Performance:")
        print(f"  Total time: {performance.total_time_s:.3f}s")
        print(f"  Throughput: {performance.throughput_chunks_per_sec:.2f} chunks/sec")
        print(f"  Mean chunk time: {performance.mean_chunk_time_ms:.3f} ms")
        print(f"  Total chunks: {performance.total_chunks}")
        print(f"\nMemory Usage:")
        print(f"  Peak memory: {performance.peak_memory_mb:.2f} MB")
        print(f"  Average memory: {performance.avg_memory_mb:.2f} MB")
        print(f"\nBottleneck: {performance.bottleneck_block}")

        print(f"\nBlock-by-Block Performance:")
        print(f"{'Block':<25} {'Mean (ms)':>12} {'Median (ms)':>12} {'Std Dev':>12} {'Total (ms)':>12}")
        print(f"{'-'*80}")

        # Sort by mean time (slowest first)
        sorted_blocks = sorted(
            performance.block_performances,
            key=lambda b: b.mean_time_ms,
            reverse=True
        )

        for block_perf in sorted_blocks:
            print(
                f"{block_perf.block_name:<25} "
                f"{block_perf.mean_time_ms:>12.3f} "
                f"{block_perf.median_time_ms:>12.3f} "
                f"{block_perf.std_dev_ms:>12.3f} "
                f"{block_perf.total_time_ms:>12.1f}"
            )

        print(f"{'='*70}\n")

    def _print_comparison(self, results: Dict[str, SystemPerformance]):
        """Print comparison between configurations."""
        print(f"\n{'='*70}")
        print(f"CONFIGURATION COMPARISON")
        print(f"{'='*70}\n")

        print(f"{'Configuration':<25} {'Throughput':>15} {'Mean Time':>15} {'Peak Memory':>15}")
        print(f"{'-'*70}")

        for config_name, performance in results.items():
            print(
                f"{config_name:<25} "
                f"{performance.throughput_chunks_per_sec:>14.2f} "
                f"{performance.mean_chunk_time_ms:>14.3f} ms "
                f"{performance.peak_memory_mb:>14.2f} MB"
            )

        print(f"{'='*70}\n")

    def _generate_test_inputs(self, count: int) -> List[str]:
        """Generate varied test inputs."""
        templates = [
            "What are the ethical implications of AI in {domain}?",
            "How can we balance {concept1} and {concept2}?",
            "Should we use AI for {application}?",
            "Explain the concept of {concept}.",
            "What if we combine {tech1} with {tech2}?",
            "Is it right to {action} in {situation}?",
            "Compare {option1} versus {option2}.",
            "Why does {phenomenon} occur?",
        ]

        domains = ["healthcare", "education", "surveillance", "employment", "warfare"]
        concepts = ["privacy", "security", "freedom", "autonomy", "justice", "fairness"]
        applications = ["criminal justice", "hiring", "medical diagnosis", "social media"]
        techs = ["neural networks", "genetic algorithms", "quantum computing", "blockchain"]
        actions = ["intervene", "collect data", "automate decisions", "restrict access"]
        situations = ["emergencies", "conflicts", "daily life", "research"]

        inputs = []
        import random
        random.seed(42)

        for i in range(count):
            template = random.choice(templates)
            text = template.format(
                domain=random.choice(domains),
                concept1=random.choice(concepts),
                concept2=random.choice(concepts),
                concept=random.choice(concepts),
                application=random.choice(applications),
                tech1=random.choice(techs),
                tech2=random.choice(techs),
                action=random.choice(actions),
                situation=random.choice(situations),
                option1=random.choice(concepts),
                option2=random.choice(concepts),
                phenomenon=random.choice(techs)
            )
            inputs.append(text)

        return inputs

    def _get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def save_results(self, performance: SystemPerformance, output_path: str):
        """Save results to JSON file."""
        # Convert to dict
        results = {
            "configuration": performance.configuration,
            "total_time_s": performance.total_time_s,
            "throughput_chunks_per_sec": performance.throughput_chunks_per_sec,
            "mean_chunk_time_ms": performance.mean_chunk_time_ms,
            "total_chunks": performance.total_chunks,
            "peak_memory_mb": performance.peak_memory_mb,
            "avg_memory_mb": performance.avg_memory_mb,
            "bottleneck_block": performance.bottleneck_block,
            "block_performances": [asdict(bp) for bp in performance.block_performances]
        }

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {output_path}")


def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description="Verdant-Minds Performance Benchmarking")
    parser.add_argument("--mode", choices=["quick", "full", "block", "compare"],
                       default="quick", help="Benchmark mode")
    parser.add_argument("--iterations", type=int, default=100,
                       help="Number of iterations (for full mode)")
    parser.add_argument("--block", type=str, help="Block name (for block mode)")
    parser.add_argument("--output", type=str, default="benchmark_results.json",
                       help="Output file for results")
    parser.add_argument("--config", type=str, default="default",
                       help="Configuration name")

    args = parser.parse_args()

    # Create benchmark
    benchmark = PerformanceBenchmark(config_name=args.config)

    # Run appropriate benchmark
    if args.mode == "quick":
        performance = benchmark.run_quick_benchmark()
    elif args.mode == "full":
        performance = benchmark.run_full_benchmark(num_iterations=args.iterations)
    elif args.mode == "block":
        if not args.block:
            print("Error: --block required for block mode")
            return
        performance = benchmark.benchmark_single_block(args.block, num_iterations=1000)
        # Convert to SystemPerformance for saving
        performance = SystemPerformance(
            total_time_s=performance.total_time_ms / 1000,
            throughput_chunks_per_sec=0,
            mean_chunk_time_ms=performance.mean_time_ms,
            total_chunks=performance.executions,
            peak_memory_mb=0,
            avg_memory_mb=performance.memory_delta_mb,
            block_performances=[performance],
            bottleneck_block=performance.block_name,
            configuration=args.config
        )
    elif args.mode == "compare":
        configs = ["default", "performance_optimized", "research_debug"]
        results = benchmark.compare_configurations(configs, num_iterations=50)
        # Save first config results
        performance = results["default"]
    else:
        print(f"Unknown mode: {args.mode}")
        return

    # Save results
    benchmark.save_results(performance, args.output)


if __name__ == "__main__":
    main()
