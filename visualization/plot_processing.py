#!/usr/bin/env python3
"""
Processing Visualization for Verdant-Minds

Creates publication-quality visualizations of cognitive processing,
wave functions, memory patterns, and ethical evaluations.

Features:
- CognitiveChunk flow visualization
- ECWF state evolution plots
- Memory activation heatmaps
- Ethical principle scoring
- Multi-panel publication figures

Usage:
    python visualization/plot_processing.py --all
    python visualization/plot_processing.py --chunk-flow
    python visualization/plot_processing.py --wave-evolution
    python visualization/plot_processing.py --memory-activation
    python visualization/plot_processing.py --ethical-scores

Requirements:
    pip install matplotlib numpy seaborn
"""

import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Try to import seaborn for better styling
try:
    import seaborn as sns
    sns.set_style("whitegrid")
    sns.set_palette("husl")
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False

# Configure matplotlib for publication quality
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16


@dataclass
class ProcessingData:
    """Container for processing visualization data."""
    blocks: List[str]
    processing_times: List[float]
    activations: List[float]
    timestamp: float


@dataclass
class WaveFunctionData:
    """Container for wave function evolution data."""
    cognitive_dims: List[str]
    ethical_dims: List[str]
    cognitive_amplitudes: np.ndarray
    ethical_amplitudes: np.ndarray
    entropy: List[float]
    time_steps: List[float]


@dataclass
class MemoryData:
    """Container for memory activation data."""
    concepts: List[str]
    activations: np.ndarray
    connections: np.ndarray
    timestamps: List[float]


@dataclass
class EthicalData:
    """Container for ethical evaluation data."""
    principles: List[str]
    scores: np.ndarray
    thresholds: np.ndarray
    verdicts: List[str]


class ProcessingVisualizer:
    """Publication-quality visualization generator."""

    def __init__(self, output_dir: str = "outputs/figures"):
        """Initialize visualizer."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Define color schemes
        self.colors = {
            'primary': '#2C3E50',
            'secondary': '#3498DB',
            'success': '#27AE60',
            'warning': '#F39C12',
            'danger': '#E74C3C',
            'cognitive': '#3498DB',
            'ethical': '#9B59B6',
            'memory': '#E67E22',
            'king': '#C0392B'
        }

        # Block names
        self.block_names = [
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

    def generate_sample_data(self) -> Tuple[ProcessingData, WaveFunctionData, MemoryData, EthicalData]:
        """Generate sample data for visualization."""
        # Processing data
        processing_times = np.random.exponential(0.15, len(self.block_names))
        activations = np.random.uniform(0.6, 0.98, len(self.block_names))

        processing_data = ProcessingData(
            blocks=self.block_names,
            processing_times=processing_times.tolist(),
            activations=activations.tolist(),
            timestamp=0.0
        )

        # Wave function data
        cog_dims = [
            "Situational\nAwareness",
            "Consequence\nPrediction",
            "Pattern\nRecognition",
            "Past\nExperience",
            "Decision\nComplexity"
        ]

        eth_dims = [
            "Non-\nmaleficence",
            "Beneficence",
            "Autonomy",
            "Justice",
            "Transparency"
        ]

        time_steps = np.linspace(0, 10, 50)
        cog_amps = np.random.randn(50, 5).cumsum(axis=0)
        cog_amps = (cog_amps - cog_amps.min(axis=0)) / (cog_amps.max(axis=0) - cog_amps.min(axis=0))

        eth_amps = np.random.randn(50, 5).cumsum(axis=0)
        eth_amps = (eth_amps - eth_amps.min(axis=0)) / (eth_amps.max(axis=0) - eth_amps.min(axis=0))

        entropy = 0.5 + 0.3 * np.sin(time_steps) + 0.1 * np.random.randn(50)

        wave_data = WaveFunctionData(
            cognitive_dims=cog_dims,
            ethical_dims=eth_dims,
            cognitive_amplitudes=cog_amps,
            ethical_amplitudes=eth_amps,
            entropy=entropy.tolist(),
            time_steps=time_steps.tolist()
        )

        # Memory data
        concepts = [f"Concept_{i}" for i in range(20)]
        activations = np.random.exponential(1, (10, 20))
        connections = np.random.rand(20, 20)
        connections = (connections + connections.T) / 2  # Symmetric
        np.fill_diagonal(connections, 0)

        memory_data = MemoryData(
            concepts=concepts,
            activations=activations,
            connections=connections,
            timestamps=np.linspace(0, 10, 10).tolist()
        )

        # Ethical data
        principles = [
            "Non-maleficence\n(avoid harm)",
            "Beneficence\n(do good)",
            "Autonomy\n(respect choice)",
            "Justice\n(fairness)",
            "Transparency"
        ]

        scores = np.array([
            [0.85, 0.78, 0.92, 0.88, 0.76],
            [0.82, 0.85, 0.89, 0.91, 0.79],
            [0.88, 0.81, 0.94, 0.87, 0.82]
        ])

        thresholds = np.array([0.75, 0.75, 0.75, 0.75, 0.75])
        verdicts = ["Approved", "Approved", "Approved"]

        ethical_data = EthicalData(
            principles=principles,
            scores=scores,
            thresholds=thresholds,
            verdicts=verdicts
        )

        return processing_data, wave_data, memory_data, ethical_data

    def plot_chunk_flow(self, data: ProcessingData, save: bool = True, show: bool = False) -> str:
        """
        Visualize CognitiveChunk flow through processing blocks.

        Creates a publication-quality figure showing:
        - Processing time per block
        - Activation levels
        - Information flow diagram

        Args:
            data: Processing data
            save: Whether to save the figure
            show: Whether to display the figure

        Returns:
            Path to saved figure
        """
        fig = plt.figure(figsize=(14, 10))
        gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. Processing times bar chart
        ax1 = fig.add_subplot(gs[0, :])
        colors = [self.colors['cognitive'] if 'King' not in block else self.colors['king']
                  for block in data.blocks]

        bars = ax1.barh(data.blocks, data.processing_times, color=colors, alpha=0.7, edgecolor='black')

        # Add value labels
        for i, (bar, time) in enumerate(zip(bars, data.processing_times)):
            ax1.text(time + 0.01, i, f'{time:.3f}s', va='center', fontsize=9)

        ax1.set_xlabel('Processing Time (seconds)', fontweight='bold')
        ax1.set_title('Processing Time per Cognitive Block', fontweight='bold', pad=15)
        ax1.grid(axis='x', alpha=0.3)
        ax1.set_xlim(0, max(data.processing_times) * 1.15)

        # 2. Block activation levels
        ax2 = fig.add_subplot(gs[1, 0])

        activation_colors = plt.cm.RdYlGn(data.activations)
        bars = ax2.bar(range(len(data.blocks)), data.activations,
                       color=activation_colors, edgecolor='black', alpha=0.8)

        ax2.set_ylabel('Activation Level', fontweight='bold')
        ax2.set_xlabel('Block Index', fontweight='bold')
        ax2.set_title('Block Activation Levels', fontweight='bold')
        ax2.set_xticks(range(len(data.blocks)))
        ax2.set_xticklabels(range(1, len(data.blocks) + 1))
        ax2.set_ylim(0, 1.0)
        ax2.axhline(y=0.75, color='red', linestyle='--', alpha=0.5, label='Threshold')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)

        # Add activation percentage labels
        for i, (bar, act) in enumerate(zip(bars, data.activations)):
            ax2.text(i, act + 0.02, f'{act:.0%}', ha='center', fontsize=8)

        # 3. Cumulative processing time
        ax3 = fig.add_subplot(gs[1, 1])

        cumulative_times = np.cumsum(data.processing_times)
        ax3.plot(range(len(data.blocks)), cumulative_times, marker='o',
                linewidth=2, markersize=8, color=self.colors['primary'])
        ax3.fill_between(range(len(data.blocks)), cumulative_times,
                         alpha=0.3, color=self.colors['secondary'])

        ax3.set_ylabel('Cumulative Time (seconds)', fontweight='bold')
        ax3.set_xlabel('Block Index', fontweight='bold')
        ax3.set_title('Cumulative Processing Time', fontweight='bold')
        ax3.set_xticks(range(len(data.blocks)))
        ax3.set_xticklabels(range(1, len(data.blocks) + 1))
        ax3.grid(True, alpha=0.3)

        # 4. Processing flow diagram
        ax4 = fig.add_subplot(gs[2, :])

        # Create Sankey-like flow diagram
        y_positions = np.linspace(0, 1, len(data.blocks))

        for i, (block, activation) in enumerate(zip(data.blocks, data.activations)):
            # Draw block
            color = self.colors['king'] if 'King' in block or 'Ethics' in block else self.colors['cognitive']
            rect = mpatches.Rectangle((0.05 + i * 0.09, 0.4), 0.08, 0.2,
                                     facecolor=color, edgecolor='black',
                                     alpha=0.7, linewidth=1.5)
            ax4.add_patch(rect)

            # Add block label
            ax4.text(0.09 + i * 0.09, 0.25, f'B{i+1}',
                    ha='center', va='top', fontsize=9, fontweight='bold')

            # Draw connection to next block
            if i < len(data.blocks) - 1:
                arrow = mpatches.FancyArrowPatch(
                    (0.13 + i * 0.09, 0.5),
                    (0.05 + (i + 1) * 0.09, 0.5),
                    arrowstyle='->', mutation_scale=20,
                    color='gray', alpha=0.6, linewidth=2
                )
                ax4.add_patch(arrow)

        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        ax4.set_title('Information Flow Through Blocks', fontweight='bold', pad=15)

        # Add legend
        legend_elements = [
            mpatches.Patch(facecolor=self.colors['cognitive'], alpha=0.7,
                          edgecolor='black', label='Cognitive Block'),
            mpatches.Patch(facecolor=self.colors['king'], alpha=0.7,
                          edgecolor='black', label='Ethical/King Block')
        ]
        ax4.legend(handles=legend_elements, loc='lower right')

        # Overall title
        fig.suptitle('Cognitive Chunk Processing Flow Analysis',
                    fontsize=18, fontweight='bold', y=0.98)

        # Save figure
        filename = self.output_dir / f'chunk_flow_{datetime.now():%Y%m%d_%H%M%S}.png'
        if save:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved: {filename}")

        if show:
            plt.show()
        else:
            plt.close()

        return str(filename)

    def plot_wave_evolution(self, data: WaveFunctionData, save: bool = True, show: bool = False) -> str:
        """
        Visualize ECWF state evolution over time.

        Creates a publication-quality figure showing:
        - Cognitive dimension amplitudes over time
        - Ethical dimension amplitudes over time
        - Wave function entropy evolution
        - State space trajectory

        Args:
            data: Wave function data
            save: Whether to save the figure
            show: Whether to display the figure

        Returns:
            Path to saved figure
        """
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(3, 2, figure=fig, hspace=0.35, wspace=0.3)

        # 1. Cognitive dimensions over time
        ax1 = fig.add_subplot(gs[0, :])

        for i, dim in enumerate(data.cognitive_dims):
            ax1.plot(data.time_steps, data.cognitive_amplitudes[:, i],
                    label=dim, linewidth=2, alpha=0.8)

        ax1.set_xlabel('Time Steps', fontweight='bold')
        ax1.set_ylabel('Amplitude', fontweight='bold')
        ax1.set_title('Cognitive State Evolution', fontweight='bold', fontsize=14)
        ax1.legend(loc='upper left', ncol=5, framealpha=0.9)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 1)

        # 2. Ethical dimensions over time
        ax2 = fig.add_subplot(gs[1, :])

        for i, dim in enumerate(data.ethical_dims):
            ax2.plot(data.time_steps, data.ethical_amplitudes[:, i],
                    label=dim, linewidth=2, alpha=0.8, linestyle='--')

        ax2.set_xlabel('Time Steps', fontweight='bold')
        ax2.set_ylabel('Amplitude', fontweight='bold')
        ax2.set_title('Ethical State Evolution', fontweight='bold', fontsize=14)
        ax2.legend(loc='upper left', ncol=5, framealpha=0.9)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 1)

        # 3. Entropy evolution
        ax3 = fig.add_subplot(gs[2, 0])

        ax3.plot(data.time_steps, data.entropy, linewidth=2.5,
                color=self.colors['danger'], alpha=0.8)
        ax3.fill_between(data.time_steps, data.entropy, alpha=0.3,
                        color=self.colors['danger'])

        ax3.set_xlabel('Time Steps', fontweight='bold')
        ax3.set_ylabel('Entropy', fontweight='bold')
        ax3.set_title('Wave Function Entropy (Uncertainty)', fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Add entropy statistics
        mean_entropy = np.mean(data.entropy)
        ax3.axhline(y=mean_entropy, color='black', linestyle='--',
                   alpha=0.5, label=f'Mean: {mean_entropy:.3f}')
        ax3.legend()

        # 4. State space trajectory (2D projection)
        ax4 = fig.add_subplot(gs[2, 1])

        # Use first two cognitive dimensions for visualization
        scatter = ax4.scatter(data.cognitive_amplitudes[:, 0],
                             data.cognitive_amplitudes[:, 1],
                             c=data.time_steps, cmap='viridis',
                             s=50, alpha=0.6, edgecolors='black')

        # Draw trajectory
        ax4.plot(data.cognitive_amplitudes[:, 0],
                data.cognitive_amplitudes[:, 1],
                color='gray', alpha=0.3, linewidth=1)

        # Mark start and end
        ax4.scatter(data.cognitive_amplitudes[0, 0],
                   data.cognitive_amplitudes[0, 1],
                   color='green', s=200, marker='o', edgecolors='black',
                   linewidths=2, label='Start', zorder=5)
        ax4.scatter(data.cognitive_amplitudes[-1, 0],
                   data.cognitive_amplitudes[-1, 1],
                   color='red', s=200, marker='s', edgecolors='black',
                   linewidths=2, label='End', zorder=5)

        ax4.set_xlabel(f'{data.cognitive_dims[0]} Amplitude', fontweight='bold')
        ax4.set_ylabel(f'{data.cognitive_dims[1]} Amplitude', fontweight='bold')
        ax4.set_title('State Space Trajectory (2D Projection)', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        cbar = plt.colorbar(scatter, ax=ax4)
        cbar.set_label('Time Step', fontweight='bold')

        # Overall title
        fig.suptitle('Extended Cognitive Wave Function (ECWF) Evolution',
                    fontsize=18, fontweight='bold', y=0.99)

        # Save figure
        filename = self.output_dir / f'wave_evolution_{datetime.now():%Y%m%d_%H%M%S}.png'
        if save:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved: {filename}")

        if show:
            plt.show()
        else:
            plt.close()

        return str(filename)

    def plot_memory_activation(self, data: MemoryData, save: bool = True, show: bool = False) -> str:
        """
        Visualize memory activation patterns.

        Creates a publication-quality figure showing:
        - Activation heatmap over time
        - Connection strength matrix
        - Top activated concepts
        - Activation dynamics

        Args:
            data: Memory activation data
            save: Whether to save the figure
            show: Whether to display the figure

        Returns:
            Path to saved figure
        """
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. Activation heatmap over time
        ax1 = fig.add_subplot(gs[0, :])

        im1 = ax1.imshow(data.activations.T, aspect='auto', cmap='YlOrRd',
                        interpolation='nearest')

        ax1.set_xlabel('Time Step', fontweight='bold')
        ax1.set_ylabel('Concept Index', fontweight='bold')
        ax1.set_title('Memory Activation Patterns Over Time', fontweight='bold', fontsize=14)

        # Add colorbar
        cbar1 = plt.colorbar(im1, ax=ax1)
        cbar1.set_label('Activation Strength', fontweight='bold')

        # 2. Connection strength matrix
        ax2 = fig.add_subplot(gs[1, 0])

        im2 = ax2.imshow(data.connections, cmap='Blues', vmin=0, vmax=1)

        ax2.set_xlabel('Concept Index', fontweight='bold')
        ax2.set_ylabel('Concept Index', fontweight='bold')
        ax2.set_title('Concept Connection Matrix', fontweight='bold')

        # Add colorbar
        cbar2 = plt.colorbar(im2, ax=ax2)
        cbar2.set_label('Connection Strength', fontweight='bold')

        # 3. Top activated concepts
        ax3 = fig.add_subplot(gs[1, 1])

        # Calculate average activation per concept
        avg_activation = data.activations.mean(axis=0)
        top_indices = np.argsort(avg_activation)[-10:][::-1]

        top_concepts = [data.concepts[i] for i in top_indices]
        top_activations = avg_activation[top_indices]

        bars = ax3.barh(range(len(top_concepts)), top_activations,
                       color=self.colors['memory'], alpha=0.7, edgecolor='black')

        ax3.set_yticks(range(len(top_concepts)))
        ax3.set_yticklabels(top_concepts)
        ax3.set_xlabel('Average Activation', fontweight='bold')
        ax3.set_title('Top 10 Activated Concepts', fontweight='bold')
        ax3.grid(axis='x', alpha=0.3)

        # Add value labels
        for i, (bar, act) in enumerate(zip(bars, top_activations)):
            ax3.text(act + 0.05, i, f'{act:.2f}', va='center', fontsize=9)

        # Overall title
        fig.suptitle('Memory Web Activation Analysis',
                    fontsize=18, fontweight='bold', y=0.98)

        # Save figure
        filename = self.output_dir / f'memory_activation_{datetime.now():%Y%m%d_%H%M%S}.png'
        if save:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved: {filename}")

        if show:
            plt.show()
        else:
            plt.close()

        return str(filename)

    def plot_ethical_scores(self, data: EthicalData, save: bool = True, show: bool = False) -> str:
        """
        Visualize ethical principle scores.

        Creates a publication-quality figure showing:
        - Principle scores across evaluations
        - Radar chart of ethical dimensions
        - Score distribution
        - Threshold comparison

        Args:
            data: Ethical evaluation data
            save: Whether to save the figure
            show: Whether to display the figure

        Returns:
            Path to saved figure
        """
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

        # 1. Ethical scores heatmap
        ax1 = fig.add_subplot(gs[0, :])

        im = ax1.imshow(data.scores, cmap='RdYlGn', aspect='auto',
                       vmin=0, vmax=1, interpolation='nearest')

        ax1.set_xticks(range(len(data.principles)))
        ax1.set_xticklabels(data.principles, rotation=0, ha='center')
        ax1.set_yticks(range(len(data.verdicts)))
        ax1.set_yticklabels([f'Evaluation {i+1}' for i in range(len(data.verdicts))])
        ax1.set_title('Ethical Principle Scores Across Evaluations',
                     fontweight='bold', fontsize=14)

        # Add score values as text
        for i in range(len(data.verdicts)):
            for j in range(len(data.principles)):
                text_color = 'white' if data.scores[i, j] < 0.5 else 'black'
                ax1.text(j, i, f'{data.scores[i, j]:.2f}',
                        ha='center', va='center', color=text_color,
                        fontweight='bold')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax1)
        cbar.set_label('Score', fontweight='bold')

        # Add threshold line
        for i in range(len(data.principles)):
            ax1.axhline(y=-0.5, color='red', linewidth=2, linestyle='--')

        # 2. Radar chart of average scores
        ax2 = fig.add_subplot(gs[1, 0], projection='polar')

        # Calculate average scores
        avg_scores = data.scores.mean(axis=0)

        # Number of variables
        num_vars = len(data.principles)

        # Compute angle for each axis
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        avg_scores_plot = avg_scores.tolist()
        thresholds_plot = data.thresholds.tolist()

        # Close the plot
        angles += angles[:1]
        avg_scores_plot += avg_scores_plot[:1]
        thresholds_plot += thresholds_plot[:1]

        # Plot
        ax2.plot(angles, avg_scores_plot, 'o-', linewidth=2, label='Average Score',
                color=self.colors['ethical'])
        ax2.fill(angles, avg_scores_plot, alpha=0.25, color=self.colors['ethical'])
        ax2.plot(angles, thresholds_plot, 'r--', linewidth=2, label='Threshold')

        # Fix axis to go in the right order
        ax2.set_theta_offset(np.pi / 2)
        ax2.set_theta_direction(-1)

        # Draw axis lines for each angle and label
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels([p.replace('\n', ' ') for p in data.principles],
                           fontsize=9)

        ax2.set_ylim(0, 1)
        ax2.set_title('Ethical Principles Radar', fontweight='bold',
                     fontsize=12, pad=20)
        ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax2.grid(True)

        # 3. Score distribution
        ax3 = fig.add_subplot(gs[1, 1])

        # Flatten scores for distribution
        all_scores = data.scores.flatten()

        ax3.hist(all_scores, bins=20, color=self.colors['ethical'],
                alpha=0.7, edgecolor='black')
        ax3.axvline(x=data.thresholds[0], color='red', linestyle='--',
                   linewidth=2, label='Threshold')
        ax3.axvline(x=all_scores.mean(), color='green', linestyle='-',
                   linewidth=2, label=f'Mean: {all_scores.mean():.3f}')

        ax3.set_xlabel('Score', fontweight='bold')
        ax3.set_ylabel('Frequency', fontweight='bold')
        ax3.set_title('Score Distribution', fontweight='bold')
        ax3.legend()
        ax3.grid(axis='y', alpha=0.3)

        # Add statistics text
        stats_text = f'Mean: {all_scores.mean():.3f}\n'
        stats_text += f'Std: {all_scores.std():.3f}\n'
        stats_text += f'Min: {all_scores.min():.3f}\n'
        stats_text += f'Max: {all_scores.max():.3f}'

        ax3.text(0.02, 0.98, stats_text, transform=ax3.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round',
                facecolor='wheat', alpha=0.5), fontsize=9)

        # Overall title
        fig.suptitle('Ethical Evaluation Analysis',
                    fontsize=18, fontweight='bold', y=0.98)

        # Save figure
        filename = self.output_dir / f'ethical_scores_{datetime.now():%Y%m%d_%H%M%S}.png'
        if save:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✓ Saved: {filename}")

        if show:
            plt.show()
        else:
            plt.close()

        return str(filename)

    def plot_comprehensive_analysis(self, save: bool = True, show: bool = False) -> List[str]:
        """
        Create comprehensive multi-figure analysis.

        Generates all visualization types with sample data.

        Args:
            save: Whether to save figures
            show: Whether to display figures

        Returns:
            List of paths to saved figures
        """
        print("Generating comprehensive visualization analysis...")
        print("=" * 60)

        # Generate sample data
        proc_data, wave_data, mem_data, eth_data = self.generate_sample_data()

        # Generate all plots
        saved_files = []

        print("\n1. Cognitive Chunk Flow...")
        saved_files.append(self.plot_chunk_flow(proc_data, save=save, show=show))

        print("\n2. Wave Function Evolution...")
        saved_files.append(self.plot_wave_evolution(wave_data, save=save, show=show))

        print("\n3. Memory Activation Patterns...")
        saved_files.append(self.plot_memory_activation(mem_data, save=save, show=show))

        print("\n4. Ethical Scores...")
        saved_files.append(self.plot_ethical_scores(eth_data, save=save, show=show))

        print("\n" + "=" * 60)
        print(f"✓ Generated {len(saved_files)} publication-quality figures")
        print(f"✓ Output directory: {self.output_dir}")

        return saved_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate publication-quality visualizations for Verdant-Minds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualization/plot_processing.py --all
  python visualization/plot_processing.py --chunk-flow
  python visualization/plot_processing.py --wave-evolution
  python visualization/plot_processing.py --output outputs/my_figures
  python visualization/plot_processing.py --all --show

Output:
  All figures are saved as high-resolution PNG files (300 DPI)
  suitable for publication in papers and documentation.
        """
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Generate all visualization types'
    )

    parser.add_argument(
        '--chunk-flow',
        action='store_true',
        help='Generate chunk flow visualization'
    )

    parser.add_argument(
        '--wave-evolution',
        action='store_true',
        help='Generate wave function evolution plot'
    )

    parser.add_argument(
        '--memory-activation',
        action='store_true',
        help='Generate memory activation visualization'
    )

    parser.add_argument(
        '--ethical-scores',
        action='store_true',
        help='Generate ethical scores plot'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='outputs/figures',
        help='Output directory for figures (default: outputs/figures)'
    )

    parser.add_argument(
        '--show',
        action='store_true',
        help='Display figures interactively (in addition to saving)'
    )

    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save figures (only display)'
    )

    args = parser.parse_args()

    # Create visualizer
    visualizer = ProcessingVisualizer(output_dir=args.output)

    # Generate sample data
    proc_data, wave_data, mem_data, eth_data = visualizer.generate_sample_data()

    save = not args.no_save
    show = args.show

    # Check if any specific plot was requested
    any_specific = (args.chunk_flow or args.wave_evolution or
                   args.memory_activation or args.ethical_scores)

    # If --all or no specific flags, generate all
    if args.all or not any_specific:
        visualizer.plot_comprehensive_analysis(save=save, show=show)
    else:
        # Generate specific plots
        if args.chunk_flow:
            print("Generating chunk flow visualization...")
            visualizer.plot_chunk_flow(proc_data, save=save, show=show)

        if args.wave_evolution:
            print("Generating wave evolution visualization...")
            visualizer.plot_wave_evolution(wave_data, save=save, show=show)

        if args.memory_activation:
            print("Generating memory activation visualization...")
            visualizer.plot_memory_activation(mem_data, save=save, show=show)

        if args.ethical_scores:
            print("Generating ethical scores visualization...")
            visualizer.plot_ethical_scores(eth_data, save=save, show=show)

    print("\n✓ Visualization complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nVisualization interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        print("Please report issues at: https://github.com/captainkoopa420/Verdant-Minds/issues")
        sys.exit(1)
