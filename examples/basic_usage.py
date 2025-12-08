#!/usr/bin/env python3
"""
Verdant-Minds Basic Usage Example

This script demonstrates the fundamental usage patterns of the Unified Synthetic Mind
cognitive architecture. It shows how to initialize the system, process inputs, examine
cognitive processing, access memory, and inspect ethical evaluations.

Note: This example works with the current codebase even without pre-trained models.
Responses are based on template logic and initialized knowledge.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
# This allows importing from the usm package
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind


def print_section_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def example_1_basic_initialization():
    """
    Example 1: Basic System Initialization

    Shows how to create an instance of the Unified Synthetic Mind with
    default configuration.
    """
    print_section_header("Example 1: Basic Initialization")

    # Initialize the system with default settings
    # The seed parameter ensures reproducible results
    mind = UnifiedSyntheticMind(seed=42)

    print("✓ UnifiedSyntheticMind initialized successfully!")
    print(f"  - Cognitive dimensions: {mind.ecwf_core.num_cognitive_dims}")
    print(f"  - Ethical dimensions: {mind.ecwf_core.num_ethical_dims}")
    print(f"  - Memory Web nodes: {mind.memory_web.graph.number_of_nodes()}")
    print(f"  - Memory Web edges: {mind.memory_web.graph.number_of_edges()}")

    return mind


def example_2_custom_configuration():
    """
    Example 2: Custom Configuration

    Shows how to initialize the system with custom parameters to control
    cognitive processing behavior.
    """
    print_section_header("Example 2: Custom Configuration")

    # Create custom configuration
    custom_config = {
        "cognitive_dimensions": 5,      # Number of cognitive dimensions in ECWF
        "ethical_dimensions": 5,        # Number of ethical dimensions in ECWF
        "wave_facets": 7,              # Wave function facets
        "learning_rate": 0.05,         # Learning rate for adaptation
        "decision_threshold": 0.7,     # Confidence threshold for decisions
        "ethical_sensitivity": 0.6,    # Sensitivity to ethical concerns
        "initialize_knowledge": True   # Auto-initialize knowledge base
    }

    mind = UnifiedSyntheticMind(seed=42, config=custom_config)

    print("✓ UnifiedSyntheticMind initialized with custom config!")
    print(f"  - Learning rate: {mind.config['learning_rate']}")
    print(f"  - Decision threshold: {mind.config['decision_threshold']}")
    print(f"  - Ethical sensitivity: {mind.config['ethical_sensitivity']}")

    return mind


def example_3_simple_query(mind):
    """
    Example 3: Processing a Simple Query

    Shows how to process a simple input and get a response.
    """
    print_section_header("Example 3: Processing a Simple Query")

    # Process a simple query
    query = "What is artificial intelligence?"

    print(f"Query: {query}")
    print("\nProcessing through the cognitive pipeline...")

    # Get response (this processes through all 9 blocks)
    response = mind.get_response(query)

    print(f"\nResponse:\n{response}")

    # Check system metrics
    metrics = mind.get_system_metrics()
    print(f"\n✓ Processing complete!")
    print(f"  - Total interactions: {metrics['total_interactions']}")
    print(f"  - Glass transition temp: {metrics['glass_transition_temp']:.3f}")


def example_4_retrieve_cognitive_chunk(mind):
    """
    Example 4: Retrieving and Examining a CognitiveChunk

    Shows how to access the CognitiveChunk that flows through the pipeline
    and examine its contents in detail.
    """
    print_section_header("Example 4: Examining CognitiveChunk")

    # Process input and get the cognitive chunk
    query = "How can AI be used ethically in healthcare?"

    print(f"Query: {query}")
    print("\nProcessing to retrieve CognitiveChunk...")

    # Use process_input to get the chunk directly (instead of get_response)
    chunk = mind.process_input(query)

    print(f"\n✓ CognitiveChunk retrieved!")
    print(f"  - Number of sections: {len(chunk.sections)}")
    print(f"  - Available sections:")

    for section_name in chunk.sections.keys():
        print(f"    • {section_name}")

    # Examine specific sections
    print("\n--- Sensory Input Section ---")
    sensory_data = chunk.get_section_content("sensory_input_section")
    if sensory_data:
        print(f"  Input text: {sensory_data.get('input_text', 'N/A')[:50]}...")
        print(f"  Token count: {len(sensory_data.get('tokens', []))}")
        print(f"  Complexity score: {sensory_data.get('complexity_score', 0):.2f}")

    print("\n--- Memory Section ---")
    memory_data = chunk.get_section_content("memory_section")
    if memory_data:
        retrieved = memory_data.get('retrieved_concepts', [])
        print(f"  Retrieved concepts: {len(retrieved)}")
        if retrieved:
            concepts = [c[0] if isinstance(c, tuple) else c for c in retrieved[:5]]
            print(f"  Top concepts: {', '.join(concepts)}")

    print("\n--- Action Selection Section ---")
    action_data = chunk.get_section_content("action_selection_section")
    if action_data:
        print(f"  Selected action: {action_data.get('selected_action', 'N/A')}")
        print(f"  Action confidence: {action_data.get('action_confidence', 0):.2f}")
        print(f"  Action reason: {action_data.get('action_reason', 'N/A')}")


def example_5_access_memory_web(mind):
    """
    Example 5: Accessing the Memory Web

    Shows how to directly interact with the semantic memory graph,
    query concepts, and explore relationships.
    """
    print_section_header("Example 5: Accessing Memory Web")

    # Access the Memory Web directly
    memory_web = mind.memory_web

    print(f"Memory Web Statistics:")
    print(f"  - Total concepts (nodes): {memory_web.graph.number_of_nodes()}")
    print(f"  - Total connections (edges): {memory_web.graph.number_of_edges()}")

    # List some concepts in memory
    print("\n--- Sample Concepts ---")
    concepts = list(memory_web.graph.nodes())[:10]
    for concept in concepts:
        stability = memory_web.graph.nodes[concept].get('stability', 0)
        print(f"  • {concept} (stability: {stability:.2f})")

    # Query for related concepts
    if "Artificial Intelligence" in memory_web.graph:
        print("\n--- Concepts Related to 'Artificial Intelligence' ---")

        # Activate concepts starting from AI
        activated = memory_web.activate_concepts(
            initial_concepts=["Artificial Intelligence"],
            num_steps=2,           # Spread activation for 2 steps
            activation_threshold=0.3  # Minimum activation to include
        )

        print(f"  Activated {len(activated)} related concepts:")
        for concept, activation in list(activated.items())[:10]:
            print(f"    • {concept}: {activation:.3f}")

    # Add a new concept manually (demonstration)
    print("\n--- Adding a New Concept ---")
    memory_web.add_thought(
        "Machine Learning",
        stability=0.8,
        metadata={"description": "AI subset focused on learning from data"}
    )
    print("  ✓ Added 'Machine Learning' to Memory Web")

    # Connect it to existing concept
    if "Artificial Intelligence" in memory_web.graph:
        memory_web.connect_thoughts(
            "Artificial Intelligence",
            "Machine Learning",
            strength=0.9
        )
        print("  ✓ Connected 'Machine Learning' to 'Artificial Intelligence'")


def example_6_examine_wave_function(mind):
    """
    Example 6: Examining the Extended Cognitive Wave Function (ECWF)

    Shows how to access and examine the quantum-inspired wave function
    representation of cognitive states.
    """
    print_section_header("Example 6: Examining ECWF Wave Function")

    # Access the ECWF core
    ecwf = mind.ecwf_core

    print("ECWF Configuration:")
    print(f"  - Cognitive dimensions: {ecwf.num_cognitive_dims}")
    print(f"  - Ethical dimensions: {ecwf.num_ethical_dims}")

    # Get current wave function state
    state = ecwf.get_state_summary()

    print("\nCurrent Wave Function State:")
    print(f"  - Cognitive entropy: {state['cognitive_entropy']:.3f}")
    print(f"  - Ethical entropy: {state['ethical_entropy']:.3f}")
    print(f"  - Total energy: {state['total_energy']:.3f}")

    # Show dimension meanings
    print("\n--- Cognitive Dimensions ---")
    cog_meanings = ecwf.cognitive_meanings
    for dim, meaning in cog_meanings.items():
        print(f"  Dimension {dim}: {meaning}")

    print("\n--- Ethical Dimensions ---")
    eth_meanings = ecwf.ethical_meanings
    for dim, meaning in eth_meanings.items():
        print(f"  Dimension {dim}: {meaning}")

    # Process a query and examine wave state changes
    print("\n--- Processing Query and Observing Wave Function ---")
    chunk = mind.process_input("Should AI be transparent?")

    wave_data = chunk.get_section_content("wave_function_section")
    if wave_data:
        print(f"  Wave entropy after processing: {wave_data.get('entropy', 0):.3f}")
        print(f"  Dominant cognitive dims: {wave_data.get('dominant_cognitive_dims', [])}")
        print(f"  Dominant ethical dims: {wave_data.get('dominant_ethical_dims', [])}")


def example_7_ethical_evaluation(mind):
    """
    Example 7: Examining Ethical Evaluation

    Shows how to access the ethical reasoning performed by the Ethics King
    and examine principle-based evaluations.
    """
    print_section_header("Example 7: Ethical Evaluation")

    # Process an ethically-charged query
    query = "Is it acceptable to use AI for surveillance without consent?"

    print(f"Query: {query}")
    print("\nProcessing with ethical oversight...")

    chunk = mind.process_input(query)

    # Examine ethical evaluation
    ethics_data = chunk.get_section_content("ethics_king_section")

    if ethics_data:
        evaluation = ethics_data.get('evaluation', {})

        print("\n--- Ethics King Evaluation ---")
        print(f"  Ethical status: {evaluation.get('status', 'N/A')}")
        print(f"  Overall ethical score: {evaluation.get('overall_ethical_score', 0):.3f}")

        # Show principle scores
        principle_scores = evaluation.get('principle_scores', {})
        if principle_scores:
            print("\n  Principle Scores:")
            for principle, score in principle_scores.items():
                print(f"    • {principle}: {score:.3f}")

        # Show ethical concerns
        concerns = evaluation.get('concerns', [])
        if concerns:
            print("\n  Ethical Concerns Identified:")
            for concern in concerns:
                print(f"    ⚠ {concern}")

        # Show recommendation
        recommendation = evaluation.get('recommendation', '')
        if recommendation:
            print(f"\n  Recommendation: {recommendation}")


def example_8_system_metrics(mind):
    """
    Example 8: Monitoring System Metrics

    Shows how to access comprehensive system metrics including performance,
    memory usage, and king influence statistics.
    """
    print_section_header("Example 8: System Metrics")

    # Process a few queries to generate metrics
    queries = [
        "What is machine learning?",
        "How does ethical AI work?",
        "What are the benefits of transparency?"
    ]

    print("Processing multiple queries to generate metrics...")
    for query in queries:
        mind.get_response(query)
        print(f"  ✓ Processed: {query[:40]}...")

    # Get comprehensive metrics
    metrics = mind.get_system_metrics()

    print("\n--- System Metrics ---")
    print(f"  Total interactions: {metrics['total_interactions']}")
    print(f"  Uptime: {metrics['uptime']:.2f} seconds")
    print(f"  Interactions per hour: {metrics['interactions_per_hour']:.2f}")
    print(f"  Glass transition temp: {metrics['glass_transition_temp']:.3f}")
    print(f"  System entropy: {metrics['system_entropy']:.3f}")
    print(f"  Ethical evaluations: {metrics['ethical_evaluations']}")
    print(f"  Decisions made: {metrics['decisions_made']}")

    # Memory metrics
    print("\n--- Memory Metrics ---")
    mem_metrics = metrics.get('memory_metrics', {})
    print(f"  Concepts in memory: {mem_metrics.get('num_thoughts', 0)}")
    print(f"  Connections: {mem_metrics.get('num_connections', 0)}")

    # Bridge metrics
    print("\n--- Memory-ECWF Bridge Metrics ---")
    bridge_metrics = metrics.get('bridge_metrics', {})
    print(f"  Concept-to-wave mappings: {bridge_metrics.get('concept_mappings', 0)}")

    # King metrics
    print("\n--- Three Kings Activity ---")
    kings_metrics = metrics.get('kings_metrics', {})
    print(f"  Data King interventions: {kings_metrics.get('data_king', 0)}")
    print(f"  Forefront King decisions: {kings_metrics.get('forefront_king', 0)}")
    print(f"  Ethics King evaluations: {kings_metrics.get('ethics_king', 0)}")


def example_9_save_and_load(mind):
    """
    Example 9: Saving and Loading System State

    Shows how to persist the system state to disk and restore it later.
    """
    print_section_header("Example 9: Save and Load System State")

    # Save system state
    save_path = "mind_state_example.pkl"

    print(f"Saving system state to: {save_path}")
    success = mind.save_system_state(save_path)

    if success:
        print("  ✓ System state saved successfully!")

        # Load system state
        print(f"\nLoading system state from: {save_path}")
        restored_mind = UnifiedSyntheticMind.load_system_state(save_path)

        print("  ✓ System state loaded successfully!")

        # Verify restoration
        restored_metrics = restored_mind.get_system_metrics()
        print(f"\n  Restored system metrics:")
        print(f"    - Total interactions: {restored_metrics['total_interactions']}")
        print(f"    - Memory concepts: {restored_metrics['memory_metrics']['num_thoughts']}")

        # Clean up example file
        import os
        os.remove(save_path)
        print(f"\n  Cleaned up example file: {save_path}")
    else:
        print("  ✗ Failed to save system state")


def main():
    """Main function to run all examples."""
    print("\n" + "=" * 70)
    print("  VERDANT-MINDS BASIC USAGE EXAMPLES")
    print("  Unified Synthetic Mind Cognitive Architecture")
    print("=" * 70)

    try:
        # Example 1: Basic initialization
        mind = example_1_basic_initialization()

        # Example 2: Custom configuration
        custom_mind = example_2_custom_configuration()

        # Use the basic mind for remaining examples

        # Example 3: Simple query
        example_3_simple_query(mind)

        # Example 4: Retrieve and examine CognitiveChunk
        example_4_retrieve_cognitive_chunk(mind)

        # Example 5: Access Memory Web
        example_5_access_memory_web(mind)

        # Example 6: Examine wave function
        example_6_examine_wave_function(mind)

        # Example 7: Ethical evaluation
        example_7_ethical_evaluation(mind)

        # Example 8: System metrics
        example_8_system_metrics(mind)

        # Example 9: Save and load
        example_9_save_and_load(mind)

        print("\n" + "=" * 70)
        print("  ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nNext Steps:")
        print("  1. Modify these examples for your own use cases")
        print("  2. Explore the source code in 'Verdant Source Codes/src/'")
        print("  3. Read the architecture documentation in 'docs/architecture.md'")
        print("  4. Check out the main README.md for more information")
        print("\n")

    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
