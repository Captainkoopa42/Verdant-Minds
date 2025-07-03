import json
import numpy as np

from usm import UnifiedSyntheticMind
from integration.BlockIntegrationManager import BlockIntegrationManager
from integration.SystemIntegrationFramework import create_integration_testing_module
from integration.IntegrationTestSuite import IntegrationTestSuite


def run_evolution_loop(iterations: int = 3) -> None:
    """Runs a full system test of Verdant-Minds."""

    # Initialize core system and supporting modules
    mind = UnifiedSyntheticMind()
    integration_manager = BlockIntegrationManager(mind)
    integration_framework = create_integration_testing_module(mind)
    test_suite = IntegrationTestSuite(mind, integration_manager)

    prompts = [
        "Discuss the ethical implications of AI in healthcare resource allocation.",
        "Explain the challenges of decision-making under uncertainty.",
        "Explore links between innovation, sustainability, and equity.",
        "You discover a self-driving car must choose between harming a pedestrian or the passenger. What should it do?",
        "How does quantum entanglement relate to information transfer?",
        "Write a short imaginative story about a green robot in a forest.",
        "Blargle zorp wibble wobble?",
        "What is the nature of consciousness?",
    ]

    run_results = []

    for i in range(iterations):
        text = prompts[i % len(prompts)]

        chunk = mind.process_input(text)
        reply = mind.get_response(text)

        print(f"\n[Cycle {i+1}] Prompt: {text}")
        print(f"Response: {reply}\n")

        run_results.append({"prompt": text, "response": reply})

        mem_data = chunk.get_section_content("memory_section") or {}
        input_concepts = [
            c[0] if isinstance(c, tuple) else c
            for c in mem_data.get("retrieved_concepts", [])
        ]

        cog_state = np.random.rand(mind.ecwf_core.num_cognitive_dims)
        eth_state = np.random.rand(mind.ecwf_core.num_ethical_dims)

        mind.memory_bridge.bidirectional_update(
            cog_state, eth_state, input_concepts, t=i
        )

    print("\n✅ Full System Evolution Completed.")

    print("\nFinal System Metrics:")
    final_metrics = mind.get_system_metrics()
    print(json.dumps(final_metrics, indent=2))

    vis_path = mind.visualize_memory()
    if vis_path:
        print(f"\nMemory graph saved to: {vis_path}")

    print("\n🔎 Running Integration Tests...")
    results = test_suite.run_integration_tests()
    print("\nIntegration Test Summary:")
    print(json.dumps(results.get("performance_metrics", {}), indent=2))

    with open("verdant_run_results.json", "w") as f:
        json.dump({"runs": run_results, "metrics": final_metrics}, f, indent=2)


if __name__ == "__main__":
    run_evolution_loop()
