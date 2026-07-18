# Verdant-Minds Installation Guide

This guide provides detailed instructions for installing the Verdant-Minds (Unified Synthetic Mind) cognitive architecture.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Development Installation (Recommended)](#development-installation-recommended)
  - [Standard Installation](#standard-installation)
  - [From Source](#from-source)
- [GPU Support](#gpu-support)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: Version 3.10 or higher
- **Memory**: At least 8GB RAM (16GB+ recommended for large-scale operations)
- **Storage**: At least 5GB free disk space
- **Optional**: GPU with CUDA support for accelerated deep learning

### Python Environment

We strongly recommend using a virtual environment to avoid dependency conflicts:

```bash
# Using venv (built-in)
python -m venv verdant-env
source verdant-env/bin/activate  # On Windows: verdant-env\Scripts\activate

# Or using conda
conda create -n verdant python=3.11
conda activate verdant
```

---

## Supported Installation Path

Verdant V4 supports one local source-install path for submissions and reproducibility checks:

```bash
git clone https://github.com/captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ./cultivation -e ./ethomorphic -e ./verdant
```

This editable install keeps the runtime packages aligned with the checked-out branch and is the only supported installation path for the V4 submission surface.

---


## GPU Support

### TensorFlow GPU Support

For GPU acceleration with TensorFlow:

```bash
# Install with GPU support (requires CUDA)
pip install tensorflow[and-cuda]>=2.13.0
```

### PyTorch GPU Support

For GPU acceleration with PyTorch, visit [pytorch.org](https://pytorch.org) and follow platform-specific instructions.

Example for CUDA 11.8:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## Verifying Installation

### Test the Installation

After installation, verify that everything works:

```bash
# Check version
python -c "import verdant; print('Verdant-Minds installed successfully!')"

# Run the interactive CLI
verdant-minds
# or
verdant

# Run with Python module
python -m verdant
```

### Expected Output

When you run `verdant-minds` or `verdant`, you should see:

```
Unified Synthetic Mind initialized. Type 'exit' to quit.
>
```

### Run Tests (Development Installation Only)

If you installed with `[dev]` extras:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=verdant --cov-report=html

# Run specific test file
pytest tests/test_memory.py
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'numpy'` or similar

**Solution**:
```bash
pip install -r requirements.txt
```

#### 2. GPU Not Detected

**Problem**: TensorFlow or PyTorch not using GPU

**Solution**:
```bash
# Check CUDA availability
python -c "import tensorflow as tf; print('GPU Available:', tf.test.is_gpu_available())"
python -c "import torch; print('CUDA Available:', torch.cuda.is_available())"
```

#### 3. Memory Errors

**Problem**: Out of memory errors during initialization

**Solution**:
- Close other applications
- Reduce batch sizes in configuration
- Use a machine with more RAM

#### 4. Installation Conflicts

**Problem**: Dependency version conflicts

**Solution**:
```bash
# Create a fresh virtual environment
python -m venv fresh-env
source fresh-env/bin/activate
pip install --upgrade pip
pip install -e .
```

### Getting Help

If you encounter issues:

1. **Check the Issues**: Visit [GitHub Issues](https://github.com/captainkoopa42/Verdant-Minds/issues)
2. **Read the Documentation**: See [README.md](README.md)
3. **Contact**: Email adamswilliam905@gmail.com

---

## What's Installed

After installation, you'll have:

### Console Commands

- `verdant-minds` - Main CLI entry point
- `verdant` - Alias for verdant-minds

### Python Package

```python
from verdant.system import VerdantSystem as UnifiedSyntheticMind

# Initialize the cognitive system
mind = UnifiedSyntheticMind()

# Process input
response = mind.get_response("Tell me about ethical AI")
print(response)
```

### Package Structure

```
verdant-minds/
├── verdant/                      # Main package
│   ├── __init__.py
│   └── __main__.py          # CLI entry point
├── Verdant Source Codes/    # Core cognitive architecture
│   └── src/
│       ├── core/            # Core system components
│       ├── memory/          # Memory Web & ECWF
│       ├── blocks/          # 9-Block cognitive system
│       ├── kings/           # Three Kings governance
│       ├── integration/     # Testing & integration tools
│       └── utils/           # Utility functions
└── tests/                   # Test suite (dev only)
```

---

## Next Steps

After installation:

1. **Read the README**: Understand the architecture and features
2. **Try Examples**: Run the interactive CLI and experiment
3. **Configure**: Customize settings in your code
4. **Explore**: Check out the source code and examples
5. **Contribute**: See CONTRIBUTING.md (if available)

---

## Uninstalling

To remove Verdant-Minds:

```bash
pip uninstall verdant-minds
```

To also remove dependencies (be careful if you use them elsewhere):

```bash
pip uninstall verdant-minds numpy tensorflow torch networkx matplotlib PyJWT Werkzeug python-louvain
```

---

**Happy Exploring with Verdant-Minds!** 🧠✨
