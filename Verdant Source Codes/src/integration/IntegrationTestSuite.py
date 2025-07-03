import numpy as np
import time
from typing import Dict, List, Any, Optional

class IntegrationTestSuite:
    """
    Comprehensive integration test suite for the Unified Synthetic Mind system.
    
    Provides a framework for rigorous testing of system integration, 
    cross-block communication, and complex reasoning capabilities.
    """
    
    def __init__(self, system, integration_manager):
        """
        Initialize the integration test suite.
        
        Args:
            system: The Unified Synthetic Mind system
            integration_manager: Block Integration Manager
        """
        self.system = system
        self.integration_manager = integration_manager
        
        # Define comprehensive test scenarios
        self.test_scenarios = self._generate_integration_scenarios()
        
        # Performance and metrics tracking
        self.test_results = {}
        self.performance_metrics = {
            "total_scenarios": 0,
            "passed_scenarios": 0,
            "average_processing_time": 0,
            "cross_block_flow_average": 0,
            "ethical_reasoning_quality": 0
        }
    
    def _generate_integration_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate comprehensive integration test scenarios.
        
        Returns:
            List of test scenarios with varying complexity and focus
        """
        scenarios = [
            {
                "name": "Cross-Block Ethical Reasoning",
                "description": "Validate complex ethical decision-making across system blocks",
                "input": "Discuss the ethical implications of AI in healthcare resource allocation",
                "expected_blocks": [
                    "SensoryInput", 
                    "PatternRecognition", 
                    "MemoryStorage", 
                    "InternalCommunication",
                    "ReasoningPlanning",
                    "EthicsValues", 
                    "ActionSelection"
                ],
                "validation_criteria": {
                    "ethical_concept_depth": 0.7,
                    "reasoning_coherence": 0.8,
                    "cross_block_information_flow": 0.75,
                    "processing_time_limit": 2.0  # seconds
                },
                "ethical_principles": [
                    "Non-maleficence", 
                    "Justice", 
                    "Autonomy", 
                    "Beneficence"
                ]
            },
            {
                "name": "Complex Uncertainty Reasoning",
                "description": "Test system's ability to reason under high uncertainty",
                "input": "Analyze potential strategies for managing a pandemic with limited and conflicting information",
                "expected_blocks": [
                    "SensoryInput",
                    "PatternRecognition",
                    "MemoryStorage",
                    "ReasoningPlanning",
                    "EthicsValues",
                    "ActionSelection",
                    "LanguageProcessing"
                ],
                "validation_criteria": {
                    "uncertainty_handling_quality": 0.7,
                    "reasoning_depth": 0.8,
                    "cross_block_information_flow": 0.7,
                    "processing_time_limit": 2.5  # seconds
                },
                "uncertainty_dimensions": [
                    "Data Completeness",
                    "Conflicting Information",
                    "Long-term Consequences"
                ]
            },
            {
                "name": "Multi-Domain Knowledge Integration",
                "description": "Validate system's ability to reason across diverse knowledge domains",
                "input": "Explore the interconnections between technological innovation, environmental sustainability, and social equity",
                "expected_blocks": [
                    "SensoryInput",
                    "PatternRecognition", 
                    "MemoryStorage",
                    "InternalCommunication",
                    "ReasoningPlanning",
                    "EthicsValues",
                    "LanguageProcessing",
                    "ActionSelection"
                ],
                "validation_criteria": {
                    "domain_integration_depth": 0.8,
                    "conceptual_diversity": 0.7,
                    "cross_block_information_flow": 0.8,
                    "processing_time_limit": 3.0  # seconds
                },
                "expected_domains": [
                    "Technology",
                    "Environmental Science", 
                    "Social Policy",
                    "Economics"
                ]
            }
        ]
        return scenarios
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """
        Execute comprehensive integration tests.
        
        Returns:
            Detailed test results dictionary
        """
        # Reset performance metrics
        self._reset_performance_metrics()
        
        # Prepare test results container
        test_results = {
            "overall_success": True,
            "scenario_results": {},
            "performance_metrics": self.performance_metrics
        }
        
        # Run each scenario
        for scenario in self.test_scenarios:
            scenario_result = self._run_single_scenario(scenario)
            test_results["scenario_results"][scenario["name"]] = scenario_result
            
            # Update overall success and performance metrics
            test_results["overall_success"] &= scenario_result["passed"]
            self._update_performance_metrics(scenario_result)
        
        # Finalize performance metrics
        self._finalize_performance_metrics()
        
        return test_results
    
    def _run_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single integration test scenario.
        
        Args:
            scenario: Test scenario configuration
        
        Returns:
            Detailed scenario test results
        """
        # Start timing
        start_time = time.time()
        
        try:
            # Process input through the system
            chunk = self.system.process_input(scenario["input"])
            response = self.system.get_response(scenario["input"])
        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "details": "System processing failed"
            }
        
        # Calculate total processing time
        total_processing_time = time.time() - start_time
        
        # Validate scenario criteria
        validation_results = self._validate_scenario(
            scenario, 
            chunk, 
            response, 
            total_processing_time
        )
        
        return {
            "passed": validation_results["overall_passed"],
            "processing_time": total_processing_time,
            "validation_results": validation_results,
            "response": response
        }
    
    def _validate_scenario(
        self, 
        scenario: Dict[str, Any], 
        chunk: Any, 
        response: str, 
        processing_time: float
    ) -> Dict[str, Any]:
        """
        Validate a scenario against predefined criteria.
        
        Args:
            scenario: Test scenario configuration
            chunk: Processed cognitive chunk
            response: System response
            processing_time: Total processing time
        
        Returns:
            Validation results dictionary
        """
        validation_results = {
            "overall_passed": True,
            "criteria_results": {}
        }
        
        # 1. Block Participation Validation
        processed_sections = chunk.sections.keys() if hasattr(chunk, 'sections') else []
        processed_blocks = [
            section.replace('_section', '').replace('_', ' ').title().replace(' ', '') 
            for section in processed_sections
        ]
        
        expected_blocks = set(scenario["expected_blocks"])
        actual_blocks = set(processed_blocks)
        
        block_participation = len(expected_blocks.intersection(actual_blocks)) / len(expected_blocks)
        validation_results["criteria_results"]["block_participation"] = {
            "passed": block_participation >= 0.8,
            "value": block_participation,
            "details": f"Blocks matched: {actual_blocks.intersection(expected_blocks)}"
        }
        
        # 2. Processing Time Validation
        time_limit = scenario["validation_criteria"].get("processing_time_limit", 3.0)
        time_validation = processing_time <= time_limit
        validation_results["criteria_results"]["processing_time"] = {
            "passed": time_validation,
            "value": processing_time,
            "details": f"Processed in {processing_time:.2f} seconds (limit: {time_limit})"
        }
        
        # 3. Cross-Block Information Flow Validation
        interaction_data = self.integration_manager.analyze_block_interactions(chunk)
        cross_block_flow = self._assess_cross_block_flow(interaction_data)
        flow_validation = cross_block_flow >= scenario["validation_criteria"].get("cross_block_information_flow", 0.6)
        validation_results["criteria_results"]["cross_block_flow"] = {
            "passed": flow_validation,
            "value": cross_block_flow,
            "details": f"Cross-block information flow: {cross_block_flow:.2f}"
        }
        
        # 4. Response Quality Validation
        response_length_validation = len(response) > 50  # Ensure meaningful response
        validation_results["criteria_results"]["response_quality"] = {
            "passed": response_length_validation,
            "value": len(response),
            "details": f"Response length: {len(response)} characters"
        }
        
        # 5. Domain-Specific Validations
        domain_validations = self._perform_domain_specific_validations(
            scenario, 
            chunk, 
            response
        )
        validation_results["criteria_results"].update(domain_validations)
        
        # Determine overall pass/fail
        validation_results["overall_passed"] = all(
            result["passed"] 
            for result in validation_results["criteria_results"].values()
        )
        
        return validation_results
    
    def _assess_cross_block_flow(self, interaction_data: Dict[str, Any]) -> float:
        """
        Assess the information flow between blocks.
        
        Args:
            interaction_data: Interaction analysis from integration manager
        
        Returns:
            Cross-block information flow score (0-1)
        """
        if not interaction_data:
            return 0.0
        
        # Calculate flow based on data transfer and interaction quality
        transfer_quality_scores = [
            interaction.get('information_transfer', 0) 
            for interaction in interaction_data.values() 
            if isinstance(interaction, dict)
        ]
        
        return np.mean(transfer_quality_scores) if transfer_quality_scores else 0.0
    
    def _perform_domain_specific_validations(
        self, 
        scenario: Dict[str, Any], 
        chunk: Any, 
        response: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Perform domain-specific validations based on scenario type.
        
        Args:
            scenario: Test scenario configuration
            chunk: Processed cognitive chunk
            response: System response
        
        Returns:
            Domain-specific validation results
        """
        domain_validations = {}
        
        # Ethical Reasoning Validation
        if "ethical_concept_depth" in scenario["validation_criteria"]:
            try:
                # Extract ethical concepts
                ethics_data = chunk.get_section_content("ethics_king_section") or {}
                ethical_concepts = ethics_data.get("evaluation", {}).get("principle_scores", {})
                
                # Calculate depth of ethical reasoning
                ethical_depth = len(ethical_concepts) / len(scenario.get("ethical_principles", [1]))
                ethical_validation = ethical_depth >= scenario["validation_criteria"]["ethical_concept_depth"]
                
                domain_validations["ethical_reasoning"] = {
                    "passed": ethical_validation,
                    "value": ethical_depth,
                    "details": f"Ethical principles detected: {list(ethical_concepts.keys())}"
                }
            except Exception as e:
                domain_validations["ethical_reasoning"] = {
                    "passed": False,
                    "value": 0,
                    "details": f"Error in ethical reasoning validation: {str(e)}"
                }
        
        # Uncertainty Handling Validation
        if "uncertainty_handling_quality" in scenario["validation_criteria"]:
            try:
                # Extract wave function and reasoning data
                wave_data = chunk.get_section_content("wave_function_section") or {}
                reasoning_data = chunk.get_section_content("reasoning_section") or {}
                
                # Calculate uncertainty handling quality
                entropy = wave_data.get("entropy", 0.5)
                confidence = reasoning_data.get("confidence_score", 0.5)
                
                # Compute uncertainty handling score based on how well the system manages entropy
                uncertainty_handling = 1 - abs(confidence - (1 - entropy))
                
                domain_validations["uncertainty_handling"] = {
                    "passed": uncertainty_handling >= scenario["validation_criteria"]["uncertainty_handling_quality"],
                    "value": uncertainty_handling,
                    "details": f"Entropy: {entropy:.2f}, Confidence: {confidence:.2f}"
                }
            except Exception as e:
                domain_validations["uncertainty_handling"] = {
                    "passed": False,
                    "value": 0,
                    "details": f"Error in uncertainty handling validation: {str(e)}"
                }
        
        return domain_validations
    
    def _reset_performance_metrics(self):
        """Reset performance metrics before test run."""
        self.performance_metrics = {
            "total_scenarios": len(self.test_scenarios),
            "passed_scenarios": 0,
            "average_processing_time": 0,
            "cross_block_flow_average": 0,
            "ethical_reasoning_quality": 0
        }
    
    def _update_performance_metrics(self, scenario_result: Dict[str, Any]):
        """
        Update performance metrics based on scenario results.
        
        Args:
            scenario_result: Results from a single scenario test
        """
        # Update passed scenarios
        if scenario_result["passed"]:
            self.performance_metrics["passed_scenarios"] += 1
        
        # Accumulate processing times
        self.performance_metrics["average_processing_time"] += scenario_result["processing_time"]
        
        # Assess cross-block flow and ethical reasoning
        validation_results = scenario_result["validation_results"]["criteria_results"]
        
        if "cross_block_flow" in validation_results:
            self.performance_metrics["cross_block_flow_average"] += validation_results["cross_block_flow"]["value"]
        
        if "ethical_reasoning" in validation_results:
            self.performance_metrics["ethical_reasoning_quality"] += validation_results["ethical_reasoning"]["value"]
    
    def _finalize_performance_metrics(self):
        """
        Finalize performance metrics after test run.
        Compute averages and normalize values.
        """
        total_scenarios = self.performance_metrics["total_scenarios"]
        
        # Compute averages
        self.performance_metrics["average_processing_time"] /= total_scenarios
        self.performance_metrics["cross_block_flow_average"] /= total_scenarios
        self.performance_metrics["ethical_reasoning_quality"] /= total_scenarios
        
        # Compute success rate
        self.performance_metrics["success_rate"] = (
            self.performance_metrics["passed_scenarios"] / total_scenarios
        )
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive integration test report.
        
        Returns:
            Detailed integration test report
        """
        # Run integration tests if not already run
        if not self.test_results:
            self.run_integration_tests()
        
        # Compile detailed report
        report = {
            "overall_success": self.test_results["overall_success"],
            "performance_metrics": self.performance_metrics,
            "detailed_scenario_results": {}
        }
        
        # Add detailed results for each scenario
        for scenario_name, scenario_result in self.test_results["scenario_results"].items():
            report["detailed_scenario_results"][scenario_name] = {
                "passed": scenario_result["passed"],
                "processing_time": scenario_result["processing_time"],
                "response": scenario_result["response"],
                "validation_results": scenario_result["validation_results"]
            }
        
        return report
    
    def visualize_test_results(self, test_results: Dict[str, Any], output_file: str = 'integration_test_results.png'):
        """
        Create visualizations of integration test results.
        
        Args:
            test_results: Results from run_integration_tests
            output_file: Path to save the visualization
        """
        import matplotlib.pyplot as plt
        import numpy as np
        
        # Create figure with multiple subplots
        plt.figure(figsize=(15, 10))
        
        # 1. Scenario Performance
        plt.subplot(2, 2, 1)
        scenario_names = list(test_results["scenario_results"].keys())
        passed_scenarios = [result["passed"] for result in test_results["scenario_results"].values()]
        
        plt.bar(scenario_names, passed_scenarios)
        plt.title('Scenario Pass/Fail')
        plt.ylabel('Passed')
        plt.xticks(rotation=45, ha='right')
        plt.ylim(0, 1.1)
        
        # 2. Processing Times
        plt.subplot(2, 2, 2)
        processing_times = [result["processing_time"] for result in test_results["scenario_results"].values()]
        
        plt.bar(scenario_names, processing_times)
        plt.title('Processing Times')
        plt.ylabel('Time (seconds)')
        plt.xticks(rotation=45, ha='right')
        
        # 3. Validation Criteria Performance
        plt.subplot(2, 2, 3)
        criteria_performance = {}
        for scenario_name, scenario_result in test_results["scenario_results"].items():
            criteria_performance[scenario_name] = {
                criteria: result.get("passed", False)
                for criteria, result in scenario_result["validation_results"]["criteria_results"].items()
            }
        
        criteria_names = list(list(criteria_performance.values())[0].keys())
        criteria_pass_rates = []
        
        for criteria in criteria_names:
            pass_rates = [scenario[criteria] for scenario in criteria_performance.values()]
            criteria_pass_rates.append(np.mean(pass_rates))
        
        plt.bar(criteria_names, criteria_pass_rates)
        plt.title('Validation Criteria Performance')
        plt.ylabel('Pass Rate')
        plt.xticks(rotation=45, ha='right')
        plt.ylim(0, 1.1)
        
        # 4. Performance Metrics Radar Chart
        plt.subplot(2, 2, 4, polar=True)
        metrics = test_results.get("performance_metrics", {})
        metric_names = list(metrics.keys())
        
        # Normalize metrics
        normalized_metrics = []
        for metric_value in metrics.values():
            # Skip non-numeric values
            if not isinstance(metric_value, (int, float)):
                normalized_metrics.append(0)
                continue
            
            # Normalize to 0-1 range
            if metric_value > 1:
                normalized_metrics.append(min(1.0, metric_value / 100))
            else:
                normalized_metrics.append(metric_value)
        
        # Close the plot by repeating the first value
        metric_angles = np.linspace(0, 2*np.pi, len(metric_names), endpoint=False)
        normalized_metrics_closed = normalized_metrics + [normalized_metrics[0]]
        metric_angles_closed = np.concatenate((metric_angles, [metric_angles[0]]))
        
        plt.polar(metric_angles_closed, normalized_metrics_closed)
        plt.fill(metric_angles_closed, normalized_metrics_closed, alpha=0.25)
        plt.title('Performance Metrics')
        plt.xticks(metric_angles, metric_names)
        
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
        
        return output_file
    
    def export_results_to_json(self, test_results: Dict[str, Any], output_file: str = 'integration_test_results.json'):
        """
        Export test results to a JSON file for further analysis.
        
        Args:
            test_results: Results from run_integration_tests
            output_file: Path to save the JSON file
        
        Returns:
            Path to the exported JSON file
        """
        import json
        
        with open(output_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        return output_file

def main():
    """
    Example usage of the IntegrationTestSuite.
    
    Demonstrates how to run integration tests and generate reports.
    """
    # Use the real system and integration manager
    from usm import UnifiedSyntheticMind
    from .BlockIntegrationManager import BlockIntegrationManager
    
    # Create system and integration manager
    system = UnifiedSyntheticMind()
    integration_manager = BlockIntegrationManager(system)
    
    # Create test suite
    test_suite = IntegrationTestSuite(system, integration_manager)
    
    # Run integration tests
    test_results = test_suite.run_integration_tests()
    
    # Generate integration report
    integration_report = test_suite.generate_integration_report()
    
    # Visualize results
    visualization_file = test_suite.visualize_test_results(test_results)
    
    # Export results to JSON
    json_export_file = test_suite.export_results_to_json(test_results)
    
    # Print summary
    print("Integration Test Results Summary:")
    print(f"Overall Success: {test_results['overall_success']}")
    print(f"Performance Metrics: {test_results['performance_metrics']}")
    print(f"Visualization saved to: {visualization_file}")
    print(f"JSON results exported to: {json_export_file}")

if __name__ == "__main__":
    main()