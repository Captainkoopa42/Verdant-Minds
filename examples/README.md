# Verdant-Minds Examples

This directory contains example scripts demonstrating how to use the Verdant-Minds (Unified Synthetic Mind) cognitive architecture.

---

## Available Examples

### `basic_usage.py` - Comprehensive Basic Usage Guide

A complete tutorial covering all fundamental operations of the Unified Synthetic Mind system.

**What it demonstrates:**

1. **Basic Initialization** - Creating a UnifiedSyntheticMind instance with defaults
2. **Custom Configuration** - Initializing with custom parameters
3. **Simple Query Processing** - Getting responses to text queries
4. **CognitiveChunk Examination** - Accessing and inspecting the data structure
5. **Memory Web Access** - Querying concepts and exploring semantic relationships
6. **Wave Function Inspection** - Examining ECWF state and dimensions
7. **Ethical Evaluation** - Accessing Ethics King assessments and principle scores
8. **System Metrics** - Monitoring performance and activity statistics
9. **Save and Load** - Persisting and restoring system state

**How to run:**

```bash
# From project root
python examples/basic_usage.py

# Or make it executable and run directly
chmod +x examples/basic_usage.py
./examples/basic_usage.py
```

**Expected output:**
- Formatted output showing each example with clear section headers
- Demonstrates successful initialization and processing
- Shows actual data from CognitiveChunks, Memory Web, and ECWF
- Displays ethical evaluations and system metrics
- Works with the current codebase (no trained models required)

---

## Example Output Preview

```
======================================================================
  VERDANT-MINDS BASIC USAGE EXAMPLES
  Unified Synthetic Mind Cognitive Architecture
======================================================================

======================================================================
  Example 1: Basic Initialization
======================================================================
✓ UnifiedSyntheticMind initialized successfully!
  - Cognitive dimensions: 5
  - Ethical dimensions: 5
  - Memory Web nodes: 13
  - Memory Web edges: 14

======================================================================
  Example 2: Custom Configuration
======================================================================
✓ UnifiedSyntheticMind initialized with custom config!
  - Learning rate: 0.05
  - Decision threshold: 0.7
  - Ethical sensitivity: 0.6

... (and so on for all 9 examples)
```

---

## Understanding the Examples

### System Components Demonstrated

| Component | Example(s) | What You'll Learn |
|-----------|-----------|------------------|
| **UnifiedSystem** | 1, 2 | Initialization and configuration |
| **CognitiveChunk** | 4 | Data structure and section contents |
| **Memory Web** | 5 | Semantic graph queries and concept activation |
| **ECWF Core** | 6 | Wave function states and dimension meanings |
| **Ethics King** | 7 | Ethical evaluation and principle scoring |
| **Three Kings** | 8 | Governance layer activity metrics |
| **Full Pipeline** | 3, 4 | Complete processing from input to output |

### Code Patterns Shown

```python
# 1. Initialize the system
from usm import UnifiedSyntheticMind
mind = UnifiedSyntheticMind(seed=42)

# 2. Get a simple response
response = mind.get_response("What is AI?")

# 3. Access the CognitiveChunk
chunk = mind.process_input("How does AI work?")
memory_data = chunk.get_section_content("memory_section")

# 4. Query the Memory Web
concepts = mind.memory_web.activate_concepts(
    initial_concepts=["Artificial Intelligence"],
    num_steps=2
)

# 5. Examine wave function
state = mind.ecwf_core.get_state_summary()
print(f"Cognitive entropy: {state['cognitive_entropy']}")

# 6. Check ethical evaluation
ethics_data = chunk.get_section_content("ethics_king_section")
status = ethics_data['evaluation']['status']

# 7. Get system metrics
metrics = mind.get_system_metrics()
print(f"Total interactions: {metrics['total_interactions']}")

# 8. Save/load state
mind.save_system_state("state.pkl")
restored = UnifiedSyntheticMind.load_system_state("state.pkl")
```

---

## Creating Your Own Examples

### Template Structure

```python
#!/usr/bin/env python3
"""Your example description."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind

def main():
    # Initialize system
    mind = UnifiedSyntheticMind(seed=42)

    # Your code here
    # ...

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Tips for New Examples

1. **Start Simple**: Begin with basic initialization and work up to complex interactions
2. **Use Clear Comments**: Explain what each step does and why
3. **Show Output**: Print results so users can see what's happening
4. **Handle Errors**: Use try-except blocks for robust examples
5. **Clean Up**: Remove temporary files created during examples

---

## Requirements

These examples work with:
- Python 3.8+
- Verdant-Minds installed (via `pip install -e .`)
- No trained models or additional data required

The examples use:
- Template-based response generation
- Initialized knowledge base (ethical principles, basic concepts)
- Default configuration values

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'usm'`

**Solution**:
```bash
# Install Verdant-Minds in development mode
pip install -e .

# Or add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/Verdant-Minds"
```

### Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'numpy'` (or other packages)

**Solution**:
```bash
# Install all dependencies
pip install -r requirements.txt
```

### Slow Performance

**Note**: Some operations (especially graph queries and wave function calculations) can be slow on the first run. This is normal for the prototype implementation.

---

## Next Steps

After running these examples:

1. **Modify the Examples**: Change queries, adjust parameters, experiment!
2. **Explore the Source**: Look at `Verdant Source Codes/src/` to understand implementation
3. **Read the Docs**: Check `docs/architecture.md` for system design details
4. **Try Integration Tests**: Run `mind.run_integration_tests()` to see comprehensive validation
5. **Build Your Own**: Create applications using the Verdant-Minds API

---

## Contributing Examples

Have a great example to share? Contributions are welcome!

1. Create your example in `examples/your_example.py`
2. Add clear docstrings and comments
3. Update this README with a description
4. Test thoroughly
5. Submit a pull request

---

## Additional Resources

- **Main README**: `../README.md` - Project overview and features
- **Installation Guide**: `../INSTALL.md` - Detailed setup instructions
- **Architecture Docs**: `../docs/architecture.md` - System design diagrams
- **Source Code**: `../Verdant Source Codes/src/` - Implementation details

---

## License

These examples are part of the Verdant-Minds project and are licensed under the MIT License.
See `../LICENSE` for details.
