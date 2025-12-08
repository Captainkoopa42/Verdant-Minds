# Verdant-Minds Demonstrations

Interactive demonstrations and visualizations of the Unified Synthetic Mind cognitive architecture.

---

## 🎭 Interactive Demo

The main interactive demo showcases the complete system architecture with beautiful terminal visualization.

### Quick Start

```bash
# Install required dependency
pip install rich

# Run interactive demo
python demos/interactive_demo.py

# Or make it executable and run directly
chmod +x demos/interactive_demo.py
./demos/interactive_demo.py
```

### Usage Options

**Interactive Menu (Default):**
```bash
python demos/interactive_demo.py
```

Provides a menu-driven interface to explore different aspects of the system.

**Process Specific Query:**
```bash
python demos/interactive_demo.py --query "How does AI learn?"
```

Processes a query and shows all processing stages, ethical evaluation, wave function, and memory updates.

**Complete Showcase:**
```bash
python demos/interactive_demo.py --showcase
```

Runs a comprehensive demonstration of all system features in sequence.

**Basic Text Mode (No Colors):**
```bash
python demos/interactive_demo.py --no-color
```

Falls back to basic text output for terminals without color support.

---

## ✨ Features

### 🏗️ Architecture Overview

Displays the complete system architecture as an interactive tree:
- Memory System (Web, ECWF, Bridge)
- Nine-Block Cognitive System
- Three Kings Governance Layer

```
🧠 Unified Synthetic Mind
├── 💾 Memory System
│   ├── 📊 Memory Web (NetworkX Graph)
│   ├── 🌊 ECWF Core (Wave Functions)
│   └── 🌉 Memory-ECWF Bridge
├── 🔮 Nine-Block Cognitive System
│   ├── 1. Sensory Input
│   ├── 2. Pattern Recognition
│   ├── 3. Memory Storage
│   ├── 4. Internal Communication
│   ├── 5. Reasoning & Planning
│   ├── 6. Ethics & Values
│   ├── 7. Action Selection
│   ├── 8. Language Processing
│   └── 9. Continual Learning
└── 👑 Three Kings Governance
    ├── • Data King
    ├── • Ethics King
    └── • Forefront King
```

### 🔄 Processing Pipeline

Visual representation of how data flows through the system:
- Step-by-step block activation
- Progress bars for each stage
- King oversight indicators
- Real-time processing feedback

### 🔍 Query Processing

Watch a query flow through all nine cognitive blocks:
```
🔍 Processing Query: What is artificial intelligence?

  ✓ Sensory Input: tokens=['What', 'is', 'artificial', 'intelligence?']
  ✓ Pattern Recognition: patterns_detected=5
  ✓ Memory Storage: concepts_stored=15
  ✓ Internal Communication: messages_routed=12
    👑 Data King oversight applied
  ✓ Reasoning & Planning: inference_type=abductive
  ✓ Ethics & Values: ethical_evaluation=approved
    👑 Ethics King oversight applied
  ✓ Action Selection: action=respond
    👑 Forefront King oversight applied
  ✓ Language Processing: response_generated=True
  ✓ Continual Learning: updates_applied=5
```

### ⚖️ Ethical Evaluation

Detailed breakdown of ethical principles and scoring:
```
⚖️  Ethical Evaluation

┌────────────────────────────────┬───────┬──────────────────────────┐
│ Principle                      │ Score │ Assessment               │
├────────────────────────────────┼───────┼──────────────────────────┤
│ Non-maleficence (avoid harm)   │  0.85 │ ████████████████ ✓       │
│ Beneficence (do good)          │  0.82 │ ████████████████ ✓       │
│ Autonomy (respect choice)      │  0.88 │ █████████████████ ✓      │
│ Justice (fairness)             │  0.90 │ █████████████████ ✓      │
│ Transparency                   │  0.78 │ ███████████████ ✓        │
└────────────────────────────────┴───────┴──────────────────────────┘

✓ Query Approved
Overall Ethical Score: 0.85/1.00
```

### 🌊 Wave Function Visualization

Display Extended Cognitive Wave Function (ECWF) state:
```
🌊 Extended Cognitive Wave Function (ECWF)

  Cognitive State
  ┌──────────────────────────┬───────────┬──────────────────┐
  │ Dimension                │ Amplitude │ Visualization    │
  ├──────────────────────────┼───────────┼──────────────────┤
  │ Situational awareness    │     0.654 │ ▓▓▓▓▓▓▓▓▓░░░░░░  │
  │ Consequence prediction   │     0.823 │ ▓▓▓▓▓▓▓▓▓▓▓▓░░░  │
  │ Pattern recognition      │     0.789 │ ▓▓▓▓▓▓▓▓▓▓▓░░░░  │
  │ Past experience          │     0.712 │ ▓▓▓▓▓▓▓▓▓▓░░░░░  │
  │ Decision complexity      │     0.845 │ ▓▓▓▓▓▓▓▓▓▓▓▓░░░  │
  └──────────────────────────┴───────────┴──────────────────┘

  Wave Function Entropy: 0.523 (uncertainty measure)
```

### 💾 Memory System Updates

Shows how the memory system evolves:
```
💾 Memory System Updates

┌──────────────── Memory Web (NetworkX) ────────────────┐
│ • Added 7 new concepts                                │
│ • Formed 18 new connections                           │
│ • Updated 12 existing nodes                           │
│ • Graph size: 287 nodes, 692 edges                    │
└───────────────────────────────────────────────────────┘

┌───────────────────── ECWF Core ───────────────────────┐
│ • Wave function updated                               │
│ • 5 facets modified                                   │
│ • Entropy: 0.523                                      │
│ • Glass transition temp (T_g): 0.51                   │
└───────────────────────────────────────────────────────┘

┌────────────────── Memory-ECWF Bridge ─────────────────┐
│ • Symbolic → Subsymbolic: 9 translations              │
│ • Subsymbolic → Symbolic: 6 translations              │
│ • Bidirectional sync completed                        │
└───────────────────────────────────────────────────────┘
```

### 📊 System Metrics

Real-time system performance indicators:
```
📊 System Metrics

┌────────────────────────────────┬───────────┬────────┐
│ Metric                         │     Value │ Status │
├────────────────────────────────┼───────────┼────────┤
│ Total Interactions             │       487 │ ✓      │
│ Ethical Evaluations            │       234 │ ✓      │
│ Decisions Made                 │       412 │ ✓      │
│ Glass Transition Temp (T_g)    │      0.49 │ ✓      │
│ System Entropy                 │      0.45 │ ✓      │
│ Average Processing Time        │     1.23s │ ✓      │
│ Memory Graph Size              │ 312 nodes │ ✓      │
│ Wave Function Facets           │         7 │ ✓      │
└────────────────────────────────┴───────────┴────────┘
```

---

## 🎮 Interactive Menu

The main menu provides easy access to all features:

```
═══ Main Menu ═══

1. 🏗️  Show Architecture Overview
2. 🔄 Visualize Processing Pipeline
3. 🔍 Process Custom Query
4. ⚖️  Show Ethical Evaluation Demo
5. 🌊 Display Wave Function State
6. 💾 Show Memory System Updates
7. 📊 Display System Metrics
8. 🎭 Run Complete Showcase
9. ❌ Exit

Enter your choice (1-9):
```

---

## 💡 Use Cases

### For Developers
- **Understanding Architecture:** Visualize how components interact
- **Debugging:** See data flow through blocks
- **Learning:** Explore the cognitive architecture interactively

### For Researchers
- **Demonstrations:** Show the system to collaborators
- **Documentation:** Generate visual examples for papers
- **Teaching:** Explain cognitive architectures to students

### For Presentations
- **Live Demos:** Impressive visual output for audiences
- **Showcase Mode:** Automated walkthrough of all features
- **Custom Queries:** Process audience questions in real-time

---

## 🎨 Visual Features

### Colors and Symbols

The demo uses colors and symbols to enhance understanding:

- 🔵 **Blue/Cyan:** System components and processing
- 🟢 **Green:** Success and completion
- 🟡 **Yellow:** Warnings and metrics
- 🟣 **Magenta:** Ethical evaluation and governance
- 🔴 **Red:** Errors (rare in demo mode)

**Symbols:**
- ✓ Success/Approval
- ⚠ Warning
- ✗ Error/Failure
- 🏗️ Architecture
- 🔄 Processing
- ⚖️ Ethics
- 🌊 Wave Functions
- 💾 Memory
- 📊 Metrics
- 👑 King Oversight

### Progress Indicators

Real-time progress bars show processing through blocks:
```
Sensory Input          ━━━━━━━━━━━━━━━━━━━━ 100%
Pattern Recognition    ━━━━━━━━━━━━━━━━━━━━ 100%
Memory Storage         ━━━━━━━━━━━━━━━━━━━━ 100%
```

---

## 🔧 Technical Details

### Implementation

The demo is a **simulation** that showcases the architecture without requiring trained models:

- **Simulated Processing:** Random but realistic outputs
- **Visual Feedback:** Progress bars, colors, symbols
- **Interactive:** User-driven exploration
- **Educational:** Shows structure and flow

### Why Simulation?

The demo works with untrained weights because:
1. **Architectural Demonstration:** Shows the system structure
2. **No Dependencies:** Doesn't require large models
3. **Fast Execution:** Instant feedback
4. **Educational Focus:** Teaches concepts over performance

### Dependencies

**Required:**
- Python 3.8+

**Recommended:**
- `rich` - Beautiful terminal output (highly recommended)

**Optional:**
- None - demo is self-contained

### Installation

```bash
# Minimum
python demos/interactive_demo.py --no-color

# Recommended (with rich)
pip install rich
python demos/interactive_demo.py
```

---

## 📝 Examples

### Example 1: Quick Query Demo

```bash
python demos/interactive_demo.py --query "What is consciousness?"
```

Shows complete processing of a philosophical query with ethical evaluation.

### Example 2: Complete Showcase

```bash
python demos/interactive_demo.py --showcase
```

Automated walkthrough perfect for presentations (takes ~30 seconds).

### Example 3: Interactive Exploration

```bash
python demos/interactive_demo.py
```

Choose option 3, then enter custom queries to explore different processing patterns.

### Example 4: Export for Documentation

```bash
python demos/interactive_demo.py --query "Your query" > demo_output.txt
```

Capture output for documentation or reports.

---

## 🎯 Tips for Best Experience

1. **Use a Modern Terminal:**
   - Supports Unicode and colors
   - Wide window (80+ characters recommended)
   - Good font with box-drawing characters

2. **Install Rich Library:**
   ```bash
   pip install rich
   ```
   Makes output significantly more impressive.

3. **Try Different Queries:**
   - Simple: "What is AI?"
   - Ethical: "Should AI make life-or-death decisions?"
   - Complex: "How do neural networks learn?"
   - Philosophical: "What is consciousness?"

4. **Use Showcase Mode for Presentations:**
   ```bash
   python demos/interactive_demo.py --showcase
   ```

---

## 🚀 Future Enhancements

Planned features for future versions:

- [ ] Save/load demo sessions
- [ ] Export visualizations as images
- [ ] Interactive graph visualization
- [ ] Real model integration option
- [ ] Custom color themes
- [ ] Animation speed control
- [ ] Detailed tooltips and help
- [ ] Comparison mode (before/after)

---

## 🐛 Troubleshooting

**Issue: Colors not showing**
- Solution: Install `rich` library or use `--no-color` flag

**Issue: Box characters look wrong**
- Solution: Use a terminal with Unicode support (most modern terminals)

**Issue: Output too wide**
- Solution: Maximize terminal window or use smaller font

**Issue: Demo runs too fast**
- Solution: Animation timing is intentional, but you can pause at each step

---

## 📚 Related Resources

- **Main README:** `../README.md` - Project overview
- **Architecture Docs:** `../docs/architecture.md` - Detailed architecture
- **API Reference:** `../docs/api.md` - API documentation
- **Testing Guide:** `../TESTING.md` - How to run tests

---

## 🤝 Contributing

Want to enhance the demo? Ideas for contributions:

- New visualization modes
- Additional query examples
- Performance optimizations
- Better animations
- Export features
- Documentation improvements

See main `CONTRIBUTING.md` for guidelines.

---

## 📄 License

MIT License - See `../LICENSE` for details.

---

**Created by:** Verdant-Minds Development Team
**Version:** 0.1.0
**Last Updated:** 2025-12-08
