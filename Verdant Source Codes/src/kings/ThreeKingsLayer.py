import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any

from src.core.cognitive_chunk import CognitiveChunk
from src.kings.data_king import DataKing
from src.kings.forefront_king import ForefrontKing
from src.kings.ethics_king import EthicsKing

class ThreeKingsLayer:
    """
    Coordination layer for the Three Kings Architecture.
    
    Manages interactions between kings, resolves conflicts, and provides
    comprehensive oversight of system processing.
    """
    
    def __init__(self):
        """Initialize the Three Kings coordination layer."""
        self.data_king = DataKing()
        self.forefront_king = ForefrontKing()
        self.ethics_king = EthicsKing()
        
        # Track king interactions and influence
        self.king_interaction_history = []
        self.conflict_resolution_history = []
        
        # Decision influence weights (dynamically adjusted)
        self.influence_weights = {
            "DataKing": 1.0,
            "ForefrontKing": 1.0,
            "EthicsKing": 1.0
        }
        
        # Voting thresholds
        self.majority_threshold = 0.66  # 2/3 majority
        self.consensus_threshold = 0.9  # Near unanimous
        
        # System metrics
        self.metrics = {
            "oversight_applications": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "council_votes": 0
        }

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Wrapper to conform to block interface."""
        print(f"ThreeKingsLayer processing chunk {chunk.chunk_id}")
        return self.oversee_processing(chunk)
    
    def oversee_processing(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Apply coordinated oversight from all three kings.
        
        Args:
            chunk: The cognitive chunk to oversee
            
        Returns:
            Chunk with oversight applied
        """
        # Update metrics
        self.metrics["oversight_applications"] += 1
        
        # Record initial state for conflict detection
        initial_state = self._capture_chunk_state(chunk)
        
        # Apply oversight from each king
        chunk = self.data_king.oversee_processing(chunk)
        chunk = self.forefront_king.oversee_processing(chunk)
        chunk = self.ethics_king.oversee_processing(chunk)
        
        # Detect and resolve conflicts
        conflicts = self._detect_conflicts(chunk, initial_state)
        if conflicts:
            self.metrics["conflicts_detected"] += 1
            chunk = self._resolve_conflicts(chunk, conflicts)
            self.metrics["conflicts_resolved"] += 1
        
        # Apply council wisdom for critical decisions
        decision_criticality = self._assess_decision_criticality(chunk)
        if decision_criticality > 0.7:  # Threshold for critical decisions
            chunk = self._apply_council_vote(chunk)
            self.metrics["council_votes"] += 1
        
        # Record interaction for historical tracking
        self._record_king_interaction(chunk)
        
        # Update king influence based on recent performance
        self._update_king_influence()
        
        return chunk
    
    def _capture_chunk_state(self, chunk: CognitiveChunk) -> Dict[str, Any]:
        """Capture relevant state from chunk for conflict detection."""
        # Extract key decision elements
        action_data = chunk.get_section_content("action_selection_section") or {}
        
        return {
            "selected_action": action_data.get("selected_action"),
            "action_confidence": action_data.get("action_confidence"),
            "action_parameters": action_data.get("action_parameters")
        }
    
    def _detect_conflicts(self, chunk: CognitiveChunk, 
                         initial_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect conflicts between king modifications.
        
        Args:
            chunk: Current chunk state
            initial_state: Initial chunk state before kings
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Check for action selection conflicts
        action_data = chunk.get_section_content("action_selection_section") or {}
        data_king_data = chunk.get_section_content("data_king_section") or {}
        forefront_data = chunk.get_section_content("forefront_king_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        
        # Detect action override conflicts
        if (initial_state["selected_action"] and 
            action_data.get("selected_action") != initial_state["selected_action"]):
            
            # Identify which king made the override
            overriding_king = None
            
            if "forefront_override" in action_data:
                overriding_king = "ForefrontKing"
            elif ethics_data.get("evaluation", {}).get("status") == "review_needed":
                overriding_king = "EthicsKing"
            elif "governance_actions" in data_king_data:
                for action in data_king_data["governance_actions"]:
                    if action.get("action") == "adjusted_action_priority":
                        overriding_king = "DataKing"
                        break
            
            if overriding_king:
                conflicts.append({
                    "type": "action_override",
                    "original_action": initial_state["selected_action"],
                    "new_action": action_data.get("selected_action"),
                    "overriding_king": overriding_king,
                    "criticality": 0.8  # Action overrides are significant conflicts
                })
        
        # Detect confidence assessment conflicts
        king_assessments = {}
        
        # Get ForefrontKing assessment
        if "decision_threshold" in forefront_data:
            king_assessments["ForefrontKing"] = {
                "confidence_assessment": forefront_data.get("decision_threshold", 0.5)
            }
        
        # Get EthicsKing assessment
        if "evaluation" in ethics_data:
            king_assessments["EthicsKing"] = {
                "confidence_assessment": ethics_data["evaluation"].get("overall_score", 0.5)
            }
        
        # Get DataKing assessment
        if "information_quality" in data_king_data:
            king_assessments["DataKing"] = {
                "confidence_assessment": data_king_data["information_quality"]
            }
        
        # Detect significant disagreements in confidence assessment
        if len(king_assessments) >= 2:
            assessments = [data["confidence_assessment"] for data in king_assessments.values()]
            assessment_range = max(assessments) - min(assessments)
            
            if assessment_range > 0.3:  # Significant disagreement threshold
                conflicts.append({
                    "type": "confidence_disagreement",
                    "king_assessments": king_assessments,
                    "assessment_range": assessment_range,
                    "criticality": 0.6 * assessment_range  # Scale with disagreement magnitude
                })
        
        return conflicts
    
    def _resolve_conflicts(self, chunk: CognitiveChunk, 
                          conflicts: List[Dict[str, Any]]) -> CognitiveChunk:
        """
        Resolve conflicts between kings through coordination.
        
        Args:
            chunk: Chunk with conflicts
            conflicts: List of detected conflicts
            
        Returns:
            Chunk with resolved conflicts
        """
        resolution_details = []
        
        for conflict in conflicts:
            if conflict["type"] == "action_override":
                # Resolve action override conflict
                resolution = self._resolve_action_override(chunk, conflict)
                resolution_details.append(resolution)
                
            elif conflict["type"] == "confidence_disagreement":
                # Resolve confidence assessment disagreement
                resolution = self._resolve_confidence_disagreement(chunk, conflict)
                resolution_details.append(resolution)
        
        # Record resolution in chunk
        chunk.update_section("three_kings_layer_section", {
            "conflicts_resolved": len(conflicts),
            "resolution_details": resolution_details,
            "resolution_timestamp": time.time()
        })
        
        # Add resolution to history
        self.conflict_resolution_history.append({
            "conflicts": conflicts,
            "resolutions": resolution_details,
            "timestamp": time.time()
        })
        
        # Keep history at a reasonable size
        if len(self.conflict_resolution_history) > 100:
            self.conflict_resolution_history = self.conflict_resolution_history[-100:]
        
        return chunk
    
    def _resolve_action_override(self, chunk: CognitiveChunk, 
                                conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve action override conflict using weighted king influence.
        
        Args:
            chunk: Current chunk
            conflict: Conflict details
            
        Returns:
            Resolution details
        """
        action_data = chunk.get_section_content("action_selection_section") or {}
        
        # Get king weights for voting
        overriding_king = conflict["overriding_king"]
        overriding_weight = self.influence_weights.get(overriding_king, 1.0)
        other_weights_sum = sum(w for k, w in self.influence_weights.items() if k != overriding_king)
        
        # Calculate vote strength
        override_strength = overriding_weight / (overriding_weight + other_weights_sum)
        
        # Decision based on weighted voting
        if override_strength > self.majority_threshold:
            # Keep the override (already in place)
            resolution = {
                "conflict_type": "action_override",
                "decision": "maintain_override",
                "final_action": conflict["new_action"],
                "override_strength": override_strength,
                "primary_influence": overriding_king
            }
        else:
            # Revert to original action
            action_data["selected_action"] = conflict["original_action"]
            action_data["override_rejected"] = True
            action_data["rejection_reason"] = f"Insufficient king influence ({override_strength:.2f})"
            
            # Update the chunk
            chunk.update_section("action_selection_section", action_data)
            
            resolution = {
                "conflict_type": "action_override",
                "decision": "reject_override",
                "final_action": conflict["original_action"],
                "override_strength": override_strength,
                "primary_influence": "ConsensusRejection"
            }
        
        return resolution
    
    def _resolve_confidence_disagreement(self, chunk: CognitiveChunk, 
                                        conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve confidence assessment disagreement.
        
        Args:
            chunk: Current chunk
            conflict: Conflict details
            
        Returns:
            Resolution details
        """
        # Calculate weighted average confidence
        king_assessments = conflict["king_assessments"]
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for king, assessment in king_assessments.items():
            king_weight = self.influence_weights.get(king, 1.0)
            weighted_sum += assessment["confidence_assessment"] * king_weight
            weight_sum += king_weight
        
        consensus_confidence = weighted_sum / weight_sum if weight_sum > 0 else 0.5
        
        # Identify most influential king
        max_influence = 0.0
        primary_influence = "None"
        
        for king, weight in self.influence_weights.items():
            if king in king_assessments and weight > max_influence:
                max_influence = weight
                primary_influence = king
        
        # Update confidence assessments in chunk
        self._update_king_confidence_assessments(chunk, consensus_confidence)
        
        return {
            "conflict_type": "confidence_disagreement",
            "decision": "weighted_consensus",
            "consensus_confidence": consensus_confidence,
            "assessment_range": conflict["assessment_range"],
            "primary_influence": primary_influence
        }
    
    def _update_king_confidence_assessments(self, chunk: CognitiveChunk, 
                                           consensus_confidence: float):
        """
        Update individual king confidence assessments with consensus value.
        
        Args:
            chunk: Current chunk
            consensus_confidence: Agreed confidence value
        """
        # Update ForefrontKing
        forefront_data = chunk.get_section_content("forefront_king_section") or {}
        if "decision_threshold" in forefront_data:
            # Blend with existing threshold (80% consensus, 20% original)
            original = forefront_data["decision_threshold"]
            forefront_data["decision_threshold"] = 0.8 * consensus_confidence + 0.2 * original
            forefront_data["consensus_adjusted"] = True
            chunk.update_section("forefront_king_section", forefront_data)
        
        # For other kings, add consensus note but don't modify their fundamental assessments
        # This preserves their individual perspectives while acknowledging the consensus
    
    def _assess_decision_criticality(self, chunk: CognitiveChunk) -> float:
        """
        Assess the criticality of the current decision.
        
        Args:
            chunk: Current chunk
            
        Returns:
            Criticality score (0-1)
        """
        criticality = 0.5  # Default moderate criticality
        
        # Extract decision information
        action_data = chunk.get_section_content("action_selection_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        
        # Increase criticality for ethical concerns
        if ethics_data.get("evaluation", {}).get("status") in ["review_needed", "acceptable"]:
            ethical_concerns = ethics_data.get("evaluation", {}).get("concerns", [])
            criticality += 0.1 * len(ethical_concerns)
        
        # Action-specific criticality
        selected_action = action_data.get("selected_action", "")
        if selected_action == "defer_decision":
            criticality += 0.2  # Deferral indicates potentially critical decision
        elif selected_action == "trigger_system_action":
            criticality += 0.15  # System actions have higher impact
            
        # Confidence-based criticality
        confidence = action_data.get("action_confidence", 0.5)
        if confidence < 0.4 or confidence > 0.9:
            criticality += 0.1  # Very low or very high confidence increases criticality
            
        return min(1.0, criticality)
    
    def _apply_council_vote(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Apply coordinated council vote for critical decisions.
        
        Args:
            chunk: Current chunk
            
        Returns:
            Chunk with council decision applied
        """
        # Extract key information for voting
        action_data = chunk.get_section_content("action_selection_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        data_king_data = chunk.get_section_content("data_king_section") or {}
        forefront_data = chunk.get_section_content("forefront_king_section") or {}
        
        # Get current action and alternatives
        current_action = action_data.get("selected_action", "")
        all_scores = action_data.get("all_action_scores", {})
        
        # Get individual king votes
        votes = {
            "EthicsKing": self._get_ethics_king_vote(ethics_status, current_action, all_scores),
            "DataKing": self._get_data_king_vote(data_king_data, current_action, all_scores),
            "ForefrontKing": current_action  # Forefront King's original decision
        }
        
        # Count weighted votes
        vote_counts = {}
        total_weight = sum(self.influence_weights.values())
        
        for king, vote in votes.items():
            king_weight = self.influence_weights.get(king, 1.0)
            if vote not in vote_counts:
                vote_counts[vote] = 0
            vote_counts[vote] += king_weight / total_weight
        
        # Determine winning vote
        winning_vote = max(vote_counts.items(), key=lambda x: x[1])
        
        # Apply council decision if different from current action
        if winning_vote[0] != current_action and winning_vote[1] >= self.majority_threshold:
            # Change action based on council vote
            action_data["selected_action"] = winning_vote[0]
            action_data["council_override"] = True
            action_data["vote_distribution"] = vote_counts
            action_data["deciding_threshold"] = self.majority_threshold
            
            # Update chunk
            chunk.update_section("action_selection_section", action_data)
        
        # Record council vote in chunk
        chunk.update_section("three_kings_layer_section", {
            "council_vote": {
                "votes": votes,
                "vote_counts": vote_counts,
                "winning_vote": winning_vote[0],
                "winning_margin": winning_vote[1],
                "threshold": self.majority_threshold,
                "applied": winning_vote[0] != current_action and winning_vote[1] >= self.majority_threshold
            },
            "council_timestamp": time.time()
        })
        
        return chunk
    
    def _get_ethics_king_vote(self, ethics_status: str, current_action: str, 
                              all_scores: Dict[str, float]) -> str:
        """
        Determine the Ethics King's vote based on ethical status.
        
        Args:
            ethics_status: Current ethical status
            current_action: Currently selected action
            all_scores: Dictionary of action scores
            
        Returns:
            Recommended action
        """
        if ethics_status == "review_needed":
            return "defer_decision"
        elif ethics_status in ["excellent", "good"]:
            # Ethics King defers to current action for excellent ethical status
            return current_action
        else:
            # For acceptable status, lean toward caution
            return "provide_partial_answer" if "provide_partial_answer" in all_scores else current_action
    
    def _get_data_king_vote(self, data_king_data: Dict[str, Any], 
                            current_action: str, 
                            all_scores: Dict[str, float]) -> str:
        """
        Determine the Data King's vote based on information quality.
        
        Args:
            data_king_data: Data King's section data
            current_action: Currently selected action
            all_scores: Dictionary of action scores
            
        Returns:
            Recommended action
        """
        # Extract information quality and relevance
        info_quality = data_king_data.get("information_quality", 0.5)
        info_relevance = data_king_data.get("relevance", 0.5)
        
        if info_quality < 0.4:
            # Low quality information suggests asking for clarification
            return "ask_clarification"
        elif info_quality > 0.8 and info_relevance > 0.8:
            # High quality and relevant information suggests direct answer
            return "answer_query" if "answer_query" in all_scores else current_action
        else:
            # Moderate quality suggests partial answer
            return "provide_partial_answer" if "provide_partial_answer" in all_scores else current_action
    
    def _record_king_interaction(self, chunk: CognitiveChunk):
        """Record interaction between kings for historical tracking."""
        # Extract king influences
        influences = []
        
        # Data King influence
        data_king_section = chunk.get_section_content("data_king_section") or {}
        if data_king_section:
            influences.append({
                "king": "DataKing",
                "primary_metric": data_king_section.get("information_quality", 0.5),
                "governance_actions": len(data_king_section.get("governance_actions", []))
            })
        
        # Forefront King influence
        forefront_king_section = chunk.get_section_content("forefront_king_section") or {}
        if forefront_king_section:
            influences.append({
                "king": "ForefrontKing",
                "primary_metric": forefront_king_section.get("cognitive_load", 0.5),
                "assessment": forefront_king_section.get("executive_assessment", "")
            })
        
        # Ethics King influence
        ethics_king_section = chunk.get_section_content("ethics_king_section") or {}
        if ethics_king_section:
            influences.append({
                "king": "EthicsKing",
                "primary_metric": ethics_king_section.get("evaluation", {}).get("overall_score", 0.5),
                "status": ethics_king_section.get("evaluation", {}).get("status", "")
            })
        
        # Record interaction
        interaction = {
            "timestamp": time.time(),
            "influences": influences,
            "conflicts_detected": getattr(chunk, "conflicts_detected", 0),
            "conflicts_resolved": getattr(chunk, "conflicts_resolved", 0),
            "council_vote": "council_vote" in (chunk.get_section_content("three_kings_layer_section") or {})
        }
        
        self.king_interaction_history.append(interaction)
        
        # Keep history at a reasonable size
        if len(self.king_interaction_history) > 200:
            self.king_interaction_history = self.king_interaction_history[-200:]
    
    def _update_king_influence(self):
        """Update king influence weights based on recent performance."""
        # Only update if we have enough history
        if len(self.king_interaction_history) < 10:
            return
        
        # Get recent interactions
        recent_interactions = self.king_interaction_history[-20:]
        
        # Calculate average primary metrics for each king
        king_metrics = {
            "DataKing": [],
            "ForefrontKing": [],
            "EthicsKing": []
        }
        
        # Collect metrics
        for interaction in recent_interactions:
            for influence in interaction["influences"]:
                king = influence.get("king")
                if king in king_metrics and "primary_metric" in influence:
                    king_metrics[king].append(influence["primary_metric"])
        
        # Calculate new influence weights
        for king, metrics in king_metrics.items():
            if metrics:
                avg_metric = sum(metrics) / len(metrics)
                
                # Update influence weight
                old_weight = self.influence_weights.get(king, 1.0)
                
                # Higher metrics get higher influence
                # But we dampen the effect to prevent wild oscillations
                new_weight = old_weight * 0.9 + avg_metric * 0.1 * 2.0  # Scale metric to 0-2 range
                
                # Ensure weight stays in reasonable range
                self.influence_weights[king] = max(0.5, min(1.5, new_weight))
    
    def get_kings_state(self) -> Dict[str, Any]:
        """
        Get the current state of all kings.
        
        Returns:
            Dictionary with king state information
        """
        return {
            "data_king": {
                "influence_weight": self.influence_weights.get("DataKing", 1.0),
                "influence_count": len(self.data_king.influence_history)
            },
            "forefront_king": {
                "influence_weight": self.influence_weights.get("ForefrontKing", 1.0),
                "attention_focus": self.forefront_king.attention_focus,
                "cognitive_load": self.forefront_king.cognitive_load,
                "decision_threshold": self.forefront_king.decision_threshold
            },
            "ethics_king": {
                "influence_weight": self.influence_weights.get("EthicsKing", 1.0),
                "ethical_sensitivity": self.ethics_king.ethical_sensitivity,
                "evaluation_count": len(self.ethics_king.evaluation_history)
            },
            "coordination": {
                "metrics": self.metrics,
                "conflict_count": len(self.conflict_resolution_history),
                "council_majority_threshold": self.majority_threshold
            }
        }
