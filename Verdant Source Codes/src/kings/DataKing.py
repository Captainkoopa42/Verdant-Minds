import numpy as np
import time
from typing import Dict, List, Tuple, Any, Optional, Set

from core.cognitive_chunk import CognitiveChunk
from .base_king import BaseKing

class DataKing(BaseKing):
    """
    Data King: Guardian of information quality, relevance, and integrity.
    
    The Data King oversees information intake, pattern recognition, and memory storage.
    It ensures data quality, assesses relevance, and efficiently manages information flow.
    Serves as one of the three kings in the governance layer of the Unified Synthetic Mind.
    """
    
    def __init__(self):
        """Initialize the Data King with information governance capabilities."""
        super().__init__("DataKing")
        
        # Blocks supervised by the Data King
        self.blocks_supervised = ["SensoryInput", "PatternRecognition", "MemoryStorage"]
        
        # Information quality thresholds
        self.information_quality_threshold = 0.6
        self.novelty_threshold = 0.3
        
        # Relevance tracking
        self.relevance_cache = {}  # Topic -> relevance score
        
        # Quality assessment parameters
        self.quality_assessment_params = {
            "precision_weight": 0.25,
            "accuracy_weight": 0.30,
            "consistency_weight": 0.25,
            "completeness_weight": 0.20
        }
        
        # Performance metrics
        self.oversight_metrics = {
            "total_oversights": 0,
            "quality_improvements": 0,
            "novelty_detections": 0,
            "relevance_assessments": 0,
            "avg_information_quality": 0.5
        }

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Wrapper to conform to block interface."""
        print(f"DataKing processing chunk {chunk.chunk_id}")
        return self.oversee_processing(chunk)
    
    def oversee_processing(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Oversees information processing, enhancing data quality and relevance.
        
        Args:
            chunk: The cognitive chunk to oversee
            
        Returns:
            Processed cognitive chunk with Data King's oversight
        """
        # Extract relevant data from supervised blocks
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        
        # Check information quality using multiple dimensions
        quality_score = self._evaluate_information_quality(sensory_data, pattern_data)
        
        # Evaluate information novelty
        novelty_score = self._evaluate_novelty(pattern_data, memory_data)
        
        # Determine relevance to current context
        relevance_score = self._evaluate_relevance(pattern_data, memory_data)
        
        # Apply data governance policies
        governance_actions = self._apply_data_governance(chunk, quality_score, novelty_score, relevance_score)
        
        # Update chunk with Data King's oversight information
        data_king_oversight = {
            "information_quality": quality_score,
            "novelty": novelty_score,
            "relevance": relevance_score,
            "governance_actions": governance_actions,
            "oversight_timestamp": time.time()
        }
        
        # Create or update a dedicated section for the Data King
        chunk.update_section("data_king_section", data_king_oversight)
        
        # Log the influence
        self.log_influence(chunk, "data_oversight", 
                          {"quality": quality_score, 
                           "novelty": novelty_score,
                           "relevance": relevance_score,
                           "actions_taken": len(governance_actions)})
        
        # Update metrics
        self._update_metrics(quality_score, novelty_score, relevance_score)
        
        return chunk
    
    def _evaluate_information_quality(self, sensory_data: Dict[str, Any], pattern_data: Dict[str, Any]) -> float:
        """
        Evaluates the quality of incoming information across multiple dimensions.
        
        Args:
            sensory_data: Data from sensory input
            pattern_data: Data from pattern recognition
            
        Returns:
            Quality score (0-1)
        """
        # Initialize with moderate quality
        quality_score = 0.5
        
        # Factor 1: Information volume and richness
        token_count = sensory_data.get("token_count", 0)
        if token_count > 50:
            quality_score += 0.1
        elif token_count < 10:
            quality_score -= 0.1
            
        # Factor 2: Pattern clarity and confidence
        patterns = pattern_data.get("detected_patterns", [])
        if patterns:
            # Calculate average confidence of detected patterns
            pattern_confidence = sum(p.get("confidence", 0) for p in patterns) / max(1, len(patterns))
            # Adjust quality based on pattern confidence
            quality_score += 0.2 * pattern_confidence
            
        # Factor 3: Semantic clarity
        intent = pattern_data.get("intent", "")
        if intent in ["question", "command", "statement"]:
            quality_score += 0.1
        elif intent == "unclear":
            quality_score -= 0.1
            
        # Factor 4: Internal consistency
        consistency_score = self._assess_consistency(sensory_data, pattern_data)
        quality_score += 0.15 * consistency_score
            
        # Normalize score to 0-1 range
        return max(0.1, min(1.0, quality_score))
    
    def _assess_consistency(self, sensory_data: Dict[str, Any], pattern_data: Dict[str, Any]) -> float:
        """
        Assesses the internal consistency of the information.
        
        Args:
            sensory_data: Data from sensory input
            pattern_data: Data from pattern recognition
            
        Returns:
            Consistency score (0-1)
        """
        consistency_score = 0.5  # Default moderate consistency
        
        # Check for contradictions in patterns
        patterns = pattern_data.get("detected_patterns", [])
        contradictions = 0
        
        if len(patterns) > 1:
            # Simple contradiction detection between patterns
            for i, pattern1 in enumerate(patterns):
                for pattern2 in patterns[i+1:]:
                    if self._are_contradictory(pattern1, pattern2):
                        contradictions += 1
        
        # Adjust consistency based on contradictions
        if contradictions > 0:
            consistency_score -= 0.1 * min(5, contradictions)
        else:
            consistency_score += 0.1  # Bonus for no contradictions
            
        # Check alignment between input and patterns
        extracted_concepts = pattern_data.get("extracted_concepts", [])
        input_text = sensory_data.get("input_text", "").lower()
        
        concept_alignment = 0
        for concept in extracted_concepts:
            concept_text = concept.get("value", concept) if isinstance(concept, dict) else concept
            if isinstance(concept_text, str) and concept_text.lower() in input_text:
                concept_alignment += 1
                
        if extracted_concepts:
            alignment_ratio = concept_alignment / len(extracted_concepts)
            consistency_score += 0.2 * alignment_ratio
        
        return max(0.0, min(1.0, consistency_score))
    
    def _are_contradictory(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> bool:
        """Check if two patterns contradict each other."""
        # This is a simplified implementation
        # In a full system, this would include more sophisticated contradiction detection
        
        # Check for simple negation contradictions
        if pattern1.get("type") == pattern2.get("type"):
            value1 = str(pattern1.get("value", "")).lower()
            value2 = str(pattern2.get("value", "")).lower()
            
            contradictory_pairs = [
                ("true", "false"),
                ("yes", "no"),
                ("always", "never"),
                ("all", "none"),
                ("increase", "decrease"),
                ("positive", "negative")
            ]
            
            for pos, neg in contradictory_pairs:
                if (pos in value1 and neg in value2) or (neg in value1 and pos in value2):
                    return True
        
        return False
    
    def _evaluate_novelty(self, pattern_data: Dict[str, Any], memory_data: Dict[str, Any]) -> float:
        """
        Evaluates how novel the current information is compared to existing knowledge.
        
        Args:
            pattern_data: Data from pattern recognition
            memory_data: Data from memory storage
            
        Returns:
            Novelty score (0-1)
        """
        novelty_score = 0.5  # Default moderate novelty
        
        # Extract concepts from pattern data
        current_concepts = []
        for concept in pattern_data.get("extracted_concepts", []):
            if isinstance(concept, dict) and "value" in concept:
                current_concepts.append(concept["value"])
            elif isinstance(concept, str):
                current_concepts.append(concept)
        
        # Get concepts from memory
        memory_concepts = []
        for item in memory_data.get("retrieved_concepts", []):
            if isinstance(item, tuple) and len(item) >= 2:
                memory_concepts.append(item[0])
            elif isinstance(item, str):
                memory_concepts.append(item)
        
        # Calculate Jaccard similarity between current concepts and memory
        if current_concepts and memory_concepts:
            current_set = set(current_concepts)
            memory_set = set(memory_concepts)
            
            # Calculate overlap
            intersection = current_set.intersection(memory_set)
            union = current_set.union(memory_set)
            
            if union:
                similarity = len(intersection) / len(union)
                # Novelty is inverse of similarity
                novelty_score = 1.0 - similarity
        
        # Bonus for completely new concepts
        new_concepts = [c for c in current_concepts if c not in memory_concepts]
        if new_concepts:
            novelty_bonus = 0.1 * min(0.5, len(new_concepts) / 10)
            novelty_score += novelty_bonus
            
        # Adjust based on pattern novelty
        patterns = pattern_data.get("detected_patterns", [])
        if patterns:
            pattern_types = [p.get("type") for p in patterns]
            if "novel_association" in pattern_types or "unexpected_pattern" in pattern_types:
                novelty_score += 0.15
        
        # Normalize score
        return max(0.1, min(1.0, novelty_score))
    
    def _evaluate_relevance(self, pattern_data: Dict[str, Any], memory_data: Dict[str, Any]) -> float:
        """
        Evaluates the relevance of information to current context and goals.
        
        Args:
            pattern_data: Data from pattern recognition
            memory_data: Data from memory storage
            
        Returns:
            Relevance score (0-1)
        """
        relevance_score = 0.5  # Default moderate relevance
        
        # Get topic from patterns
        topic = None
        for pattern in pattern_data.get("detected_patterns", []):
            if pattern.get("type") == "topic":
                topic = pattern.get("value")
                break
        
        # If we have a topic, check relevance cache or compute new score
        if topic:
            if topic in self.relevance_cache:
                # Apply temporal decay to cached relevance
                time_factor = 0.9  # Decay factor
                relevance_score = self.relevance_cache[topic] * time_factor
            else:
                # New topic - assign initial relevance based on memory coherence
                coherence = memory_data.get("coherence_score", 0.5)
                relevance_score = 0.3 + 0.6 * coherence  # Scale to 0.3-0.9 range
                
                # Cache the relevance score
                self.relevance_cache[topic] = relevance_score
        
        # Adjust based on memory activation
        activation_levels = memory_data.get("activation_levels", {})
        if activation_levels:
            avg_activation = sum(activation_levels.values()) / max(1, len(activation_levels))
            # Boost relevance if memory is highly activated
            relevance_score += 0.2 * avg_activation
            
        # Adjust based on goal alignment if available
        goal_alignment = pattern_data.get("goal_alignment", 0.0)
        if goal_alignment > 0:
            relevance_score += 0.15 * goal_alignment
            
        # Normalize score
        return max(0.1, min(1.0, relevance_score))
    
    def _apply_data_governance(self, chunk: CognitiveChunk, quality_score: float, 
                              novelty_score: float, relevance_score: float) -> List[Dict[str, Any]]:
        """
        Applies data governance policies based on information assessment.
        
        Args:
            chunk: The cognitive chunk
            quality_score: Information quality score
            novelty_score: Information novelty score
            relevance_score: Information relevance score
            
        Returns:
            List of governance actions taken
        """
        governance_actions = []
        
        # Policy 1: Enhance information quality if needed
        if quality_score < self.information_quality_threshold:
            action = self._enhance_information_quality(chunk)
            if action:
                governance_actions.append(action)
        
        # Policy 2: Prioritize novel information if significant
        if novelty_score > self.novelty_threshold:
            action = self._prioritize_novel_information(chunk)
            if action:
                governance_actions.append(action)
        
        # Policy 3: Adjust memory storage priority based on relevance
        relevance_action = self._adjust_memory_priority(chunk, relevance_score)
        if relevance_action:
            governance_actions.append(relevance_action)
            
        # Policy 4: Tag information with quality metadata
        metadata_action = self._tag_information_metadata(chunk, quality_score, novelty_score, relevance_score)
        if metadata_action:
            governance_actions.append(metadata_action)
            
        return governance_actions
    
    def _enhance_information_quality(self, chunk: CognitiveChunk) -> Optional[Dict[str, Any]]:
        """
        Enhances information quality by filtering or enriching data.
        
        Args:
            chunk: The cognitive chunk
            
        Returns:
            Dictionary describing the enhancement action or None
        """
        # Extract pattern data
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        
        # Strategy 1: Filter out low-confidence concepts
        concepts = pattern_data.get("extracted_concepts", [])
        if concepts:
            high_confidence_concepts = []
            for concept in concepts:
                if isinstance(concept, dict):
                    if concept.get("salience", 0) > 0.3:
                        high_confidence_concepts.append(concept)
                else:
                    # If not a dict, keep the concept (it might be a string)
                    high_confidence_concepts.append(concept)
            
            if high_confidence_concepts and len(high_confidence_concepts) < len(concepts):
                # Update pattern data with filtered concepts
                pattern_data["extracted_concepts"] = high_confidence_concepts
                chunk.update_section("pattern_recognition_section", pattern_data)
                
                return {
                    "action": "filtered_low_quality_concepts",
                    "filtered_count": len(concepts) - len(high_confidence_concepts),
                    "remaining_count": len(high_confidence_concepts)
                }
        
        # Strategy 2: Merge redundant patterns
        patterns = pattern_data.get("detected_patterns", [])
        if len(patterns) > 1:
            merged_patterns = self._merge_redundant_patterns(patterns)
            if len(merged_patterns) < len(patterns):
                pattern_data["detected_patterns"] = merged_patterns
                chunk.update_section("pattern_recognition_section", pattern_data)
                
                return {
                    "action": "merged_redundant_patterns",
                    "original_count": len(patterns),
                    "merged_count": len(merged_patterns)
                }
        
        return None
    
    def _merge_redundant_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges redundant patterns to improve information clarity.
        
        Args:
            patterns: List of detected patterns
            
        Returns:
            List of merged patterns
        """
        if len(patterns) <= 1:
            return patterns
            
        # Group patterns by type
        pattern_groups = {}
        for pattern in patterns:
            pattern_type = pattern.get("type", "unknown")
            if pattern_type not in pattern_groups:
                pattern_groups[pattern_type] = []
            pattern_groups[pattern_type].append(pattern)
        
        # Merge patterns within each group if they have similar values
        merged_patterns = []
        for pattern_type, group in pattern_groups.items():
            if len(group) <= 1:
                merged_patterns.extend(group)
                continue
                
            # Group by similar values
            value_groups = {}
            for pattern in group:
                value = str(pattern.get("value", "")).lower()
                
                # Find similar group or create new one
                matched = False
                for key in value_groups:
                    # Simple similarity check - more sophisticated in real implementation
                    if value in key or key in value or self._similarity(value, key) > 0.7:
                        value_groups[key].append(pattern)
                        matched = True
                        break
                
                if not matched:
                    value_groups[value] = [pattern]
            
            # Merge each value group
            for value_patterns in value_groups.values():
                if len(value_patterns) == 1:
                    merged_patterns.append(value_patterns[0])
                else:
                    # Create merged pattern with highest confidence
                    best_pattern = max(value_patterns, key=lambda p: p.get("confidence", 0))
                    avg_confidence = sum(p.get("confidence", 0) for p in value_patterns) / len(value_patterns)
                    
                    merged_pattern = dict(best_pattern)
                    merged_pattern["confidence"] = min(1.0, avg_confidence * 1.1)  # Slight boost for consensus
                    merged_pattern["merged"] = True
                    merged_pattern["merged_count"] = len(value_patterns)
                    
                    merged_patterns.append(merged_pattern)
        
        return merged_patterns
    
    def _similarity(self, str1: str, str2: str) -> float:
        """
        Calculate string similarity (simplified).
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score (0-1)
        """
        # Simple character-based Jaccard similarity
        if not str1 or not str2:
            return 0.0
            
        set1 = set(str1)
        set2 = set(str2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / max(1, union)
    
    def _prioritize_novel_information(self, chunk: CognitiveChunk) -> Optional[Dict[str, Any]]:
        """
        Prioritizes processing of novel information.
        
        Args:
            chunk: The cognitive chunk
            
        Returns:
            Dictionary describing the prioritization action or None
        """
        # Extract pattern data
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        
        # Identify novel concepts
        current_concepts = []
        for concept in pattern_data.get("extracted_concepts", []):
            if isinstance(concept, dict) and "value" in concept:
                current_concepts.append(concept["value"])
            elif isinstance(concept, str):
                current_concepts.append(concept)
                
        memory_concepts = []
        for item in memory_data.get("retrieved_concepts", []):
            if isinstance(item, tuple) and len(item) >= 2:
                memory_concepts.append(item[0])
            elif isinstance(item, str):
                memory_concepts.append(item)
                
        novel_concepts = [c for c in current_concepts if c not in memory_concepts]
        
        if novel_concepts:
            # Boost the salience of novel concepts
            updated = False
            
            for concept in pattern_data.get("extracted_concepts", []):
                concept_value = concept.get("value", concept) if isinstance(concept, dict) else concept
                if concept_value in novel_concepts:
                    if isinstance(concept, dict):
                        # Boost salience by 20%
                        concept["salience"] = min(1.0, concept.get("salience", 0.5) * 1.2)
                        concept["novelty_boosted"] = True
                        updated = True
            
            if updated:
                # Update pattern data
                chunk.update_section("pattern_recognition_section", pattern_data)
                
                # Also update communication priorities if available
                comm_data = chunk.get_section_content("internal_communication_section")
                if comm_data:
                    info_priorities = comm_data.get("information_priorities", {})
                    if "novelty_processing" not in info_priorities:
                        info_priorities["novelty_processing"] = 0.0
                    
                    # Increase novelty processing priority
                    info_priorities["novelty_processing"] = min(1.0, info_priorities.get("novelty_processing", 0.0) + 0.2)
                    comm_data["information_priorities"] = info_priorities
                    chunk.update_section("internal_communication_section", comm_data)
                
                return {
                    "action": "prioritized_novel_concepts",
                    "novel_concepts": novel_concepts
                }
            
        return None
    
    def _adjust_memory_priority(self, chunk: CognitiveChunk, relevance_score: float) -> Optional[Dict[str, Any]]:
        """
        Adjusts memory processing priority based on relevance.
        
        Args:
            chunk: The cognitive chunk
            relevance_score: Information relevance score
            
        Returns:
            Dictionary describing the priority adjustment or None
        """
        # Only modify processing if we have communication data
        comm_data = chunk.get_section_content("internal_communication_section")
        if not comm_data:
            return None
            
        # Adjust memory expansion priority based on relevance
        priorities = comm_data.get("information_priorities", {})
        
        if "memory_expansion" not in priorities:
            priorities["memory_expansion"] = 0.5  # Default priority
            
        old_priority = priorities["memory_expansion"]
        
        # Increase priority for highly relevant information
        if relevance_score > 0.8:
            priorities["memory_expansion"] = min(1.0, old_priority + 0.1)
        # Decrease priority for less relevant information
        elif relevance_score < 0.3:
            priorities["memory_expansion"] = max(0.1, old_priority - 0.1)
                
        # Update communication data
        comm_data["information_priorities"] = priorities
        chunk.update_section("internal_communication_section", comm_data)
        
        return {
            "action": "adjusted_memory_priority",
            "old_priority": old_priority,
            "new_priority": priorities["memory_expansion"],
            "reason": "relevance_based"
        }
    
    def _tag_information_metadata(self, chunk: CognitiveChunk, quality_score: float, 
                                 novelty_score: float, relevance_score: float) -> Dict[str, Any]:
        """
        Tags information with quality metadata for use by other blocks.
        
        Args:
            chunk: The cognitive chunk
            quality_score: Information quality score
            novelty_score: Information novelty score
            relevance_score: Information relevance score
            
        Returns:
            Dictionary describing the tagging action
        """
        # Update memory data with quality tags if available
        memory_data = chunk.get_section_content("memory_section")
        if memory_data is not None:
            # Add data quality metadata
            memory_data["data_quality"] = {
                "quality_score": quality_score,
                "novelty_score": novelty_score,
                "relevance_score": relevance_score,
                "tagged_by": "DataKing",
                "timestamp": time.time()
            }
            
            # Add recommendations for memory storage
            memory_data["storage_recommendations"] = {
                "retention_priority": quality_score * 0.3 + novelty_score * 0.4 + relevance_score * 0.3,
                "connection_formation_priority": novelty_score * 0.7 + relevance_score * 0.3,
                "stability_factor": quality_score * 0.6 + relevance_score * 0.4
            }
            
            chunk.update_section("memory_section", memory_data)
        
        return {
            "action": "tagged_information_metadata",
            "applied_tags": ["quality", "novelty", "relevance"],
            "added_recommendations": True
        }
    
    def _update_metrics(self, quality_score: float, novelty_score: float, relevance_score: float):
        """
        Updates the Data King's oversight metrics.
        
        Args:
            quality_score: Information quality score
            novelty_score: Information novelty score
            relevance_score: Information relevance score
        """
        # Update total oversights count
        self.oversight_metrics["total_oversights"] += 1
        
        # Update quality metrics
        old_avg_quality = self.oversight_metrics["avg_information_quality"]
        new_avg_quality = old_avg_quality * 0.9 + quality_score * 0.1  # Exponential moving average
        self.oversight_metrics["avg_information_quality"] = new_avg_quality
        
        # Update other counters
        if quality_score < self.information_quality_threshold:
            self.oversight_metrics["quality_improvements"] += 1
            
        if novelty_score > self.novelty_threshold:
            self.oversight_metrics["novelty_detections"] += 1
            
        self.oversight_metrics["relevance_assessments"] += 1
    
    def get_oversight_metrics(self) -> Dict[str, Any]:
        """
        Get the Data King's current oversight metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.oversight_metrics