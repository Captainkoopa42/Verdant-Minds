# Verdant-Minds API Reference

Complete API documentation for the Unified Synthetic Mind cognitive architecture.

**Version**: 0.1.0
**Python**: 3.8+

---

## Table of Contents

- [Core Classes](#core-classes)
  - [UnifiedSyntheticMind](#unifiedsyntheticmind)
  - [CognitiveChunk](#cognitivechunk)
- [Memory Systems](#memory-systems)
  - [MemoryWeb](#memoryweb)
  - [ECWFCore](#ecwfcore)
  - [MemoryECWFBridge](#memoryecwfbridge)
- [Cognitive Blocks](#cognitive-blocks)
  - [BaseBlock](#baseblock)
  - [Block Interfaces](#block-interfaces)
- [Governance Layer](#governance-layer)
  - [ThreeKingsLayer](#threekingslayer)
  - [Individual Kings](#individual-kings)
- [Configuration](#configuration)
  - [System Configuration](#system-configuration)
  - [Block Configuration](#block-configuration)
- [Utilities](#utilities)

---

## Core Classes

### UnifiedSyntheticMind

**Import**: `from usm import UnifiedSyntheticMind`

The main entry point and orchestrator for the Unified Synthetic Mind system. This class manages all components and provides the primary API for interacting with the cognitive architecture.

#### Constructor

```python
UnifiedSyntheticMind(seed: int = 42, config: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `seed` (int, optional): Random seed for reproducibility. Default: 42
- `config` (dict, optional): Configuration dictionary. See [Configuration](#configuration) for details.

**Returns:**
- `UnifiedSyntheticMind`: Initialized system instance

**Example:**
```python
from usm import UnifiedSyntheticMind

# Basic initialization
mind = UnifiedSyntheticMind()

# With custom config
mind = UnifiedSyntheticMind(
    seed=123,
    config={
        "cognitive_dimensions": 5,
        "ethical_dimensions": 5,
        "learning_rate": 0.05,
        "ethical_sensitivity": 0.6
    }
)
```

---

#### Methods

##### `get_response()`

Process input text and return a natural language response.

```python
get_response(
    input_text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str
```

**Parameters:**
- `input_text` (str): User input text to process
- `metadata` (dict, optional): Additional metadata about the input
  - `domain` (str): Domain of the query (e.g., "ethics", "technical")
  - `urgency` (str): Urgency level ("low", "medium", "high")
  - `context` (dict): Additional contextual information

**Returns:**
- `str`: Generated natural language response

**Example:**
```python
# Simple query
response = mind.get_response("What is artificial intelligence?")
print(response)

# With metadata
response = mind.get_response(
    "Should we use AI for surveillance?",
    metadata={"domain": "ethics", "urgency": "high"}
)
```

---

##### `process_input()`

Process input through the entire cognitive pipeline and return the CognitiveChunk.

```python
process_input(
    input_text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> CognitiveChunk
```

**Parameters:**
- `input_text` (str): User input text to process
- `metadata` (dict, optional): Additional metadata about the input

**Returns:**
- `CognitiveChunk`: Complete cognitive chunk with all sections populated

**Example:**
```python
chunk = mind.process_input("How does machine learning work?")

# Access specific sections
sensory_data = chunk.get_section_content("sensory_input_section")
memory_data = chunk.get_section_content("memory_section")
ethics_data = chunk.get_section_content("ethics_king_section")
```

---

##### `initialize_knowledge()`

Initialize the system with foundational knowledge concepts.

```python
initialize_knowledge(
    ethical_concepts: Optional[List[Tuple[str, float, Dict]]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `ethical_concepts` (list, optional): Additional ethical concepts to add
  - Each tuple: `(concept_name, stability, metadata)`
  - `concept_name` (str): Name of the concept
  - `stability` (float): Stability score (0.0-1.0)
  - `metadata` (dict): Additional information

**Returns:**
- `dict`: Initialization results
  - `concepts_added` (int): Total concepts added
  - `ethical_concepts` (int): Number of ethical concepts
  - `general_concepts` (int): Number of general concepts
  - `dimension_mappings` (int): Number of dimension mappings created

**Example:**
```python
results = mind.initialize_knowledge(
    ethical_concepts=[
        ("Data Privacy", 0.9, {"description": "Protection of personal data"}),
        ("Algorithmic Fairness", 0.85, {"description": "Bias-free algorithms"})
    ]
)

print(f"Added {results['concepts_added']} concepts")
print(f"Created {results['dimension_mappings']} mappings")
```

---

##### `get_system_metrics()`

Retrieve comprehensive system performance and state metrics.

```python
get_system_metrics() -> Dict[str, Any]
```

**Parameters:** None

**Returns:**
- `dict`: System metrics dictionary
  - `total_interactions` (int): Total processed interactions
  - `uptime` (float): System uptime in seconds
  - `interactions_per_hour` (float): Processing rate
  - `glass_transition_temp` (float): Current T_g value
  - `system_entropy` (float): Current system entropy
  - `ethical_evaluations` (int): Number of ethical evaluations
  - `decisions_made` (int): Total decisions made
  - `memory_metrics` (dict): Memory Web statistics
  - `bridge_metrics` (dict): Bridge operation metrics
  - `kings_metrics` (dict): Three Kings activity
  - `ecwf_state` (dict): ECWF state summary

**Example:**
```python
metrics = mind.get_system_metrics()

print(f"Total interactions: {metrics['total_interactions']}")
print(f"Glass transition temp: {metrics['glass_transition_temp']:.3f}")
print(f"Ethical evaluations: {metrics['ethical_evaluations']}")

# Memory metrics
mem = metrics['memory_metrics']
print(f"Concepts: {mem['num_thoughts']}, Connections: {mem['num_connections']}")

# King activity
kings = metrics['kings_metrics']
print(f"Data King: {kings['data_king']} interventions")
```

---

##### `save_system_state()`

Save the current system state to a file.

```python
save_system_state(filepath: str) -> bool
```

**Parameters:**
- `filepath` (str): Path where state will be saved (pickle format)

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
# Save state
success = mind.save_system_state("my_mind_state.pkl")
if success:
    print("State saved successfully")
```

---

##### `load_system_state()` (class method)

Load a system state from a file.

```python
@classmethod
load_system_state(cls, filepath: str) -> UnifiedSyntheticMind
```

**Parameters:**
- `filepath` (str): Path to saved state file

**Returns:**
- `UnifiedSyntheticMind`: Restored system instance

**Raises:**
- `Exception`: If loading fails

**Example:**
```python
# Load previously saved state
restored_mind = UnifiedSyntheticMind.load_system_state("my_mind_state.pkl")

# Verify restoration
metrics = restored_mind.get_system_metrics()
print(f"Restored {metrics['total_interactions']} interactions")
```

---

##### `run_integration_tests()`

Run comprehensive integration tests on the system.

```python
run_integration_tests() -> Dict[str, Any]
```

**Parameters:** None

**Returns:**
- `dict`: Test results
  - `overall_success` (bool): Whether all tests passed
  - `scenario_results` (dict): Results for each test scenario
  - `performance_metrics` (dict): Performance statistics

**Example:**
```python
results = mind.run_integration_tests()

if results['overall_success']:
    print("All integration tests passed!")
else:
    print("Some tests failed:")
    for name, result in results['scenario_results'].items():
        if not result['passed']:
            print(f"  - {name}: {result['error']}")
```

---

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `memory_web` | `MemoryWeb` | Semantic knowledge graph |
| `ecwf_core` | `ECWFCore` | Wave function system |
| `memory_bridge` | `MemoryECWFBridge` | Symbolic-subsymbolic bridge |
| `blocks` | `dict` | Dictionary of 9 cognitive blocks |
| `three_kings_layer` | `ThreeKingsLayer` | Governance system |
| `config` | `dict` | System configuration |
| `metrics` | `dict` | System metrics |
| `logger` | `Logger` | System logger |

**Example:**
```python
# Access components directly
memory_web = mind.memory_web
ecwf = mind.ecwf_core
bridge = mind.memory_bridge

# Access specific blocks
sensory_block = mind.blocks["SensoryInput"]
ethics_block = mind.blocks["EthicsValues"]
```

---

### CognitiveChunk

**Import**: `from core.cognitive_chunk import CognitiveChunk`

Container for cognitive processing data that flows through the pipeline. Each block adds its results to specific sections.

#### Constructor

```python
CognitiveChunk(chunk_id: Optional[str] = None)
```

**Parameters:**
- `chunk_id` (str, optional): Unique identifier. Auto-generated if None.

**Example:**
```python
from core.cognitive_chunk import CognitiveChunk

chunk = CognitiveChunk()
# Usually created automatically by the system
```

---

#### Methods

##### `update_section()`

Update or create a section in the chunk.

```python
update_section(section_name: str, content: Dict[str, Any]) -> None
```

**Parameters:**
- `section_name` (str): Name of the section
- `content` (dict): Content to store in the section

**Example:**
```python
chunk.update_section("my_section", {
    "key1": "value1",
    "key2": [1, 2, 3],
    "key3": {"nested": "data"}
})
```

---

##### `get_section_content()`

Retrieve the content of a specific section.

```python
get_section_content(section_name: str) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `section_name` (str): Name of the section to retrieve

**Returns:**
- `dict` or `None`: Section content if exists, None otherwise

**Example:**
```python
memory_data = chunk.get_section_content("memory_section")
if memory_data:
    concepts = memory_data.get("retrieved_concepts", [])
    print(f"Retrieved {len(concepts)} concepts")
```

---

##### `get_all_sections()`

Get all section names in the chunk.

```python
get_all_sections() -> List[str]
```

**Returns:**
- `list`: List of section names

**Example:**
```python
sections = chunk.get_all_sections()
print(f"Chunk has {len(sections)} sections:")
for section in sections:
    print(f"  - {section}")
```

---

#### Standard Sections

Each section is populated by a specific block during processing:

| Section Name | Populated By | Contains |
|--------------|--------------|----------|
| `sensory_input_section` | Sensory Input Block | Raw input, tokens, metadata, complexity |
| `pattern_recognition_section` | Pattern Recognition Block | Patterns, entities, linguistic features |
| `memory_section` | Memory Storage Block | Retrieved concepts, activation scores |
| `wave_function_section` | Memory Storage Block | ECWF state, amplitudes, phases, entropy |
| `internal_communication_section` | Internal Communication Block | Inter-block messages, aggregated data |
| `reasoning_section` | Reasoning & Planning Block | Inferences, hypotheses, plans |
| `ethics_king_section` | Ethics King | Ethical evaluation, principle scores |
| `action_selection_section` | Action Selection Block | Selected action, confidence, parameters |
| `language_processing_section` | Language Processing Block | Generated text, linguistic choices |
| `continual_learning_section` | Continual Learning Block | Learning updates, adjustments |
| `processing_metrics_section` | UnifiedSystem | Processing times, T_g, entropy |

**Example:**
```python
# Access all standard sections
chunk = mind.process_input("Explain quantum computing")

# Sensory data
sensory = chunk.get_section_content("sensory_input_section")
tokens = sensory.get("tokens", [])

# Memory retrieval
memory = chunk.get_section_content("memory_section")
concepts = memory.get("retrieved_concepts", [])

# Wave function
wave = chunk.get_section_content("wave_function_section")
entropy = wave.get("entropy", 0)

# Ethics
ethics = chunk.get_section_content("ethics_king_section")
status = ethics.get("evaluation", {}).get("status", "unknown")

# Action
action = chunk.get_section_content("action_selection_section")
selected = action.get("selected_action", "")
```

---

## Memory Systems

### MemoryWeb

**Import**: `from memory.memory_web import MemoryWeb`

Graph-based semantic memory using NetworkX. Stores concepts as nodes and relationships as edges.

#### Key Methods

##### `add_thought()`

Add a concept to the memory web.

```python
add_thought(
    thought_content: str,
    stability: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None
) -> None
```

**Parameters:**
- `thought_content` (str): The concept/thought to add
- `stability` (float): Stability score (0.0-1.0). Default: 0.5
- `metadata` (dict, optional): Additional information about the concept

**Example:**
```python
memory_web = mind.memory_web

memory_web.add_thought(
    "Neural Networks",
    stability=0.85,
    metadata={
        "description": "Machine learning architecture inspired by biological neurons",
        "domain": "AI"
    }
)
```

---

##### `connect_thoughts()`

Create a connection between two concepts.

```python
connect_thoughts(
    thought1: str,
    thought2: str,
    strength: float = 0.5
) -> None
```

**Parameters:**
- `thought1` (str): First concept
- `thought2` (str): Second concept
- `strength` (float): Connection strength (0.0-1.0). Default: 0.5

**Example:**
```python
memory_web.connect_thoughts(
    "Neural Networks",
    "Deep Learning",
    strength=0.9
)
```

---

##### `activate_concepts()`

Spread activation through the graph from initial concepts.

```python
activate_concepts(
    initial_concepts: List[str],
    num_steps: int = 3,
    activation_threshold: float = 0.1,
    decay_factor: float = 0.7
) -> Dict[str, float]
```

**Parameters:**
- `initial_concepts` (list): Starting concepts for activation
- `num_steps` (int): Number of spreading steps. Default: 3
- `activation_threshold` (float): Minimum activation to include. Default: 0.1
- `decay_factor` (float): Activation decay per step. Default: 0.7

**Returns:**
- `dict`: Mapping of concept → activation score

**Example:**
```python
activated = memory_web.activate_concepts(
    initial_concepts=["Artificial Intelligence", "Ethics"],
    num_steps=2,
    activation_threshold=0.3
)

for concept, activation in sorted(activated.items(),
                                   key=lambda x: x[1],
                                   reverse=True)[:10]:
    print(f"{concept}: {activation:.3f}")
```

---

##### `get_metrics()`

Get memory web statistics.

```python
get_metrics() -> Dict[str, Any]
```

**Returns:**
- `dict`: Metrics including node count, edge count, communities, etc.

**Example:**
```python
metrics = memory_web.get_metrics()
print(f"Concepts: {metrics['num_thoughts']}")
print(f"Connections: {metrics['num_connections']}")
print(f"Communities: {metrics['num_communities']}")
```

---

### ECWFCore

**Import**: `from memory.ecwf_core import ECWFCore`

Extended Cognitive Wave Function - quantum-inspired representation of cognitive states.

#### Key Methods

##### `get_state_summary()`

Get summary of current wave function state.

```python
get_state_summary() -> Dict[str, Any]
```

**Returns:**
- `dict`: State summary
  - `cognitive_entropy` (float): Entropy of cognitive dimensions
  - `ethical_entropy` (float): Entropy of ethical dimensions
  - `total_energy` (float): Total wave function energy
  - `dominant_cognitive_dims` (list): Most active cognitive dimensions
  - `dominant_ethical_dims` (list): Most active ethical dimensions

**Example:**
```python
ecwf = mind.ecwf_core
state = ecwf.get_state_summary()

print(f"Cognitive entropy: {state['cognitive_entropy']:.3f}")
print(f"Ethical entropy: {state['ethical_entropy']:.3f}")
print(f"Dominant cognitive: {state['dominant_cognitive_dims']}")
```

---

##### `set_dimension_meanings()`

Set semantic meanings for dimensions.

```python
set_dimension_meanings(
    cognitive_meanings: Dict[int, str],
    ethical_meanings: Dict[int, str]
) -> None
```

**Parameters:**
- `cognitive_meanings` (dict): Mapping of dimension index → meaning
- `ethical_meanings` (dict): Mapping of dimension index → meaning

**Example:**
```python
ecwf.set_dimension_meanings(
    cognitive_meanings={
        0: "Situational awareness",
        1: "Consequence prediction",
        2: "Pattern recognition"
    },
    ethical_meanings={
        0: "Non-maleficence",
        1: "Beneficence",
        2: "Autonomy"
    }
)
```

---

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `num_cognitive_dims` | `int` | Number of cognitive dimensions |
| `num_ethical_dims` | `int` | Number of ethical dimensions |
| `cognitive_meanings` | `dict` | Cognitive dimension semantics |
| `ethical_meanings` | `dict` | Ethical dimension semantics |

---

### MemoryECWFBridge

**Import**: `from memory.memory_ecwf_bridge import MemoryECWFBridge`

Bidirectional bridge between symbolic (Memory Web) and subsymbolic (ECWF) representations.

#### Key Methods

##### `initialize_concept_mappings()`

Initialize mappings between concepts and wave dimensions.

```python
initialize_concept_mappings(
    explicit_ethical_concepts: List[str]
) -> int
```

**Parameters:**
- `explicit_ethical_concepts` (list): Concepts to map to ethical dimensions

**Returns:**
- `int`: Number of mappings created

**Example:**
```python
bridge = mind.memory_bridge

num_mappings = bridge.initialize_concept_mappings([
    "Non-maleficence",
    "Beneficence",
    "Autonomy",
    "Justice",
    "Transparency"
])

print(f"Created {num_mappings} concept-dimension mappings")
```

---

##### `get_metrics()`

Get bridge operation metrics.

```python
get_metrics() -> Dict[str, Any]
```

**Returns:**
- `dict`: Metrics including number of mappings, translations, etc.

---

## Cognitive Blocks

### BaseBlock

**Import**: `from blocks.base_block import BaseBlock`

Abstract base class for all cognitive blocks.

#### Interface

All blocks must implement:

```python
def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
    """
    Process a cognitive chunk.

    Args:
        chunk: The cognitive chunk to process

    Returns:
        The modified cognitive chunk
    """
    pass
```

---

### Block Interfaces

Each block has specific responsibilities and section outputs.

#### SensoryInputBlock

**File**: `blocks/sensory_input_block.py`

**Purpose**: Parse and preprocess input text.

**Methods:**
- `create_chunk_from_input(input_text: str, metadata: dict) -> CognitiveChunk`
- `process_chunk(chunk: CognitiveChunk) -> CognitiveChunk`

**Outputs to**: `sensory_input_section`

**Example:**
```python
sensory_block = mind.blocks["SensoryInput"]
chunk = sensory_block.create_chunk_from_input(
    "What is AI?",
    metadata={"domain": "technical"}
)
```

---

#### MemoryStorageBlock

**File**: `blocks/memory_storage_block.py`

**Purpose**: Interface with Memory Web and ECWF.

**Constructor:**
```python
MemoryStorageBlock(memory_bridge: MemoryECWFBridge)
```

**Outputs to**: `memory_section`, `wave_function_section`

---

#### EthicsValuesBlock

**File**: `blocks/ethics_values_block.py`

**Purpose**: Evaluate ethical implications.

**Constructor:**
```python
EthicsValuesBlock(memory_bridge: MemoryECWFBridge)
```

**Outputs to**: `ethics_king_section` (after Ethics King oversight)

---

## Governance Layer

### ThreeKingsLayer

**Import**: `from kings.three_kings_layer import ThreeKingsLayer`

Coordinates the three governance kings.

#### Methods

##### `oversee_processing()`

Apply coordinated oversight from all three kings.

```python
oversee_processing(chunk: CognitiveChunk) -> CognitiveChunk
```

**Parameters:**
- `chunk` (CognitiveChunk): Chunk to oversee

**Returns:**
- `CognitiveChunk`: Modified chunk with governance decisions

---

### Individual Kings

#### DataKing

**File**: `kings/data_king.py`

**Role**: Information quality and validation

**Methods:**
- `oversee_processing(chunk) -> chunk`: Validate data quality

---

#### ForefrontKing

**File**: `kings/forefront_king.py`

**Role**: Executive function and action selection

**Methods:**
- `oversee_processing(chunk) -> chunk`: Review action decisions

---

#### EthicsKing

**File**: `kings/ethics_king.py`

**Role**: Ethical oversight and moral evaluation

**Methods:**
- `oversee_processing(chunk) -> chunk`: Evaluate ethical implications

---

## Configuration

### System Configuration

Configuration dictionary accepted by `UnifiedSyntheticMind.__init__()`:

```python
config = {
    # ECWF Parameters
    "cognitive_dimensions": 5,        # Number of cognitive dimensions
    "ethical_dimensions": 5,          # Number of ethical dimensions
    "wave_facets": 7,                # Wave function facets

    # Bridge Parameters
    "bridge_influence_factor": 0.3,   # Memory-ECWF bridge influence

    # Learning Parameters
    "learning_rate": 0.05,            # System learning rate

    # Decision Parameters
    "decision_threshold": 0.7,        # Confidence threshold for decisions
    "ethical_sensitivity": 0.6,       # Sensitivity to ethical concerns

    # System Parameters
    "initialize_knowledge": True,     # Auto-initialize knowledge base
    "log_level": "INFO"              # Logging level
}
```

**Example:**
```python
custom_config = {
    "cognitive_dimensions": 7,
    "ethical_dimensions": 6,
    "learning_rate": 0.03,
    "ethical_sensitivity": 0.8,
    "initialize_knowledge": True
}

mind = UnifiedSyntheticMind(seed=42, config=custom_config)
```

---

### Default Configuration Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cognitive_dimensions` | 5 | Cognitive wave dimensions |
| `ethical_dimensions` | 5 | Ethical wave dimensions |
| `wave_facets` | 7 | Wave function facets |
| `bridge_influence_factor` | 0.3 | Bridge translation strength |
| `learning_rate` | 0.05 | Adaptation rate |
| `decision_threshold` | 0.7 | Decision confidence threshold |
| `ethical_sensitivity` | 0.6 | Ethical concern sensitivity |
| `initialize_knowledge` | True | Auto-initialize knowledge |
| `log_level` | "INFO" | Logging verbosity |

---

## Utilities

### Logging

**Import**: `from utils.logging_utils import setup_logger`

```python
setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger
```

**Parameters:**
- `name` (str): Logger name
- `level` (int): Logging level
- `log_file` (str, optional): File to log to
- `format_string` (str, optional): Custom format

**Returns:**
- `logging.Logger`: Configured logger

**Example:**
```python
from utils.logging_utils import setup_logger
import logging

logger = setup_logger(
    "my_module",
    level=logging.DEBUG,
    log_file="my_app.log"
)

logger.info("System initialized")
logger.debug("Debug information")
```

---

## Common Usage Patterns

### Pattern 1: Simple Query-Response

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind()
response = mind.get_response("What is machine learning?")
print(response)
```

---

### Pattern 2: Examine Processing

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind()
chunk = mind.process_input("Explain AI ethics")

# Examine each stage
sensory = chunk.get_section_content("sensory_input_section")
memory = chunk.get_section_content("memory_section")
ethics = chunk.get_section_content("ethics_king_section")

print(f"Complexity: {sensory['complexity_score']}")
print(f"Concepts: {memory['retrieved_concepts']}")
print(f"Ethics: {ethics['evaluation']['status']}")
```

---

### Pattern 3: Memory Exploration

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind()

# Add concept
mind.memory_web.add_thought("Quantum Computing", stability=0.85)

# Connect to existing
mind.memory_web.connect_thoughts(
    "Quantum Computing",
    "Artificial Intelligence",
    strength=0.7
)

# Explore relationships
activated = mind.memory_web.activate_concepts(
    initial_concepts=["Quantum Computing"],
    num_steps=2
)
```

---

### Pattern 4: Ethical Analysis

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind(config={"ethical_sensitivity": 0.8})

chunk = mind.process_input(
    "Should AI make life-or-death decisions?",
    metadata={"domain": "ethics"}
)

ethics = chunk.get_section_content("ethics_king_section")
evaluation = ethics['evaluation']

print(f"Status: {evaluation['status']}")
print(f"Score: {evaluation['overall_ethical_score']}")
print(f"Concerns: {evaluation['concerns']}")

for principle, score in evaluation['principle_scores'].items():
    print(f"  {principle}: {score:.3f}")
```

---

### Pattern 5: Monitoring and Metrics

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind()

# Process some queries
for query in queries:
    mind.get_response(query)

# Get comprehensive metrics
metrics = mind.get_system_metrics()

print(f"Interactions: {metrics['total_interactions']}")
print(f"T_g: {metrics['glass_transition_temp']:.3f}")
print(f"Kings activity: {metrics['kings_metrics']}")
```

---

## Error Handling

### Common Exceptions

- `ImportError`: Module not found (check installation)
- `KeyError`: Section not found in CognitiveChunk
- `ValueError`: Invalid parameter value
- `FileNotFoundError`: State file not found (load_system_state)

### Example

```python
from usm import UnifiedSyntheticMind

try:
    mind = UnifiedSyntheticMind(config={"invalid_key": 123})
    chunk = mind.process_input("test")

    # Safe section access
    ethics = chunk.get_section_content("ethics_king_section")
    if ethics:
        status = ethics.get("evaluation", {}).get("status", "unknown")
    else:
        status = "not_available"

except ImportError as e:
    print(f"Installation issue: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Version Information

### Version History

- **0.1.0** (2025-01-XX): Initial release
  - Core architecture implemented
  - Nine-block cognitive system
  - Three Kings governance
  - Memory-ECWF bridge
  - Basic knowledge initialization

### API Stability

- ✅ **Stable**: UnifiedSyntheticMind core API
- ✅ **Stable**: CognitiveChunk structure
- ⚠️ **Beta**: Memory Web API (may expand)
- ⚠️ **Beta**: ECWF API (may add methods)
- 🚧 **Alpha**: Block-specific APIs (subject to change)

---

## Additional Resources

- **Main README**: `../README.md` - Project overview
- **Architecture Docs**: `architecture.md` - System design
- **Examples**: `../examples/` - Working code examples
- **Installation**: `../INSTALL.md` - Setup guide
- **Source Code**: `../Verdant Source Codes/src/` - Implementation

---

## Support

For questions or issues:
- **GitHub Issues**: [Report bugs or request features](https://github.com/captainkoopa42/Verdant-Minds/issues)
- **Email**: adamswilliam905@gmail.com

---

**Last Updated**: 2025-01-XX
**API Version**: 0.1.0
**License**: MIT
