import numpy as np
import time
import json
from typing import Dict, Any, List, Optional, Tuple

class SystemIntegrationFramework:
    """
    Comprehensive integration and performance analysis framework 
    for the Unified Synthetic Mind system.
    
    Provides advanced tracking, analysis, and validation of 
    system interactions and performance.
    """
    
    def __init__(self, system):
        """
        Initialize the integration framework.
        
        Args:
            system: The Unified Synthetic Mind system
        """
        self.system = system
        
        # Performance tracking metrics
        self.performance_metrics = {
            "total_interactions": 0,
            "processing_times": [],
            "block_performance": {},
            "first_interaction_time": time.time(),
            "anomalies": []
        }
        
        # Block interaction tracking
        self.block_interaction_tracker = BlockInteractionTracker(system)
        
        # Test scenario management
        self.test_scenarios = self._generate_integration_scenarios()
        
        # Configuration parameters
        self.config = {
            "max_history_length": 100,
            "performance_spike_threshold": 3,  # Standard deviations
            "high_interaction_frequency_threshold": 10  # interactions/second
        }
    
    def _generate_integration_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate comprehensive integration test scenarios.
        
        Returns:
            List of test scenarios
        """
        return [
            {
                "name": "Cross-Block Ethical Reasoning",
                "input": "Discuss the ethical implications of AI in healthcare",
                "expected_blocks": [
                    "SensoryInput", "PatternRecognition", "MemoryStorage", 
                    "InternalCommunication", "ReasoningPlanning", 
                    "EthicsValues", "ActionSelection"
                ],
                "validation_criteria": {
                    "ethical_concept_depth": 0.7,
                    "reasoning_coherence": 0.8,
                    "cross_block_information_flow": 0.75,
                    "processing_time_limit": 2.0
                }
            },
            {
                "name": "Complex Uncertainty Reasoning",
                "input": "Explain the challenges of making decisions under high uncertainty in medical diagnostics",
                "expected_blocks": [
                    "SensoryInput", "PatternRecognition", "MemoryStorage", 
                    "ReasoningPlanning", "EthicsValues", "ActionSelection"
                ],
                "validation_criteria": {
                    "uncertainty_handling_quality": 0.7,
                    "reasoning_depth": 0.8,
                    "cross_block_information_flow": 0.7,
                    "processing_time_limit": 2.5
                }
            }
        ]
    
    def track_block_interaction(self, block_name: str, processing_data: Dict[str, Any]):
        """
        Track performance of a specific block during system processing.
        
        Args:
            block_name: Name of the block
            processing_data: Performance data for the block
        """
        # Update block performance metrics
        if block_name not in self.performance_metrics["block_performance"]:
            self.performance_metrics["block_performance"][block_name] = {
                "total_processing_time": 0,
                "interaction_count": 0,
                "avg_processing_time": 0
            }
        
        block_metrics = self.performance_metrics["block_performance"][block_name]
        block_metrics["total_processing_time"] += processing_data.get('processing_time', 0)
        block_metrics["interaction_count"] += 1
        block_metrics["avg_processing_time"] = (
            block_metrics["total_processing_time"] / block_metrics["interaction_count"]
        )
        
        # Log detailed interaction
        self.block_interaction_tracker.log_interaction(
            block_name, 
            processing_data.get('target_block', 'system'), 
            processing_data.get('data_transfer', None)
        )
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """
        Execute comprehensive integration tests.
        
        Returns:
            Detailed test results
        """
        test_results = {
            "overall_success": True,
            "scenario_results": {}
        }
        
        for scenario in self.test_scenarios:
            scenario_result = self._run_single_scenario(scenario)
            test_results["scenario_results"][scenario["name"]] = scenario_result
            
            # Update overall success
            test_results["overall_success"] &= scenario_result["passed"]
        
        return test_results
    
    def _run_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single integration test scenario.
        
        Args:
            scenario: Test scenario configuration
        
        Returns:
            Detailed scenario test results
        """
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
            Validation results
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
        cross_block_flow = self._assess_cross_block_flow(chunk)
        flow_validation = cross_block_flow >= scenario["validation_criteria"].get("cross_block_information_flow", 0.6)
        validation_results["criteria_results"]["cross_block_flow"] = {
            "passed": flow_validation,
            "value": cross_block_flow,
            "details": f"Cross-block information flow: {cross_block_flow:.2f}"
        }
        
        # 4. Response Quality Validation
        response_length_validation = len(response) > 50
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
    
    def _assess_cross_block_flow(self, chunk: Any) -> float:
        """
        Assess the information flow between blocks.
        
        Args:
            chunk: Cognitive chunk to analyze
        
        Returns:
            Cross-block information flow score (0-1)
        """
        sections = chunk.sections.keys() if hasattr(chunk, 'sections') else []
        unique_sections = len(set(sections))
        return min(1.0, unique_sections / 10.0)
    
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
                ethical_depth = len(ethical_concepts) / 5.0  # Normalize against expected principles
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
        
        return domain_validations
    
    def generate_integration_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive integration test report.
        
        Args:
            test_results: Results from run_integration_tests
        
        Returns:
            Detailed integration test report
        """
        report = {
            "total_scenarios": len(test_results["scenario_results"]),
            "passed_scenarios": sum(
                1 for result in test_results["scenario_results"].values() 
                if result["passed"]
            ),
            "overall_success_rate": 0.0,
            "scenario_details": {}
        }
        
        # Calculate overall success rate
        report["overall_success_rate"] = (
            report["passed_scenarios"] / 
            max(1, report["total_scenarios"])
        )
        
        # Detailed scenario breakdown
        for scenario_name, scenario_result in test_results["scenario_results"].items():
            report["scenario_details"][scenario_name] = {
                "passed": scenario_result["passed"],
                "processing_time": scenario_result.get("processing_time", 0),
                "validation_results": scenario_result.get("validation_results", {})
            }
        
        return report


class BlockInteractionTracker:
    """
    Advanced tracking and analysis of block interactions.
    """
    
    def __init__(self, system):
        """
        Initialize the Block Interaction Tracker.
        
        Args:
            system: The Unified Synthetic Mind system
        """
        self.system = system
        
        # Detailed interaction logs
        self.detailed_interaction_logs: Dict[str, List[Dict[str, Any]]] = {}
        
        # Cross-block communication patterns
        self.communication_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.config = {
            "max_log_entries": 1000,
            "semantic_extraction_depth": 3
        }
    
    def log_interaction(
        self, 
        source_block: str, 
        target_block: str, 
        data_transfer: Any, 
        interaction_type: str = 'data_flow'
    ):
        """
        Log detailed interactions between blocks.
        
        Args:
            source_block: Name of the source block
            target_block: Name of the target block
            data_transfer: Data being transferred between blocks
            interaction_type: Type of interaction
        """
        # Create interaction key
        interaction_key = f"{source_block}->{target_block}"
        
        # Initialize log if not exists
        if interaction_key not in self.detailed_interaction_logs:
            self.detailed_interaction_logs[interaction_key] = []
        
        # Limit log entries
        if len(self.detailed_interaction_logs[interaction_key]) >= self.config['max_log_entries']:
            self.detailed_interaction_logs[interaction_key].pop(0)
        
        # Create detailed interaction log entry
        interaction_entry = {
            "timestamp": time.time(),
            "source_block": source_block,
            "target_block": target_block,
            "interaction_type": interaction_type,
            "data_volume": len(str(data_transfer)),
            "data_type": type(data_transfer).__name__,
            "context_details": self._extract_context_details(data_transfer)
        }
        
        # Log the interaction
        self.detailed_interaction_logs[interaction_key].append(interaction_entry)
        
        # Update communication patterns
        self._update_communication_patterns(interaction_entry)
    
    def _extract_context_details(self, data_transfer: Any) -> Dict[str, Any]:
        """
        Extract contextual information from data transfers.
        
        Args:
            data_transfer: Data being transferred between blocks
        
        Returns:
            Dictionary of contextual details
        """
        context_details = {
            "basic_type": type(data_transfer).__name__,
            "size": len(str(data_transfer)) if hasattr(data_transfer, '__len__') else 'N/A'
        }
        
        # Advanced context extraction based on data type
        try:
            if hasattr(data_transfer, 'sections'):
                # For CognitiveChunk-like objects
                context_details.update({
                    "section_names": list(data_transfer.sections.keys()),
                    "section_count": len(data_transfer.sections)
                })
            elif isinstance(data_transfer, dict):
                # For dictionary-like objects
                context_details.update({
                    "keys": list(data_transfer.keys()),
                    "value_types": {k: type(v).__name__ for k, v in data_transfer.items()}
                })
            elif hasattr(data_transfer, '__dict__'):
                # For object-like structures
                context_details.update({
                    "object_attributes": list(data_transfer.__dict__.keys())
                })
        except Exception as e:
            context_details["extraction_error"] = str(e)
        
        return context_details
    
    def _update_communication_patterns(self, interaction_entry: Dict[str, Any]):
        """
        Update cross-block communication patterns.
        
        Args:
            interaction_entry: Detailed interaction log entry
        """
        key = f"{interaction_entry['source_block']}->{interaction_entry['target_block']}"
        
        if key not in self.communication_patterns:
            self.communication_patterns[key] = {
                "total_interactions": 0,
                "total_data_volume": 0,
                "interaction_timestamps": [],
                "interaction_types": {}
            }
        
        pattern = self.communication_patterns[key]
        pattern["total_interactions"] += 1
        pattern["total_data_volume"] += interaction_entry["data_volume"]
        pattern["interaction_timestamps"].append(interaction_entry["timestamp"])
        
        # Track interaction types
        interaction_type = interaction_entry["interaction_type"]
        if interaction_type not in pattern["interaction_types"]:
            pattern["interaction_types"][interaction_type] = 0
        pattern["interaction_types"][interaction_type] += 1
    
    def analyze_communication_patterns(self) -> Dict[str, Any]:
        """
        Analyze and summarize cross-block communication patterns.
        
        Returns:
            Comprehensive communication pattern analysis
        """
        communication_analysis = {}
        
        for interaction_key, pattern in self.communication_patterns.items():
            # Calculate interaction frequency
            if pattern["interaction_timestamps"]:
                total_time = pattern["interaction_timestamps"][-1] - pattern["interaction_timestamps"][0]
                interaction_frequency = pattern["total_interactions"] / max(1, total_time)
            else:
                interaction_frequency = 0
            
            communication_analysis[interaction_key] = {
                "total_interactions": pattern["total_interactions"],
                "total_data_volume": pattern["total_data_volume"],
                "interaction_frequency": interaction_frequency,
                "interaction_types": pattern["interaction_types"],
                "avg_data_volume": pattern["total_data_volume"] / max(1, pattern["total_interactions"])
            }
        
        return communication_analysis
    
    def export_interaction_logs(self) -> str:
        """
        Export interaction logs to a JSON string.
        
        Returns:
            JSON string of interaction logs
        """
        export_data = {
            "detailed_interaction_logs": self.detailed_interaction_logs,
            "communication_patterns": self.communication_patterns
        }
        
        # Convert to JSON
        return json.dumps(export_data, indent=2)
    
    def import_interaction_logs(self, log_data: str):
        """
        Import interaction logs from a JSON string.
        
        Args:
            log_data: JSON string of interaction logs
        """
        try:
            imported_data = json.loads(log_data)
            self.detailed_interaction_logs = imported_data.get("detailed_interaction_logs", {})
            self.communication_patterns = imported_data.get("communication_patterns", {})
        except Exception as e:
            print(f"Error importing logs: {e}")
    
    def reset_tracking(self):
        """
        Reset all tracking data.
        """
        self.detailed_interaction_logs.clear()
        self.communication_patterns.clear()


def create_integration_testing_module(system):
    """
    Create and configure the integration testing module for a system.
    
    Args:
        system: The Unified Synthetic Mind system
    
    Returns:
        Configured SystemIntegrationFramework instance
    """
    # Create integration framework
    integration_framework = SystemIntegrationFramework(system)
    
    # Attach integration framework to system if possible
    if hasattr(system, 'integration_tools'):
        system.integration_tools = integration_framework
    
    return integration_framework


def main():
    """
    Demonstration of the integration testing framework.
    """
    # Use the real system module
    from usm import UnifiedSyntheticMind
    
    # Create system
    system = UnifiedSyntheticMind()
    
    # Create integration testing module
    integration_framework = create_integration_testing_module(system)
    
    # Run integration tests
    test_results = integration_framework.run_integration_tests()
    
    # Generate integration report
    report = integration_framework.generate_integration_report(test_results)
    
    # Print report
    print(json.dumps(report, indent=2))
    
    # Optional: Export interaction logs
    interaction_logs = integration_framework.block_interaction_tracker.export_interaction_logs()
    with open('system_integration_logs.json', 'w') as f:
        f.write(interaction_logs)


if __name__ == "__main__":
    main()