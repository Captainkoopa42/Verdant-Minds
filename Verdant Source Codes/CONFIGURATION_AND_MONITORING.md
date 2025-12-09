# Configuration and Monitoring Guide

This document explains the configuration system, performance benchmarking, and enhanced logging features in Verdant-Minds.

---

## 📋 Table of Contents

- [Configuration System](#configuration-system)
- [Performance Benchmarking](#performance-benchmarking)
- [Enhanced Logging](#enhanced-logging)
- [Log Analysis](#log-analysis)
- [Quick Start Examples](#quick-start-examples)

---

## ⚙️ Configuration System

### Overview

Verdant-Minds uses a flexible YAML-based configuration system that allows you to customize all aspects of the system without changing code.

### Files

- `config/default_config.yaml` - Default configuration (DO NOT MODIFY)
- `config/ethical_reasoning_config.yaml` - Optimized for ethical tasks
- `config/performance_optimized_config.yaml` - Optimized for speed
- `config/research_debug_config.yaml` - Maximum verbosity for research

### Usage

#### Basic Usage

```python
from src.utils.config_manager import ConfigManager

# Use default configuration
config = ConfigManager()

# Load custom configuration
config = ConfigManager(config_path="config/ethical_reasoning_config.yaml")

# Override specific settings
config = ConfigManager(config_override={
    "ecwf.cognitive_dimensions": 7,
    "logging.level": "DEBUG"
})
```

#### Accessing Configuration

```python
# Get value using dot notation
cog_dims = config.get("ecwf.cognitive_dimensions")  # Returns 5

# Get with default
max_tokens = config.get("blocks.sensory_input.max_tokens", default=512)

# Set value
config.set("logging.level", "DEBUG")
```

#### Validation

```python
# Validate configuration
try:
    config.validate()
    print("Configuration valid!")
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
```

#### Saving Configuration

```python
# Save current configuration to file
config.save("my_custom_config.yaml")

# Export as dictionary
config_dict = config.to_dict()
```

### Configuration Sections

#### System

```yaml
system:
  seed: 42                      # Random seed for reproducibility
  debug: false                  # Enable debug mode
  profiling_enabled: false      # Enable performance profiling
  max_concurrent_chunks: 1      # Concurrent processing limit
```

#### ECWF

```yaml
ecwf:
  cognitive_dimensions: 5       # Number of cognitive dimensions
  ethical_dimensions: 5         # Number of ethical dimensions
  initial_amplitude: 1.0        # Initial wave amplitude
  entropy_base: 2.0            # Entropy calculation base
```

#### Memory Web

```yaml
memory_web:
  graph_type: "directed"        # Graph type
  default_stability: 0.5        # Default concept stability
  activation_threshold: 0.3     # Activation spreading threshold
  max_activation_hops: 3        # Max spreading distance
  community_algorithm: "louvain" # Community detection algorithm
```

#### Blocks

```yaml
blocks:
  pattern_recognition:
    enabled: true
    max_keywords: 50
    opposition_detection: true
    tension_computation: true
    sentiment_analysis: true
    entity_recognition: true

  ethics_values:
    enabled: true
    ethical_sensitivity: 0.6    # 0.0 = permissive, 1.0 = strict
    non_maleficence_weight: 1.0
    require_ethical_approval: true
```

#### Governance

```yaml
governance:
  enabled: true
  coordination_strategy: "consensus"  # consensus, majority, weighted_vote
  require_unanimous_approval: false
  approval_threshold: 0.6
```

#### Logging

```yaml
logging:
  level: "INFO"                  # DEBUG, INFO, WARNING, ERROR, CRITICAL

  console:
    enabled: true
    level: "INFO"
    format: "simple"             # simple, detailed, json
    colorized: true

  file:
    enabled: true
    level: "DEBUG"
    path: "logs/verdant_minds.log"
    max_size_mb: 100
    backup_count: 5

  structured:
    enabled: false
    path: "logs/verdant_minds_structured.jsonl"

  performance:
    enabled: true
    log_block_timings: true
    log_memory_usage: true
    metrics_interval: 10
```

### Creating Custom Configurations

1. Copy `config/default_config.yaml`
2. Modify only the sections you need
3. Save with a descriptive name (e.g., `my_experiment_config.yaml`)
4. Load it: `config = ConfigManager(config_path="my_experiment_config.yaml")`

### Best Practices

- **Don't modify default_config.yaml** - It serves as documentation
- **Use descriptive names** - `ethical_strict.yaml` not `config1.yaml`
- **Version control configs** - Track configuration changes with git
- **Validate before use** - Always call `config.validate()`
- **Document overrides** - Add comments explaining why you changed defaults

---

## 🏁 Performance Benchmarking

### Overview

The performance benchmarking suite measures processing time, memory usage, and throughput for the Verdant-Minds system.

### Quick Start

```bash
# Quick benchmark (10 iterations)
python -m benchmarks.performance_tests --mode quick

# Full benchmark (100 iterations)
python -m benchmarks.performance_tests --mode full --iterations 100

# Benchmark single block
python -m benchmarks.performance_tests --mode block --block PatternRecognition

# Compare configurations
python -m benchmarks.performance_tests --mode compare

# Save results to JSON
python -m benchmarks.performance_tests --mode full --output results.json
```

### Programmatic Usage

```python
from benchmarks.performance_tests import PerformanceBenchmark

# Create benchmark
benchmark = PerformanceBenchmark(config_name="default")

# Run full benchmark
performance = benchmark.run_full_benchmark(num_iterations=100)

# Print results
print(f"Throughput: {performance.throughput_chunks_per_sec:.2f} chunks/sec")
print(f"Bottleneck: {performance.bottleneck_block}")

# Benchmark single block
block_perf = benchmark.benchmark_single_block("PatternRecognition", num_iterations=1000)

# Save results
benchmark.save_results(performance, "my_results.json")
```

### Metrics Collected

#### System-Level
- **Total time** - Overall processing time
- **Throughput** - Chunks processed per second
- **Mean chunk time** - Average time per chunk
- **Peak memory** - Maximum memory usage
- **Average memory** - Mean memory usage

#### Block-Level
- **Mean time** - Average processing time
- **Median time** - Median processing time
- **Standard deviation** - Time variability
- **Min/Max time** - Time range
- **Memory delta** - Memory change per execution

### Interpreting Results

```
BENCHMARK RESULTS
==========================================
Overall Performance:
  Total time: 12.345s
  Throughput: 8.10 chunks/sec
  Mean chunk time: 123.45 ms

Block-by-Block Performance:
Block                     Mean (ms)  Median (ms)  Std Dev   Total (ms)
------------------------------------------------------------------------
PatternRecognition           45.123       44.567     2.345    4512.300
MemoryStorage               23.456       23.012     1.234    2345.600
...

Bottleneck: PatternRecognition
```

**Bottleneck** = Slowest block (focus optimization here)

### Baseline Performance (Untrained Weights)

**Typical Performance (Default Config, Laptop):**
- **Throughput**: 5-10 chunks/second
- **Mean chunk time**: 100-200 ms
- **Peak memory**: 200-400 MB
- **Bottleneck**: Usually PatternRecognition or MemoryStorage

**Factors Affecting Performance:**
- System configuration (dimensions, thresholds)
- Memory Web size (number of concepts/relations)
- Input complexity (text length, vocabulary)
- Hardware (CPU, RAM)
- Python version and NumPy optimization

### Optimization Tips

1. **Reduce dimensions** - Lower cognitive_dimensions and ethical_dimensions
2. **Limit memory spreading** - Decrease max_activation_hops
3. **Disable expensive features** - Turn off entity_recognition
4. **Increase thresholds** - Higher activation_threshold = fewer nodes
5. **Enable caching** - Set enable_caching: true
6. **Use performance config** - Load `performance_optimized_config.yaml`

---

## 📊 Enhanced Logging

### Overview

The enhanced logging system provides structured, performant, and analyzable logging with multiple output formats.

### Setup

```python
from src.utils.enhanced_logging import setup_logging, get_logger

# Set up logging system
setup_logging(
    level="INFO",
    log_file="logs/verdant.log",
    structured_log_file="logs/verdant_structured.jsonl",
    console_output=True,
    colorize=True
)

# Get logger
logger = get_logger(__name__, context={"component": "PatternRecognition"})
```

### Log Levels

- **DEBUG** - Detailed diagnostic information
- **INFO** - General informational messages
- **WARNING** - Warning messages (something unexpected)
- **ERROR** - Error messages (something failed)
- **CRITICAL** - Critical errors (system failure)

### Usage

#### Basic Logging

```python
logger.debug("Processing chunk", extra={"chunk_id": "123"})
logger.info("Chunk processed successfully")
logger.warning("Low confidence in result")
logger.error("Failed to process chunk", exc_info=True)
```

#### Structured Logging

```python
# All logs include structured metadata
logger.info(
    "Pattern detection complete",
    extra={
        "extra_data": {
            "chunk_id": "abc123",
            "keywords_found": 15,
            "oppositions": 3,
            "sentiment": "neutral"
        }
    }
)
```

#### Performance Logging

```python
# Log timing
logger.performance.log_timing("pattern_recognition", 45.3, chunk_id="123")

# Log memory
logger.performance.log_memory("memory_storage", 12.5, operation="add_concepts")

# Log throughput
logger.performance.log_throughput("system", 8.5, window="last_minute")
```

#### Timing Context

```python
from src.utils.enhanced_logging import TimingContext

# Automatically log duration
with TimingContext(logger, "expensive_operation", metadata={"type": "test"}):
    # Your code here
    process_chunk(chunk)
```

#### Chunk Processing Events

```python
# Start processing
logger.log_chunk_processing("chunk_123", "PatternRecognition", status="start")

# Complete processing
logger.log_chunk_processing("chunk_123", "PatternRecognition", status="complete",
                           keywords=15, oppositions=3)

# Log block output
logger.log_block_output("PatternRecognition", {
    "keywords_extracted": 15,
    "tensions_detected": 3
})
```

### Log Formats

#### Console (Colorized)

```
2025-01-08 10:30:15 | INFO     | pattern_recognition | Processing chunk 123
2025-01-08 10:30:15 | ERROR    | memory_storage | Failed to add concept
```

#### File (Detailed)

```
2025-01-08 10:30:15,123 | INFO     | src.blocks.pattern_recognition | process_chunk | Processing chunk 123
```

#### Structured (JSON)

```json
{
  "timestamp": "2025-01-08T10:30:15.123456",
  "level": "INFO",
  "logger": "src.blocks.pattern_recognition",
  "message": "Processing chunk 123",
  "module": "pattern_recognition_block",
  "function": "process_chunk",
  "line": 98,
  "extra_data": {
    "chunk_id": "123",
    "block": "PatternRecognition"
  }
}
```

### Log Rotation

Logs are automatically rotated when they reach the configured size:

```yaml
logging:
  file:
    max_size_mb: 100        # Rotate at 100MB
    backup_count: 5         # Keep 5 backups
    rotation: "size"        # Rotate by size
```

Rotated files: `verdant.log`, `verdant.log.1`, `verdant.log.2`, etc.

---

## 🔍 Log Analysis

### Overview

The log analyzer extracts insights from structured JSON logs.

### Command Line Usage

```bash
# Generate report
python -m src.utils.monitoring.log_analyzer logs/verdant_structured.jsonl --report

# Show errors only
python -m src.utils.monitoring.log_analyzer logs/verdant_structured.jsonl --errors

# Export metrics to JSON
python -m src.utils.monitoring.log_analyzer logs/verdant_structured.jsonl \
    --export metrics.json
```

### Programmatic Usage

```python
from src.utils.monitoring.log_analyzer import LogAnalyzer

# Create analyzer
analyzer = LogAnalyzer("logs/verdant_structured.jsonl")

# Get performance metrics
metrics = analyzer.get_performance_metrics()
print(f"Mean pattern recognition time: {metrics['timing']['pattern_recognition']['mean']:.2f}ms")

# Get error summary
errors = analyzer.get_error_summary()
print(f"Total errors: {errors['total_errors']}")

# Generate report
report = analyzer.generate_report()
print(report)

# Export metrics
analyzer.export_metrics("analysis_results.json")
```

### Analysis Output

```
VERDANT-MINDS LOG ANALYSIS REPORT
================================================================================
Log file: logs/verdant_structured.jsonl
Total entries: 5432

Log Level Distribution:
  DEBUG     :   3201
  INFO      :   2015
  WARNING   :    195
  ERROR     :     19
  CRITICAL  :      2

Performance Metrics:

  Timing Statistics:
  Operation                          Mean (ms)   Median (ms)          Min          Max
  ----------------------------------------------------------------------------------
  pattern_recognition                   45.123        44.567       38.901       67.234
  memory_storage                        23.456        23.012       18.345       45.678
  ...

  Memory Statistics:
  Operation                          Mean (MB)       Max (MB)
  ------------------------------------------------------------
  memory_storage                         12.34          25.67
  ...

Block Processing Statistics:
  Block                               Events         Errors
  ------------------------------------------------------------
  PatternRecognition                    1000              0
  MemoryStorage                         1000              2
  ...

Error Summary:
  Total errors: 19

  Error Types:
    KeyError: 12
    ValueError: 5
    AttributeError: 2
```

---

## 🚀 Quick Start Examples

### Example 1: Performance-Optimized System

```python
from src.utils.config_manager import ConfigManager
from src.utils.enhanced_logging import setup_logging

# Load performance config
config = ConfigManager(config_path="config/performance_optimized_config.yaml")

# Setup minimal logging
setup_logging(
    level="WARNING",  # Only warnings and errors
    console_output=True,
    log_file=None  # Disable file logging
)

# Use system with optimized configuration
from usm import UnifiedSyntheticMind
mind = UnifiedSyntheticMind(config=config)
```

### Example 2: Research/Debug Mode

```python
from src.utils.config_manager import ConfigManager
from src.utils.enhanced_logging import setup_logging, get_logger

# Load debug config
config = ConfigManager(config_path="config/research_debug_config.yaml")

# Setup comprehensive logging
setup_logging(
    level="DEBUG",
    log_file="logs/research.log",
    structured_log_file="logs/research_structured.jsonl",
    console_output=True,
    colorize=True
)

logger = get_logger(__name__)
logger.info("Starting research session")

# Use system
mind = UnifiedSyntheticMind(config=config)
```

### Example 3: Custom Ethical Configuration

```python
from src.utils.config_manager import ConfigManager

# Load ethical config and customize
config = ConfigManager(config_path="config/ethical_reasoning_config.yaml")

# Override for even stricter ethics
config.set("blocks.ethics_values.ethical_sensitivity", 0.95)
config.set("governance.require_unanimous_approval", True)
config.set("blocks.action_selection.min_confidence", 0.7)

# Validate
config.validate()

# Use
mind = UnifiedSyntheticMind(config=config)
```

### Example 4: Benchmark and Analyze

```python
from benchmarks.performance_tests import PerformanceBenchmark
from src.utils.monitoring.log_analyzer import LogAnalyzer

# Run benchmark with structured logging enabled
config = ConfigManager()
config.set("logging.structured.enabled", True)
config.set("logging.performance.enabled", True)

benchmark = PerformanceBenchmark(config_name="custom")
performance = benchmark.run_full_benchmark(num_iterations=100)

# Analyze logs
analyzer = LogAnalyzer("logs/verdant_structured.jsonl")
report = analyzer.generate_report()
print(report)

# Export both
benchmark.save_results(performance, "benchmark_results.json")
analyzer.export_metrics("log_analysis.json")
```

---

## 📚 Additional Resources

- **Default Configuration**: `config/default_config.yaml` (complete reference)
- **Configuration Validation**: `src/utils/config_manager.py`
- **Performance Benchmarks**: `benchmarks/performance_tests.py`
- **Enhanced Logging**: `src/utils/enhanced_logging.py`
- **Log Analysis**: `src/utils/monitoring/log_analyzer.py`

---

## 🆘 Troubleshooting

### Configuration Issues

**Problem**: `ConfigValidationError: ecwf.cognitive_dimensions must be a positive integer`

**Solution**: Ensure all numeric values are valid:
```yaml
ecwf:
  cognitive_dimensions: 5  # Must be positive integer
  ethical_dimensions: 5    # Must be positive integer
```

### Performance Issues

**Problem**: System is too slow

**Solutions**:
1. Load `performance_optimized_config.yaml`
2. Reduce dimensions (cognitive_dimensions: 3)
3. Disable expensive features (entity_recognition: false)
4. Increase thresholds (activation_threshold: 0.5)

### Logging Issues

**Problem**: Logs not appearing

**Solutions**:
1. Check log level: `logging.level: "DEBUG"`
2. Verify output enabled: `logging.console.enabled: true`
3. Check file permissions for log directory
4. Ensure directory exists: `mkdir -p logs`

### Memory Issues

**Problem**: High memory usage

**Solutions**:
1. Enable auto-pruning: `memory_web.auto_prune: true`
2. Increase prune threshold: `memory_web.prune_threshold: 0.15`
3. Limit activation hops: `memory_web.max_activation_hops: 2`
4. Enable garbage collection: `performance.auto_gc: true`

---

## 📝 Version History

- **v0.2.0** (2025-01-08) - Added configuration system, benchmarking, enhanced logging
- **v0.1.0** (2024-12) - Initial release

---

<div align="center">

**Verdant-Minds** • *Configurable, Observable, Optimizable*

[🏠 Home](../README.md) •
[📖 Main Docs](../README.md) •
[🤝 Contributing](../CONTRIBUTING.md)

</div>
