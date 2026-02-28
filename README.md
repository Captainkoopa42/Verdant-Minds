# Verdant-Minds

<div align="center">

**A thermodynamic cognitive architecture with active governance, coherence geometry, and cultivation tooling**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: ~95% Complete](https://img.shields.io/badge/Status-~95%25%20Complete-brightgreen.svg)]()

</div>

Verdant-Minds is a **working thermodynamic cognitive architecture**. It is not positioned here as a toy prototype: the full core loop, governance, memory-wave bridge, persistence stack, telemetry path, and LLM cultivation loop are implemented and runnable in this repository.

## Current state

- **Completion:** ~95% complete at the architecture/infrastructure level.
- **Processing core:** operational end-to-end across all core cognitive stages.
- **Cultivation:** LLM-in-the-loop cultivation is operational.
- **Persistence:** session state, governance state, and learning traces persist across runs.

## What Verdant is

Verdant combines symbolic memory, wave-based cognition, and thermodynamic phase control into one loop:

1. **Nine-block pipeline** for perception → interpretation → memory → reasoning → ethics → action → language → learning.
2. **Three Kings governance** (Data King, Forefront King, Ethics King) for coordinated decision authority.
3. **ECWF (Extended Cognitive Wave Function)** as the system’s continuous cognitive state representation.
4. **MemoryWeb with pconnect dynamics** for concept topology and weighted memory interaction.
5. **Bidirectional Memory–ECWF bridge** for symbol↔wave translation and emergent concept formation.

## Thermodynamic processing governs every cycle

Verdant uses **glass-transition style regulation (`T_g`)** as a first-class control signal:

- **Rigid** phase: stabilization, consistency, constraint-sensitive behavior.
- **Flexible** phase: balanced exploration/exploitation.
- **Chaotic** phase: broader exploratory dynamics with grounding checks.

These phases directly influence processing and action-selection behavior, not just reporting.

## Coherence geometry and contradiction handling

Every cycle includes coherence self-monitoring signals such as:

- **H¹ cohomology-informed coherence checks**
- **Housed contradiction index**
- **Triangle validity signals**

These are fed back into governance each cycle, so contradiction/coherence metrics influence decision dynamics in-loop.

## Ethics as geometry (Ethomorphism)

Ethics in Verdant is embedded in wave-function geometry via **Ethomorphism**, rather than added as an external post-hoc constraint layer.

## LLM cultivation loop

`scripts/verdant_llm_cultivator.py` provides a live cultivation loop where an external LLM reads telemetry and injects one next input per cycle. The loop now includes explicit cultivation context (recent domain usage, FCE trend slices, growth windows, and memory growth context) to reduce semantic repetition and improve emergence conditions.

## Run Verdant

```bash
git clone <repo-url>
cd Verdant-Minds
pip install -r requirements.txt
python scripts/verdant_repl.py
```

## Core scripts

- `scripts/verdant_repl.py` — interactive loop for direct engagement.
- `scripts/verdant_telemetry.py` — telemetry inspection/reporting.
- `scripts/kernel_loop.py --demo` — demo trajectory for the thermodynamic kernel loop.
- `scripts/verdant_llm_cultivator.py` — Anthropic-driven cultivation loop.

## Theoretical foundation

Verdant’s conceptual basis includes:

- **Soul Equation**
- **Verdant Hierarchy**
- **Ethomorphism**

Whitepaper materials in-repo:

- `Verdant Outline/Verdant Paper/I. EXECUTIVE SUMMARY.txt`
- `Verdant Outline/Verdant Paper/II. THEORETICAL FOUNDATIONS.txt`
- `Verdant Outline/Verdant Paper/III. ARCHITECTURAL DESIGN.txt`

---

## Legacy README content (retained)

The original README sections are preserved below for historical context and detailed background.

# Verdant-Minds

<div align="center">

**A Quantum-Inspired Cognitive Architecture for Artificial General Intelligence**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

*Thermodynamic Knowledge Representation • Emergent Reasoning • Ethical AI*

[Installation](#installation) •
[Quick Start](#quick-start) •
[Architecture](#architecture) •
[Documentation](INSTALL.md) •
[Contributing](#contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [What Makes This Different](#what-makes-this-different)
- [Key Innovations](#key-innovations)
- [Architecture](#architecture)
  - [Extended Cognitive Wave Function (ECWF)](#extended-cognitive-wave-function-ecwf)
  - [Nine-Block Cognitive System](#nine-block-cognitive-system)
  - [Three Kings Governance](#three-kings-governance)
  - [Memory Web & ECWF Bridge](#memory-web--ecwf-bridge)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Current Status](#current-status)
- [Project Structure](#project-structure)
- [Research Background](#research-background)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)
- [Contact](#contact)

---

## 🧠 Overview

**Verdant-Minds** (Unified Synthetic Mind) is a pioneering research project that explores a novel approach to artificial general intelligence by integrating concepts from quantum physics, thermodynamics, cognitive science, and ethical philosophy into a unified computational framework.

Unlike traditional neural networks that rely purely on statistical pattern matching, this system incorporates:
- **Quantum-inspired wave function representations** of cognitive states
- **Thermodynamic principles** (glass transition temperature) for adaptive reasoning
- **Graph-based semantic memory** with emergent conceptual clustering
- **Multi-layer ethical governance** embedded in the system's mathematical substrate
- **Modular cognitive blocks** inspired by human information processing

The goal is to create an AI system capable of:
- General-purpose reasoning across diverse domains
- Contextual ethical decision-making
- Emergent understanding and concept formation
- Uncertainty-aware probabilistic reasoning
- Self-reflective learning and adaptation

> ⚠️ **Research Status**: This is an experimental research prototype in active development. It represents a theoretical exploration of alternative AI architectures rather than a production-ready system.

---

## 🌟 What Makes This Different

### Traditional AI vs. Verdant-Minds

| Aspect | Traditional Deep Learning | Verdant-Minds |
|--------|--------------------------|---------------|
| **Knowledge Representation** | Distributed weights in neural networks | Wave functions + semantic graphs |
| **Reasoning Style** | Pattern matching from training data | Probabilistic state evolution + symbolic inference |
| **Ethical Framework** | Post-hoc alignment techniques | Embedded quantum ethical field operator |
| **Cognitive Model** | End-to-end black box | Modular blocks with explicit cognitive roles |
| **Uncertainty** | Confidence scores | Wave function superposition states |
| **Adaptability** | Requires retraining | Glass transition temperature framework |

### Core Philosophy

This project is built on several key hypotheses:

1. **Cognition as Wave Function**: Mental states can be represented as quantum-inspired wave functions that evolve probabilistically
2. **Thermodynamic Cognition**: Cognitive flexibility can be modeled using phase transitions (rigid ↔ fluid processing)
3. **Embedded Ethics**: Ethical reasoning should be part of the mathematical substrate, not an add-on
4. **Emergent Understanding**: True comprehension arises from graph dynamics and wave function interactions
5. **Governance by Committee**: Multiple specialized "kings" provide checks and balances on system behavior

---

## 🚀 Key Innovations

### 1. **Extended Cognitive Wave Function (ECWF)**
A quantum-inspired framework where cognitive states exist as wave functions in a multi-dimensional space:
- **Cognitive dimensions**: situational awareness, consequence prediction, pattern recognition, past experience, decision complexity
- **Ethical dimensions**: non-maleficence, beneficence, autonomy, justice, transparency
- **Wave properties**: amplitude, phase, entropy, coherence
- Enables superposition of multiple hypotheses and probabilistic reasoning

### 2. **Glass Transition Temperature (T_g) Framework**
Adaptive processing inspired by thermodynamic phase transitions:
- **Low T_g**: Rigid, convergent, rule-based processing (like solid glass)
- **High T_g**: Fluid, divergent, creative processing (like liquid)
- Automatically adjusts based on:
  - Computational complexity
  - Environmental entropy (ambiguity)
  - System entropy (internal uncertainty)

### 3. **Memory-ECWF Bridge**
Bidirectional translation between symbolic and subsymbolic representations:
- **Memory Web**: NetworkX-based semantic graph with concepts as nodes
- **ECWF**: Continuous wave function representation
- **Bridge**: Maps concepts to wave dimensions and vice versa
- Enables both logical reasoning and intuitive pattern recognition

### 4. **Three Kings Governance**
A checks-and-balances system inspired by political philosophy:
- **Data King**: Ensures information quality, validates inputs, detects anomalies
- **Forefront King**: Executive function, action selection, goal prioritization
- **Ethics King**: Evaluates moral implications, enforces ethical constraints
- All three must coordinate for critical decisions

### 5. **Quantum Ethical Field Operator**
Ethics embedded in mathematical formalism:
- Operates on wave functions to enforce ethical constraints
- Context-sensitive moral reasoning through dimensional projections
- Transparent ethical evaluations with principle-based scoring

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input / Environment                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Nine-Block Cognitive System                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Sensory    │→ │   Pattern    │→ │   Memory     │      │
│  │    Input     │  │ Recognition  │  │   Storage    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                  ↓                  ↓              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Internal   │→ │  Reasoning & │→ │   Ethics &   │      │
│  │Communication │  │   Planning   │  │    Values    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                  ↓                  ↓              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Action    │→ │   Language   │→ │  Continual   │      │
│  │  Selection   │  │  Processing  │  │   Learning   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Three Kings Governance Layer                   │
│  ┌───────────┐      ┌───────────┐      ┌───────────┐       │
│  │   Data    │ ←──→ │ Forefront │ ←──→ │  Ethics   │       │
│  │   King    │      │   King    │      │   King    │       │
│  └───────────┘      └───────────┘      └───────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Memory Web ←→ ECWF Bridge                       │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │   Semantic Graph     │ ↔  │  Wave Function       │      │
│  │   (NetworkX)         │    │  (NumPy Arrays)      │      │
│  │  - Concepts/Nodes    │    │  - Cognitive Dims    │      │
│  │  - Relations/Edges   │    │  - Ethical Dims      │      │
│  │  - Communities       │    │  - Phase/Entropy     │      │
│  └──────────────────────┘    └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                   System Output
```

### Extended Cognitive Wave Function (ECWF)

The ECWF represents cognitive states as wave functions in a high-dimensional space:

**Mathematical Formulation:**
```
Ψ(c, e, t) = A(c, e, t) · exp(iφ(c, e, t))

where:
  c = cognitive dimensions (5D vector)
  e = ethical dimensions (5D vector)
  t = time
  A = amplitude (importance/activation)
  φ = phase (temporal relationships)
```

**Properties:**
- **Superposition**: Multiple cognitive states can coexist
- **Entanglement**: Cognitive and ethical dimensions influence each other
- **Collapse**: Measurement (decision-making) collapses to specific state
- **Evolution**: Unitary operators evolve the wave function over time

**Cognitive Dimensions:**
1. Situational awareness
2. Consequence prediction
3. Pattern recognition
4. Past experience
5. Decision complexity

**Ethical Dimensions:**
1. Non-maleficence (avoid harm)
2. Beneficence (do good)
3. Autonomy (respect choice)
4. Justice (fairness)
5. Transparency (explainability)

### Nine-Block Cognitive System

Each block is a specialized processing module inspired by cognitive science:

1. **Sensory Input Block**
   - Parses input text into cognitive chunks
   - Extracts metadata (complexity, sentiment, ambiguity)
   - Creates initial wave function representation

2. **Pattern Recognition Block**
   - Identifies linguistic patterns
   - Extracts entities and relationships
   - Performs statistical analysis

3. **Memory Storage Block**
   - Interfaces with Memory Web
   - Retrieves relevant concepts
   - Stores new information

4. **Internal Communication Block**
   - Facilitates information flow between blocks
   - Aggregates partial results
   - Detects conflicts and inconsistencies

5. **Reasoning & Planning Block**
   - Deductive, inductive, and abductive inference
   - Multi-step planning
   - Hypothesis generation and evaluation

6. **Ethics & Values Block**
   - Applies Quantum Ethical Field Operator
   - Evaluates moral implications
   - Enforces ethical constraints

7. **Action Selection Block**
   - Chooses appropriate response type
   - Manages action confidence
   - Handles deferral and clarification

8. **Language Processing Block**
   - Generates natural language responses
   - Ensures coherence and relevance
   - Adapts style to context

9. **Continual Learning Block**
   - Updates system parameters
   - Learns from interactions
   - Adapts to new domains

### Three Kings Governance

A tripartite oversight system inspired by separation of powers:

#### Data King (Judicial Branch)
- **Role**: Information quality and validation
- **Functions**:
  - Verifies data integrity
  - Detects anomalies and outliers
  - Audits information sources
  - Flags inconsistencies
- **Influence**: Can block processing if data quality is poor

#### Forefront King (Executive Branch)
- **Role**: Goal-oriented action and execution
- **Functions**:
  - Prioritizes objectives
  - Selects high-level strategies
  - Manages resource allocation
  - Drives decision execution
- **Influence**: Determines final action selection

#### Ethics King (Legislative Branch)
- **Role**: Moral oversight and ethical alignment
- **Functions**:
  - Evaluates ethical implications
  - Enforces value constraints
  - Resolves moral dilemmas
  - Provides transparency
- **Influence**: Can veto unethical actions

**Coordination**: All three kings must reach consensus for critical decisions, providing a checks-and-balances system.

### Memory Web & ECWF Bridge

#### Memory Web
A graph-based semantic memory using NetworkX:
- **Nodes**: Concepts with stability scores
- **Edges**: Relationships with strengths
- **Communities**: Emergent conceptual clusters (Louvain algorithm)
- **Centrality**: Importance metrics for concepts

#### Bridge Functions
1. **Concept → Wave Mapping**
   - Active concepts amplify corresponding wave dimensions
   - Ethical concepts project onto ethical dimensions
   - Community structure influences wave coherence

2. **Wave → Concept Mapping**
   - High-amplitude dimensions activate related concepts
   - Wave entropy modulates concept activation
   - Phase relationships inform conceptual connections

---

## 💻 Installation

### Prerequisites

- **Python**: 3.8 or higher
- **OS**: Linux, macOS, or Windows
- **Memory**: 8GB RAM minimum (16GB+ recommended)
- **Optional**: CUDA-capable GPU for accelerated processing

### Quick Install

```bash
# Clone the repository
git clone https://github.com/captainkoopa42/Verdant-Minds.git
cd Verdant-Minds

# Install in development mode (recommended)
pip install -e .
```

### Alternative Installation Methods

```bash
# Standard installation
pip install .

# With development tools (testing, linting, profiling)
pip install -e ".[dev]"

# Manual dependency installation (legacy)
pip install -r requirements.txt
```

### GPU Support (Optional)

For GPU-accelerated deep learning (if using TensorFlow/PyTorch components):

```bash
# TensorFlow with CUDA
pip install tensorflow[and-cuda]>=2.13.0

# PyTorch with CUDA (see pytorch.org for specific version)
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Verify Installation

```bash
# Test import
python -c "from usm import UnifiedSyntheticMind; print('✓ Installation successful')"

# Run CLI
verdant-minds
```

For detailed installation instructions, troubleshooting, and platform-specific guidance, see **[INSTALL.md](INSTALL.md)**.

---

## 🚀 Quick Start

### Command Line Interface

After installation, launch the interactive CLI:

```bash
verdant-minds
# or
usm
# or
python -m usm
```

Example interaction:
```
Unified Synthetic Mind initialized. Type 'exit' to quit.
> What are the ethical implications of AI in healthcare?
Based on my understanding of Non-maleficence, Beneficence, Autonomy,
I would approach this by considering the relationships between these
elements and how they relate to your question about AI in healthcare...
> exit
```

### Python API

Use the system programmatically in your code:

```python
from usm import UnifiedSyntheticMind

# Initialize the cognitive system
mind = UnifiedSyntheticMind(
    seed=42,  # For reproducibility
    config={
        "cognitive_dimensions": 5,
        "ethical_dimensions": 5,
        "learning_rate": 0.05,
        "ethical_sensitivity": 0.6
    }
)

# Process a query
response = mind.get_response("Explain quantum computing")
print(response)

# Access system metrics
metrics = mind.get_system_metrics()
print(f"Total interactions: {metrics['total_interactions']}")
print(f"Glass transition temp: {metrics['glass_transition_temp']:.3f}")

# Initialize with domain knowledge
mind.initialize_knowledge(
    ethical_concepts=[
        ("Privacy", 0.9, {"description": "Data protection"}),
        ("Consent", 0.9, {"description": "Informed agreement"})
    ]
)

# Process with metadata
chunk = mind.process_input(
    "Should we use AI for surveillance?",
    metadata={"domain": "ethics", "urgency": "high"}
)

# Examine cognitive processing
wave_data = chunk.get_section_content("wave_function_section")
ethics_data = chunk.get_section_content("ethics_king_section")
print(f"Ethical status: {ethics_data['evaluation']['status']}")
```

### Advanced Usage

```python
# Access individual components
memory_web = mind.memory_web
ecwf_core = mind.ecwf_core
bridge = mind.memory_bridge

# Query the Memory Web
related_concepts = memory_web.activate_concepts(
    initial_concepts=["Artificial Intelligence"],
    num_steps=2,
    activation_threshold=0.3
)

# Examine wave function properties
wave_state = ecwf_core.get_state_summary()
print(f"Wave entropy: {wave_state['cognitive_entropy']:.3f}")
print(f"Ethical entropy: {wave_state['ethical_entropy']:.3f}")

# Run integration tests
test_results = mind.run_integration_tests()
print(f"Overall success: {test_results['overall_success']}")

# Save/load system state
mind.save_system_state("mind_state.pkl")
restored_mind = UnifiedSyntheticMind.load_system_state("mind_state.pkl")
```

---

## 📊 Current Status

### ✅ What Works

**Core Infrastructure:**
- ✓ Package installation via pip
- ✓ Console commands (`verdant-minds`, `usm`)
- ✓ Modular nine-block architecture
- ✓ Three Kings coordination layer
- ✓ Logging and error handling

**Memory & Knowledge:**
- ✓ NetworkX-based Memory Web
- ✓ Concept storage and retrieval
- ✓ Community detection (Louvain algorithm)
- ✓ Bidirectional Memory-ECWF bridge
- ✓ Knowledge base initialization

**Wave Function Processing:**
- ✓ ECWF state representation
- ✓ Cognitive and ethical dimensions
- ✓ Wave evolution operators
- ✓ Entropy calculations
- ✓ Quantum ethical field operator

**Cognitive Blocks:**
- ✓ All 9 blocks implemented
- ✓ Inter-block communication
- ✓ Processing pipeline
- ✓ Cognitive chunk data structure

**Governance:**
- ✓ Three Kings implementation
- ✓ Ethical evaluation framework
- ✓ Multi-king coordination
- ✓ Decision oversight

**Testing & Integration:**
- ✓ Integration test suite
- ✓ Performance metrics
- ✓ System visualization tools
- ✓ Block interaction tracking

### 🚧 Under Development

**Training & Learning:**
- ⚠️ Limited pre-trained knowledge base
- ⚠️ Continual learning mechanisms need training data
- ⚠️ Adaptive parameter tuning

**Language Generation:**
- ⚠️ Response generation is template-based
- ⚠️ No fine-tuned language models integrated
- ⚠️ Limited natural language understanding

**Deep Learning Integration:**
- ⚠️ TensorFlow/PyTorch components are placeholders
- ⚠️ Neural network blocks not yet trained
- ⚠️ Embedding models not integrated

**Scalability:**
- ⚠️ Performance optimization needed for large graphs
- ⚠️ Distributed processing not implemented
- ⚠️ Memory efficiency improvements needed

### 🎯 Research Goals

**Short Term:**
1. Integrate pre-trained language models for better NLU/NLG
2. Train initial knowledge base on curated datasets
3. Implement adaptive learning from user interactions
4. Add comprehensive unit tests

**Medium Term:**
1. Develop custom neural architectures for blocks
2. Implement distributed processing for scalability
3. Create benchmark tasks for evaluation
4. Publish research findings

**Long Term:**
1. Demonstrate emergent reasoning capabilities
2. Validate ethical governance mechanisms
3. Explore consciousness-like properties
4. Release trained models (if applicable)

### ⚠️ Known Limitations

- **No Pre-trained Models**: The system doesn't come with pre-trained weights; responses are based on template logic and initialized knowledge
- **Limited NLU**: Natural language understanding relies on simple pattern matching, not deep semantic comprehension
- **Computational Cost**: ECWF operations and graph processing can be slow for large-scale problems
- **Research Prototype**: This is experimental software, not production-ready
- **Requires Training**: Most cognitive blocks need domain-specific training to be effective

---

## 📁 Project Structure

```
Verdant-Minds/
│
├── usm/                          # Main package entry point
│   ├── __init__.py              # Exports UnifiedSyntheticMind
│   └── __main__.py              # CLI entry point
│
├── Verdant Source Codes/src/    # Core cognitive architecture
│   ├── core/                    # System orchestration
│   │   ├── system.py           # UnifiedSystem class (main)
│   │   ├── cognitive_chunk.py  # Data structure for processing
│   │   └── system_learning.py  # Learning mechanisms
│   │
│   ├── memory/                  # Memory systems
│   │   ├── memory_web.py       # NetworkX semantic graph
│   │   ├── ecwf_core.py        # Wave function representation
│   │   └── memory_ecwf_bridge.py # Symbolic ↔ subsymbolic
│   │
│   ├── blocks/                  # Nine cognitive blocks
│   │   ├── base_block.py       # Base class for all blocks
│   │   ├── sensory_input_block.py
│   │   ├── pattern_recognition_block.py
│   │   ├── memory_storage_block.py
│   │   ├── internal_communication_block.py
│   │   ├── reasoning_planning_block.py
│   │   ├── ethics_values_block.py
│   │   ├── action_selection_block.py
│   │   ├── language_processing_block.py
│   │   └── continual_learning_block.py
│   │
│   ├── kings/                   # Governance layer
│   │   ├── base_king.py        # Base class for kings
│   │   ├── data_king.py        # Information quality
│   │   ├── forefront_king.py   # Executive function
│   │   ├── ethics_king.py      # Ethical oversight
│   │   └── three_kings_layer.py # Coordination
│   │
│   ├── integration/             # Testing & validation
│   │   ├── integration_tools.py
│   │   ├── IntegrationTestSuite.py
│   │   ├── BlockIntegrationManager.py
│   │   └── SystemIntegrationFramework.py
│   │
│   ├── utils/                   # Utilities
│   │   └── logging_utils.py    # Logging configuration
│   │
│   ├── auth/                    # Authentication (if needed)
│   ├── config/                  # Configuration
│   └── services/                # External services
│
├── tests/                       # Test suite (TBD)
├── docs/                        # Documentation (TBD)
│
├── requirements.txt             # Core dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.py                     # Setuptools configuration
├── pyproject.toml              # Modern packaging config
├── setup.cfg                    # Additional setup config
├── MANIFEST.in                  # Distribution files spec
│
├── README.md                    # This file
├── INSTALL.md                   # Installation guide
├── LICENSE                      # MIT License
├── VERDANT_LICENSE_APPENDIX.md  # Additional license info
└── .gitignore                   # Git ignore rules
```

### Key Files

- **`usm/__init__.py`**: Main entry point, sets up Python path
- **`core/system.py`**: `UnifiedSystem` class that orchestrates everything
- **`memory/ecwf_core.py`**: ECWF wave function mathematics
- **`memory/memory_web.py`**: NetworkX semantic graph
- **`kings/three_kings_layer.py`**: Governance coordination

---

## 🔬 Research Background

### Theoretical Foundations

This project draws inspiration from multiple research domains:

**Quantum Cognition:**
- Busemeyer & Bruza (2012): "Quantum Models of Cognition and Decision"
- Pothos & Busemeyer (2013): Quantum probability in psychology
- Aerts et al. (2013): Quantum structure in cognition

**Thermodynamic Cognition:**
- Friston (2010): Free energy principle
- Oizumi et al. (2014): Integrated information theory
- Sengupta et al. (2013): Information and efficiency in neural codes

**Ethical AI:**
- Bostrom (2014): Superintelligence and value alignment
- Russell (2019): Human Compatible AI
- Floridi & Cowls (2019): AI4People ethical framework

**Cognitive Architecture:**
- Anderson et al. (2004): ACT-R cognitive architecture
- Laird (2012): Soar cognitive architecture
- Franklin & Graesser (2001): LIDA model

**Graph-Based Knowledge:**
- Bordes et al. (2013): Knowledge graph embeddings
- Nickel et al. (2016): Review of knowledge graph completion
- Hamilton et al. (2017): Graph representation learning

### Novel Contributions

1. **Quantum-Thermodynamic Integration**: Combining quantum-inspired representations with thermodynamic phase transitions for adaptive cognition

2. **Embedded Ethical Substrate**: Mathematical formalization of ethics as an integral part of cognitive processing, not a post-hoc filter

3. **Multi-King Governance**: Separation of powers applied to AI decision-making

4. **Memory-Wave Duality**: Bidirectional bridge between symbolic and subsymbolic representations

5. **Glass Transition Framework**: Novel approach to modeling cognitive flexibility

---

## 🤝 Contributing

We welcome contributions from the AI research community! This is an experimental project exploring alternative approaches to AGI.

### How to Contribute

1. **Report Issues**: Found a bug? [Open an issue](https://github.com/captainkoopa42/Verdant-Minds/issues)

2. **Propose Features**: Have an idea? Start a discussion in issues

3. **Submit Code**:
   ```bash
   # Fork the repository
   git clone https://github.com/YOUR_USERNAME/Verdant-Minds.git
   cd Verdant-Minds

   # Create a feature branch
   git checkout -b feature/your-feature-name

   # Make changes and commit
   git add .
   git commit -m "Add: your feature description"

   # Push and create PR
   git push origin feature/your-feature-name
   ```

4. **Improve Documentation**: Help clarify concepts and add examples

5. **Conduct Experiments**: Test the architecture on different tasks

### Development Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest

# Check code style
black --check .
flake8 .

# Type checking
mypy usm/
```

### Areas of Interest

We're particularly interested in contributions related to:

- **Knowledge Base Creation**: Curated datasets for initialization
- **Benchmark Tasks**: Evaluation scenarios for cognitive capabilities
- **Neural Integration**: Connecting pre-trained models to blocks
- **Performance Optimization**: Making the system faster and more scalable
- **Ethical Scenarios**: Test cases for ethical reasoning
- **Visualization**: Tools for understanding system behavior
- **Documentation**: Tutorials, examples, and explanations

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Document classes and functions with docstrings
- Keep functions focused and modular
- Write tests for new functionality (when test framework is ready)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

Additional information: [VERDANT_LICENSE_APPENDIX.md](VERDANT_LICENSE_APPENDIX.md)

### Key Points

- ✓ Free for academic and commercial use
- ✓ Modification and distribution allowed
- ✓ Attribution required
- ✗ No warranty provided

---

## 📚 Citation

If you use this work in your research, please cite:

```bibtex
@software{verdant_minds_2025,
  title={Verdant-Minds: A Quantum-Inspired Cognitive Architecture for AGI},
  author={captainkoopa42},
  year={2025},
  url={https://github.com/captainkoopa42/Verdant-Minds},
  note={Experimental research prototype exploring thermodynamic knowledge
        representation and embedded ethical reasoning}
}
```

---

## 📬 Contact

**Project Maintainer**: captainkoopa42
**Email**: adamswilliam905@gmail.com
**GitHub**: [@captainkoopa42](https://github.com/captainkoopa42)

### Get Involved

- 🐛 **Issues**: [Report bugs or request features](https://github.com/captainkoopa42/Verdant-Minds/issues)
- 💬 **Discussions**: Join the conversation (discussions TBD)
- 📧 **Email**: For research collaboration or questions

---

## 🙏 Acknowledgements

This project stands on the shoulders of giants from multiple disciplines:

- **Quantum Physics**: For inspiring alternative computational paradigms
- **Cognitive Science**: For insights into human information processing
- **Complex Systems Theory**: For understanding emergence and self-organization
- **Philosophy of Mind**: For grappling with consciousness and intentionality
- **AI Ethics**: For frameworks on responsible AI development
- **Open Source Community**: For tools like NumPy, NetworkX, PyTorch, TensorFlow

Special thanks to researchers who've explored quantum cognition, thermodynamic computation, and cognitive architectures.

---

## ⚠️ Disclaimer

**This is experimental research software under active development.**

- Not intended for production use
- No guarantees of correctness or safety
- Responses are based on limited knowledge and simple logic
- Ethical reasoning is theoretical and not validated
- Use for research and educational purposes only

---

<div align="center">

**Verdant-Minds** • *Exploring the frontiers of artificial cognition*

⭐ Star this repo if you find it interesting!

[🏠 Home](https://github.com/captainkoopa42/Verdant-Minds) •
[📖 Docs](INSTALL.md) •
[🐛 Issues](https://github.com/captainkoopa42/Verdant-Minds/issues)

</div>
