# Verdant-Minds Visualization Suite

Publication-quality visualizations for the Unified Synthetic Mind cognitive architecture.

---

## Overview

This module generates high-resolution, publication-ready visualizations suitable for:
- Academic papers and conferences
- Technical documentation
- Presentations and demos
- Research reports
- Blog posts and articles

All figures are generated at **300 DPI** with professional styling and clear labels.

---

## Quick Start

```bash
# Install dependencies
pip install matplotlib numpy seaborn

# Generate all visualizations
python visualization/plot_processing.py --all

# Or generate specific plots
python visualization/plot_processing.py --chunk-flow
python visualization/plot_processing.py --wave-evolution
python visualization/plot_processing.py --memory-activation
python visualization/plot_processing.py --ethical-scores
```

---

## Visualization Types

### 1. 🔄 Cognitive Chunk Flow

**Command:**
```bash
python visualization/plot_processing.py --chunk-flow
```

**Generates:** `chunk_flow_YYYYMMDD_HHMMSS.png`

**Contents:**
- **Processing Time Bar Chart** - Time spent in each cognitive block
- **Block Activation Levels** - Activation strength visualization
- **Cumulative Processing Time** - Progressive time accumulation
- **Information Flow Diagram** - Visual pipeline representation

**Use Cases:**
- Understanding processing bottlenecks
- Analyzing block performance
- Documenting system flow
- Identifying optimization opportunities

**Example Output:**

```
┌─────────────────────────────────────────────────────┐
│  Processing Time per Cognitive Block                │
│  Sensory Input        ▓▓▓▓▓▓ 0.152s                │
│  Pattern Recognition  ▓▓▓▓▓▓▓▓ 0.189s              │
│  Memory Storage       ▓▓▓▓▓ 0.134s                 │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

### 2. 🌊 Wave Function Evolution

**Command:**
```bash
python visualization/plot_processing.py --wave-evolution
```

**Generates:** `wave_evolution_YYYYMMDD_HHMMSS.png`

**Contents:**
- **Cognitive Dimensions Over Time** - 5 dimensions evolving
- **Ethical Dimensions Over Time** - 5 ethical principles
- **Entropy Evolution** - Wave function uncertainty
- **State Space Trajectory** - 2D projection of cognitive state

**Use Cases:**
- Understanding system dynamics
- Analyzing state evolution
- Studying uncertainty patterns
- Documenting quantum-inspired representations

**Dimensions Visualized:**

*Cognitive:*
1. Situational Awareness
2. Consequence Prediction
3. Pattern Recognition
4. Past Experience
5. Decision Complexity

*Ethical:*
1. Non-maleficence
2. Beneficence
3. Autonomy
4. Justice
5. Transparency

### 3. 💾 Memory Activation Patterns

**Command:**
```bash
python visualization/plot_processing.py --memory-activation
```

**Generates:** `memory_activation_YYYYMMDD_HHMMSS.png`

**Contents:**
- **Activation Heatmap** - Concept activations over time
- **Connection Matrix** - Concept relationship strengths
- **Top Activated Concepts** - Most frequently activated concepts

**Use Cases:**
- Analyzing memory access patterns
- Understanding concept relationships
- Identifying important concepts
- Studying memory dynamics

### 4. ⚖️ Ethical Principle Scores

**Command:**
```bash
python visualization/plot_processing.py --ethical-scores
```

**Generates:** `ethical_scores_YYYYMMDD_HHMMSS.png`

**Contents:**
- **Scores Heatmap** - Principle scores across evaluations
- **Radar Chart** - Multi-dimensional ethical profile
- **Score Distribution** - Statistical analysis of scores
- **Threshold Comparison** - Performance vs. requirements

**Use Cases:**
- Documenting ethical compliance
- Analyzing ethical consistency
- Identifying ethical concerns
- Reporting ethical performance

---

## Command-Line Options

### Basic Usage

```bash
# Generate all visualizations
python visualization/plot_processing.py --all

# Generate specific types
python visualization/plot_processing.py --chunk-flow
python visualization/plot_processing.py --wave-evolution
python visualization/plot_processing.py --memory-activation
python visualization/plot_processing.py --ethical-scores
```

### Advanced Options

```bash
# Custom output directory
python visualization/plot_processing.py --all --output my_figures/

# Display interactively (in addition to saving)
python visualization/plot_processing.py --all --show

# Only display, don't save
python visualization/plot_processing.py --all --show --no-save

# Get help
python visualization/plot_processing.py --help
```

---

## Output Format

### File Naming

All files follow the pattern:
```
{type}_{timestamp}.png
```

Examples:
- `chunk_flow_20251208_143052.png`
- `wave_evolution_20251208_143053.png`
- `memory_activation_20251208_143054.png`
- `ethical_scores_20251208_143055.png`

### File Specifications

- **Format:** PNG
- **Resolution:** 300 DPI
- **Color Space:** RGB
- **Suitable For:** Print and digital media
- **Size:** Typically 4-8 MB per figure
- **Dimensions:** Variable (optimized for readability)

---

## Publication Quality Features

### Professional Styling

✅ **Typography**
- Serif fonts for readability
- Consistent sizing (10-16pt)
- Bold labels and titles
- Clear legends

✅ **Colors**
- Colorblind-friendly palettes
- High contrast for readability
- Consistent color coding
- Professional appearance

✅ **Layout**
- Multi-panel figures
- Proper spacing and alignment
- Clear visual hierarchy
- Publication standards

✅ **Data Presentation**
- Grid lines for reference
- Value labels where appropriate
- Statistical annotations
- Clear axes and units

### Example Styling

```python
# Configuration (already applied)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
```

---

## Integration with Papers

### LaTeX Integration

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.8\textwidth]{figures/chunk_flow_20251208_143052.png}
    \caption{Cognitive Chunk processing flow through the nine-block system,
             showing processing times and activation levels for each block.}
    \label{fig:chunk-flow}
\end{figure}
```

### Markdown Integration

```markdown
![Cognitive Chunk Flow](outputs/figures/chunk_flow_20251208_143052.png)
*Figure 1: Processing flow through cognitive blocks*
```

### Word/PowerPoint

Simply drag and drop the high-resolution PNG files. The 300 DPI ensures they look crisp in print and presentations.

---

## Customization

### Using as a Library

```python
from visualization.plot_processing import ProcessingVisualizer, ProcessingData

# Create visualizer
viz = ProcessingVisualizer(output_dir="my_outputs")

# Create custom data
data = ProcessingData(
    blocks=["Block 1", "Block 2", "Block 3"],
    processing_times=[0.1, 0.15, 0.12],
    activations=[0.85, 0.92, 0.88],
    timestamp=0.0
)

# Generate visualization
viz.plot_chunk_flow(data, save=True, show=False)
```

### Custom Color Schemes

Edit the `colors` dictionary in `ProcessingVisualizer.__init__()`:

```python
self.colors = {
    'primary': '#2C3E50',      # Dark blue-gray
    'secondary': '#3498DB',    # Bright blue
    'success': '#27AE60',      # Green
    'warning': '#F39C12',      # Orange
    'danger': '#E74C3C',       # Red
    'cognitive': '#3498DB',    # Blue
    'ethical': '#9B59B6',      # Purple
    'memory': '#E67E22',       # Orange
    'king': '#C0392B'          # Dark red
}
```

---

## Sample Data

The visualizer includes a `generate_sample_data()` method that creates realistic simulated data for demonstration purposes. This allows generating visualizations without actual system execution or trained models.

**Perfect for:**
- Documentation examples
- Architecture demonstrations
- Proof-of-concept figures
- Teaching materials

---

## Dependencies

### Required

```bash
pip install matplotlib numpy
```

### Recommended

```bash
pip install seaborn  # Better default styling
```

### Optional

```bash
pip install plotly   # Interactive visualizations (future feature)
```

### Full Installation

```bash
# All dependencies
pip install matplotlib numpy seaborn

# Or from requirements
pip install -r requirements.txt
```

---

## Troubleshooting

### Issue: Figures are blurry

**Solution:** The figures are generated at 300 DPI. Ensure you're viewing them at proper resolution. If using in LaTeX, don't scale them too large.

### Issue: Colors look different than examples

**Solution:** Install seaborn for consistent color schemes:
```bash
pip install seaborn
```

### Issue: "Cannot write mode RGBA as JPEG"

**Solution:** The script saves as PNG by default. If you modified it to save as JPEG, convert RGBA to RGB first or use PNG.

### Issue: Font warnings

**Solution:** The script uses serif fonts. If you get warnings, matplotlib will fall back to default fonts automatically.

### Issue: Out of memory

**Solution:** The sample data uses reasonable sizes. If generating many figures, close them after saving:
```python
plt.close('all')
```

---

## Performance

### Generation Time

- **Single figure:** ~0.5-1.5 seconds
- **All figures:** ~3-5 seconds
- **With display:** +1-2 seconds per figure

### File Sizes

- **Typical size:** 2-6 MB per figure
- **High complexity:** Up to 10 MB
- **Simple plots:** 1-3 MB

### Optimization Tips

1. **Batch generation:** Use `--all` to generate all at once
2. **Disable display:** Don't use `--show` for batch processing
3. **Lower DPI:** Edit `plt.rcParams['savefig.dpi']` for smaller files
4. **Close figures:** Use `plt.close()` to free memory

---

## Examples Gallery

### Research Paper Figures

**Figure 1-1:** System Architecture Overview
```bash
python visualization/plot_processing.py --chunk-flow
```
Caption: "Processing time and activation levels across the nine-block cognitive architecture."

**Figure 1-2:** Cognitive Dynamics
```bash
python visualization/plot_processing.py --wave-evolution
```
Caption: "Extended Cognitive Wave Function evolution showing cognitive and ethical dimensions over time."

**Figure 1-3:** Memory Patterns
```bash
python visualization/plot_processing.py --memory-activation
```
Caption: "Memory Web activation patterns and concept interconnections."

**Figure 1-4:** Ethical Evaluation
```bash
python visualization/plot_processing.py --ethical-scores
```
Caption: "Ethical principle scores across multiple evaluations with threshold comparison."

---

## Best Practices

### For Publications

1. **Generate at 300 DPI** (default setting)
2. **Use consistent color schemes** across all figures
3. **Include clear captions** explaining each panel
4. **Label axes properly** with units
5. **Add legends** for clarity
6. **Save as PNG** for lossless quality

### For Presentations

1. **Use `--show` flag** to preview interactively
2. **Consider larger fonts** for projector visibility
3. **Simplify complex figures** for clarity
4. **Use high contrast** for visibility
5. **Test on actual display** before presenting

### For Documentation

1. **Generate fresh figures** when data changes
2. **Use descriptive filenames** with timestamps
3. **Keep originals** in version control
4. **Document data sources** in README
5. **Provide interpretation** in captions

---

## Future Enhancements

Planned features:

- [ ] Interactive Plotly versions
- [ ] Animation support (GIF/MP4)
- [ ] Real-time updating plots
- [ ] Custom templates
- [ ] Batch processing scripts
- [ ] Automated report generation
- [ ] 3D visualizations
- [ ] SVG export option

---

## Contributing

Want to add new visualizations? Guidelines:

1. **Follow existing style** - Use the same color schemes and fonts
2. **Add docstrings** - Document parameters and returns
3. **Include examples** - Show usage in README
4. **Test output** - Verify 300 DPI quality
5. **Update README** - Document new features

---

## Citation

If you use these visualizations in publications:

```bibtex
@software{verdant_minds_viz,
  title = {Verdant-Minds Visualization Suite},
  author = {Verdant-Minds Development Team},
  year = {2025},
  url = {https://github.com/captainkoopa42/Verdant-Minds}
}
```

---

## License

MIT License - See `../LICENSE` for details.

---

## Support

**Issues:** https://github.com/captainkoopa42/Verdant-Minds/issues
**Documentation:** See main `README.md` and `docs/`
**Examples:** See `demos/` directory

---

**Created by:** Verdant-Minds Development Team
**Version:** 0.1.0
**Last Updated:** 2025-12-08
