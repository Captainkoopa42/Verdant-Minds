import time
from typing import Dict, List, Any, Optional, Set

from src.blocks.base_block import BaseBlock
from src.core.cognitive_chunk import CognitiveChunk

class InternalCommunicationBlock(BaseBlock):
    """
    Block 4: Internal Communication
    
    Orchestrates information flow between different components of the system,
    serving as a cognitive integration hub and creating dynamic information pathways
    based on relevance and priority.
    """
    
    def __init__(self):
        """Initialize the Internal Communication block."""
        super().__init__("InternalCommunication")
        
        # Communication channels configuration
        self.channels = {
            "memory_retrieval": {"priority": 0.8, "recipients": ["ReasoningPlanning", "EthicsValues"]},
            "pattern_insights": {"priority": 0.7, "recipients": ["MemoryStorage", "ReasoningPlanning"]},
            "ethical_concerns": {"priority": 0.9, "recipients": ["ReasoningPlanning", "ActionSelection"]},
            "reasoning_results": {"priority": 0.8, "recipients": ["ActionSelection", "LanguageProcessing"]},
            "system_feedback": {"priority": 0.6, "recipients": ["ContinualLearning"]}
        }
        
        # Cross-component message history for context tracking
        self.message_history = []
        self.max_history_size = 100
        
        # Information routing metadata
        self.routing_statistics = {}
        
        # Information prioritization configuration
        self.priority_thresholds = {
            "critical": 0.9,
            "high": 0.7,
            "medium": 0.5,
            "low": 0.3
        }
        
        # Working memory buffer
        self.working_memory = {}
        self.working_memory_capacity = 10
        self.working_memory_decay_rate = 0.05
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a cognitive chunk through internal communication.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk with integrated information
        """
        # Extract information from previous processing stages
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        
        # Analyze information to determine routing and priorities
        information_analysis = self._analyze_information(sensory_data, pattern_data, memory_data)
        
        # Determine information priorities for downstream processing
        information_priorities = self._determine_priorities(information_analysis)
        
        # Update working memory with current information
        self._update_working_memory(information_analysis)
        
        # Establish processing pathways based on content and context
        processing_pathways = self._establish_pathways(information_analysis, information_priorities)
        
        # Create integrated context for subsequent processing
        integrated_context = self._integrate_context(chunk, information_analysis)
        
        # Identify cross-block insights that emerge from multiple sources
        cross_block_insights = self._identify_cross_block_insights(chunk, integrated_context)
        
        # Compile internal communication data
        communication_data = {
            "information_analysis": information_analysis,
            "information_priorities": information_priorities,
            "processing_pathways": processing_pathways,
            "integrated_context": integrated_context,
            "cross_block_insights": cross_block_insights,
            "working_memory_state": list(self.working_memory.keys()),
            "processed_timestamp": time.time()
        }
        
        # Update chunk with internal communication insights
        chunk.update_section("internal_communication_section", communication_data)
        
        # Update message history
        self._update_message_history(communication_data)
        
        # Log processing details
        self.log_process(chunk, "internal_communication", {
            "pathway_count": len(processing_pathways),
            "insight_count": len(cross_block_insights),
            "priority_levels": information_priorities
        })
        
        return chunk
    
    def _analyze_information(
        self, 
        sensory_data: Dict[str, Any], 
        pattern_data: Dict[str, Any], 
        memory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze information from different sources to determine key elements.
        
        Args:
            sensory_data: Data from sensory input
            pattern_data: Data from pattern recognition
            memory_data: Data from memory storage
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "primary_concepts": [],
            "relationship_data": [],
            "confidence_scores": {},
            "information_sources": {},
            "context_markers": []
        }
        
        # Extract primary concepts from pattern data
        if "extracted_concepts" in pattern_data:
            concepts = []
            for concept in pattern_data["extracted_concepts"]:
                if isinstance(concept, dict) and "value" in concept:
                    concept_value = concept["value"]
                    salience = concept.get("salience", 0.5)
                    concepts.append((concept_value, salience))
                elif isinstance(concept, str):
                    concepts.append((concept, 0.5))
            
            # Sort by salience and take top N
            sorted_concepts = sorted(concepts, key=lambda x: x[1], reverse=True)
            analysis["primary_concepts"] = [c[0] for c in sorted_concepts[:5]]
            
            # Add confidence scores
            for concept, salience in sorted_concepts:
                analysis["confidence_scores"][concept] = salience
                analysis["information_sources"][concept] = "pattern_recognition"
        
        # Extract concepts from memory data
        retrieved_concepts = memory_data.get("retrieved_concepts") or []
        if retrieved_concepts:
            for concept in retrieved_concepts:
                if isinstance(concept, tuple) and len(concept) >= 2:
                    concept_value, relevance = concept
                    if concept_value not in analysis["primary_concepts"] and relevance > 0.5:
                        analysis["primary_concepts"].append(concept_value)
                        analysis["confidence_scores"][concept_value] = relevance
                        analysis["information_sources"][concept_value] = "memory"
                elif isinstance(concept, str):
                    if concept not in analysis["primary_concepts"]:
                        analysis["primary_concepts"].append(concept)
                        analysis["confidence_scores"][concept] = 0.5
                        analysis["information_sources"][concept] = "memory"
        
        # Extract relationship data
        if "detected_patterns" in pattern_data:
            for pattern in pattern_data["detected_patterns"]:
                pattern_type = pattern.get("type", "")
                pattern_value = pattern.get("value", "")
                
                if pattern_type == "relationship" and pattern_value:
                    analysis["relationship_data"].append({
                        "type": pattern_type,
                        "value": pattern_value,
                        "confidence": pattern.get("confidence", 0.5)
                    })
        
        # Extract context markers from sensory data
        if "sentiment" in sensory_data:
            sentiment = sensory_data["sentiment"]
            if isinstance(sentiment, dict):
                for key, value in sentiment.items():
                    if value > 0.5:
                        analysis["context_markers"].append(f"sentiment:{key}")
        
        if "intent" in sensory_data:
            intent = sensory_data["intent"]
            if isinstance(intent, str):
                analysis["context_markers"].append(f"intent:{intent}")
            elif isinstance(intent, dict) and "type" in intent:
                analysis["context_markers"].append(f"intent:{intent['type']}")
        
        return analysis
    
    def _determine_priorities(self, information_analysis: Dict[str, Any]) -> Dict[str, float]:
        """
        Determine processing priorities for different aspects of information.
        
        Args:
            information_analysis: Analysis of current information
            
        Returns:
            Dictionary mapping processing aspects to priority levels
        """
        # Initialize with default priorities
        priorities = {
            "memory_expansion": 0.5,  # Priority for memory storage operations
            "ethical_review": 0.5,    # Priority for ethical evaluation
            "reasoning_depth": 0.5,   # Priority for deep reasoning
            "action_selection": 0.6,  # Priority for selecting actions
            "language_processing": 0.5 # Priority for language generation
        }
        
        # Adjust based on confidence scores
        avg_confidence = 0.5
        if information_analysis["confidence_scores"]:
            avg_confidence = sum(information_analysis["confidence_scores"].values()) / len(information_analysis["confidence_scores"])
        
        # Higher confidence → Higher reasoning priority
        if avg_confidence > 0.7:
            priorities["reasoning_depth"] += 0.2
            priorities["action_selection"] += 0.1
        elif avg_confidence < 0.4:
            # Lower confidence → Higher memory and ethical priority
            priorities["memory_expansion"] += 0.2
            priorities["ethical_review"] += 0.1
        
        # Adjust based on context markers
        for marker in information_analysis["context_markers"]:
            if marker.startswith("sentiment:negative"):
                # Negative sentiment → Higher ethical priority
                priorities["ethical_review"] += 0.2
                priorities["reasoning_depth"] += 0.1
            elif marker.startswith("intent:question"):
                # Questions → Higher reasoning and memory priority
                priorities["reasoning_depth"] += 0.2
                priorities["memory_expansion"] += 0.1
            elif marker.startswith("intent:command"):
                # Commands → Higher action priority
                priorities["action_selection"] += 0.2
                priorities["language_processing"] += 0.1
        
        # Adjust based on relationship data
        if len(information_analysis["relationship_data"]) > 2:
            # Multiple relationships → Higher reasoning priority
            priorities["reasoning_depth"] += 0.1
            priorities["memory_expansion"] += 0.1
        
        # Normalize priorities to avoid exceeding 1.0
        for key in priorities:
            priorities[key] = min(1.0, priorities[key])
        
        return priorities
    
    def _update_working_memory(self, information_analysis: Dict[str, Any]):
        """
        Update working memory with current information.
        
        Args:
            information_analysis: Analysis of current information
        """
        # Apply decay to existing working memory items
        for key in list(self.working_memory.keys()):
            self.working_memory[key]["activation"] -= self.working_memory_decay_rate
            
            # Remove items with low activation
            if self.working_memory[key]["activation"] <= 0:
                del self.working_memory[key]
        
        # Add new concepts to working memory
        for concept in information_analysis["primary_concepts"]:
            if concept in self.working_memory:
                # Refresh existing item
                self.working_memory[concept]["activation"] = 1.0
                self.working_memory[concept]["access_count"] += 1
            else:
                # Add new item
                self.working_memory[concept] = {
                    "activation": 1.0,
                    "timestamp": time.time(),
                    "source": information_analysis["information_sources"].get(concept, "unknown"),
                    "confidence": information_analysis["confidence_scores"].get(concept, 0.5),
                    "access_count": 1
                }
        
        # Ensure working memory doesn't exceed capacity
        if len(self.working_memory) > self.working_memory_capacity:
            # Remove least activated items
            items_to_remove = sorted(
                self.working_memory.items(),
                key=lambda x: x[1]["activation"]
            )[:len(self.working_memory) - self.working_memory_capacity]
            
            for key, _ in items_to_remove:
                del self.working_memory[key]
    
    def _establish_pathways(
        self, 
        information_analysis: Dict[str, Any], 
        information_priorities: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Establish processing pathways based on information content and priorities.
        
        Args:
            information_analysis: Analysis of current information
            information_priorities: Priorities for different processing aspects
            
        Returns:
            List of processing pathways
        """
        pathways = []
        
        # Create memory pathway if relevant
        if information_priorities["memory_expansion"] > self.priority_thresholds["medium"]:
            memory_concepts = [
                c for c in information_analysis["primary_concepts"] 
                if information_analysis["information_sources"].get(c) != "memory"
            ]
            
            if memory_concepts:
                pathways.append({
                    "target": "MemoryStorage",
                    "priority": information_priorities["memory_expansion"],
                    "content": {
                        "concepts": memory_concepts,
                        "operation": "store_and_connect"
                    }
                })
        
        # Create reasoning pathway if relevant
        if information_priorities["reasoning_depth"] > self.priority_thresholds["medium"]:
            relevant_concepts = information_analysis["primary_concepts"]
            
            pathways.append({
                "target": "ReasoningPlanning",
                "priority": information_priorities["reasoning_depth"],
                "content": {
                    "concepts": relevant_concepts,
                    "relationships": information_analysis["relationship_data"],
                    "required_depth": map_priority_to_depth(information_priorities["reasoning_depth"])
                }
            })
        
        # Create ethics pathway if relevant
        if information_priorities["ethical_review"] > self.priority_thresholds["medium"]:
            pathways.append({
                "target": "EthicsValues",
                "priority": information_priorities["ethical_review"],
                "content": {
                    "concepts": information_analysis["primary_concepts"],
                    "context_markers": information_analysis["context_markers"],
                    "review_level": "standard" if information_priorities["ethical_review"] < self.priority_thresholds["high"] else "comprehensive"
                }
            })
        
        # Create action pathway
        pathways.append({
            "target": "ActionSelection",
            "priority": information_priorities["action_selection"],
            "content": {
                "primary_concepts": information_analysis["primary_concepts"][:3],
                "confidence_level": avg_dict_values(information_analysis["confidence_scores"])
            }
        })
        
        # Update routing statistics
        for pathway in pathways:
            target = pathway["target"]
            if target not in self.routing_statistics:
                self.routing_statistics[target] = {
                    "total_routes": 0,
                    "avg_priority": 0
                }
            
            self.routing_statistics[target]["total_routes"] += 1
            # Update average priority with exponential moving average
            old_avg = self.routing_statistics[target]["avg_priority"]
            new_avg = old_avg * 0.9 + pathway["priority"] * 0.1
            self.routing_statistics[target]["avg_priority"] = new_avg
        
        return pathways
    
    def _integrate_context(self, chunk: CognitiveChunk, information_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an integrated context combining information from multiple sources.
        
        Args:
            chunk: Current cognitive chunk
            information_analysis: Analysis of current information
            
        Returns:
            Integrated context dictionary
        """
        # Start with basic context from current analysis
        integrated_context = {
            "primary_concepts": information_analysis["primary_concepts"],
            "confidence_scores": information_analysis["confidence_scores"],
            "context_markers": information_analysis["context_markers"]
        }

        # Retrieve memory data safely
        memory_data = chunk.get_section_content("memory_section") or {}
        
        # Add ethical flags if available
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        if ethics_data and "evaluation" in ethics_data:
            evaluation = ethics_data["evaluation"]
            integrated_context["ethical_flags"] = evaluation.get("concerns", [])
            integrated_context["ethical_status"] = evaluation.get("status", "unknown")
        
        # Add key inferences if available
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        if reasoning_data and "inferences" in reasoning_data:
            inferences = reasoning_data["inferences"]
            key_inferences = []
            
            # Collect key inferences from each type
            for inf_type, inf_list in inferences.items():
                if inf_list:
                    # Add the most important inference from each type
                    key_inferences.append({
                        "type": inf_type,
                        "content": inf_list[0]
                    })
            
            integrated_context["key_inferences"] = key_inferences
        
        # Add memory activation levels if available
        activation_levels = memory_data.get("activation_levels")
        if activation_levels:
            integrated_context["memory_activation"] = activation_levels
        
        return integrated_context
    
    def _identify_cross_block_insights(
        self, 
        chunk: CognitiveChunk, 
        integrated_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify insights that emerge from combining information across blocks.
        
        Args:
            chunk: Current cognitive chunk
            integrated_context: Integrated context information
            
        Returns:
            List of cross-block insights
        """
        insights = []
        
        # Extract relevant data from various blocks
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        
        # Check for ethics-memory resonance
        retrieved_concepts = memory_data.get("retrieved_concepts") or []
        if retrieved_concepts and ethics_data.get("evaluation"):
            ethical_concerns = ethics_data["evaluation"].get("concerns", [])

            # Check if any ethical concerns directly relate to retrieved memory concepts
            overlapping_concepts = set(
                [c[0] if isinstance(c, tuple) else c for c in retrieved_concepts]
            ).intersection(ethical_concerns)
            
            if overlapping_concepts:
                insights.append({
                    "type": "ethics_memory_resonance",
                    "content": f"Ethical concerns about {', '.join(overlapping_concepts)} are supported by relevant memories",
                    "source_blocks": ["MemoryStorage", "EthicsValues"],
                    "importance": 0.8
                })
        
        # Check for pattern-reasoning synthesis
        if pattern_data.get("detected_patterns") and reasoning_data.get("inferences"):
            pattern_types = set(p.get("type", "") for p in pattern_data["detected_patterns"])
            inference_types = set(reasoning_data["inferences"].keys())
            
            if "relationship" in pattern_types and "deductive" in inference_types:
                # Patterns showing relationships combined with deductive reasoning
                deductive_inferences = reasoning_data["inferences"].get("deductive", [])
                
                if deductive_inferences:
                    insights.append({
                        "type": "pattern_reasoning_synthesis",
                        "content": f"Detected relationships enabled deductive reasoning: {deductive_inferences[0]}",
                        "source_blocks": ["PatternRecognition", "ReasoningPlanning"],
                        "importance": 0.7
                    })
        
        # Check for confidence-uncertainty alignment
        if integrated_context.get("confidence_scores") and reasoning_data.get("confidence_score"):
            avg_confidence = avg_dict_values(integrated_context["confidence_scores"])
            reasoning_confidence = reasoning_data["confidence_score"]
            
            confidence_delta = abs(avg_confidence - reasoning_confidence)
            
            if confidence_delta > 0.3:
                # Large discrepancy between concept confidence and reasoning confidence
                insights.append({
                    "type": "confidence_uncertainty_mismatch",
                    "content": f"Significant discrepancy between concept confidence ({avg_confidence:.2f}) and reasoning confidence ({reasoning_confidence:.2f})",
                    "source_blocks": ["PatternRecognition", "ReasoningPlanning", "MemoryStorage"],
                    "importance": 0.6
                })
        
        # Check for ethical action alignment
        if integrated_context.get("ethical_status") and action_data.get("selected_action"):
            ethical_status = integrated_context["ethical_status"]
            selected_action = action_data["selected_action"]
            
            if ethical_status == "review_needed" and selected_action != "defer_decision":
                insights.append({
                    "type": "ethics_action_misalignment",
                    "content": f"Ethical status requires review but selected action is {selected_action}",
                    "source_blocks": ["EthicsValues", "ActionSelection"],
                    "importance": 0.9
                })
        
        return insights
    
    def _update_message_history(self, communication_data: Dict[str, Any]):
        """
        Update message history with current communication data.
        
        Args:
            communication_data: Current communication data
        """
        # Add to history
        self.message_history.append({
            "timestamp": time.time(),
            "pathways": communication_data["processing_pathways"],
            "priorities": communication_data["information_priorities"],
            "insights": communication_data["cross_block_insights"]
        })
        
        # Limit history size
        if len(self.message_history) > self.max_history_size:
            self.message_history.pop(0)
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about information routing.
        
        Returns:
            Dictionary with routing statistics
        """
        return {
            "total_messages": sum(stats["total_routes"] for stats in self.routing_statistics.values()),
            "route_distribution": {
                target: stats["total_routes"] for target, stats in self.routing_statistics.items()
            },
            "priority_averages": {
                target: stats["avg_priority"] for target, stats in self.routing_statistics.items()
            }
        }


# Utility functions

def avg_dict_values(d: Dict[str, float]) -> float:
    """Calculate average of dictionary values."""
    if not d:
        return 0.5
    return sum(d.values()) / len(d)

def map_priority_to_depth(priority: float) -> str:
    """Map priority value to reasoning depth level."""
    if priority > 0.85:
        return "exhaustive"
    elif priority > 0.7:
        return "comprehensive"
    elif priority > 0.5:
        return "standard"
    else:
        return "basic"