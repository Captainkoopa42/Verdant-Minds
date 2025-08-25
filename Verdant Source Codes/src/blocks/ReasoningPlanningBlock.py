import numpy as np
import time
import re
from typing import Dict, List, Any

from src.blocks.base_block import BaseBlock
from src.core.cognitive_chunk import CognitiveChunk


class ReasoningPlanningBlock(BaseBlock):
    """
    Block 5: Reasoning & Planning

    Performs logical inference, planning, and complex reasoning,
    integrating ECWF-based probability distributions for uncertainty
    handling. Supports both deductive and inductive reasoning.
    """

    def __init__(self, memory_bridge=None):
        """
        Initialize the Reasoning & Planning block.

        Args:
            memory_bridge: Optional reference to Memory-ECWF bridge
        """
        super().__init__("ReasoningPlanning")
        self.memory_bridge = memory_bridge

        # Reasoning mechanisms
        self.reasoning_rules = {
            "deductive": [],  # Certain inferences from general to specific
            "inductive": [],  # Probable inferences from specific to general
            "abductive": [],  # Best explanations from observations
            "analogical": []  # Comparisons between similar cases
        }

        # Rule performance tracking
        self.rule_performance = {}

        # Initialize default reasoning rules
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize basic reasoning rules."""
        # Sample deductive rules
        self.reasoning_rules["deductive"] = [
            {
                "name": "modus_ponens",
                "pattern": {"if": True, "then": None},
                "inference": lambda p: p["then"] if p["if"] else None,
                "certainty": 1.0
            },
            {
                "name": "modus_tollens",
                "pattern": {"if": None, "then": False},
                "inference": lambda p: not p["if"] if p["then"] is False else None,
                "certainty": 1.0
            }
        ]

        # Sample inductive rules
        self.reasoning_rules["inductive"] = [
            {
                "name": "generalization",
                "pattern": {"instances": [], "property": None},
                "inference": lambda p: f"Most {p['category']} have {p['property']}"
                if len(p['instances']) > 3 else None,
                "certainty": 0.7
            },
            {
                "name": "statistical_syllogism",
                "pattern": {"category": None, "property": None, "instance": None},
                "inference": lambda p: f"{p['instance']} likely has {p['property']}"
                if p.get("probability", 0) > 0.5 else None,
                "certainty": 0.8
            }
        ]

        # Sample abductive rules
        self.reasoning_rules["abductive"] = [
            {
                "name": "inference_to_best_explanation",
                "pattern": {"observation": None, "explanations": []},
                "inference": lambda p: p["explanations"][0]
                if p["explanations"] else None,
                "certainty": 0.6
            }
        ]

        # Sample analogical rules
        self.reasoning_rules["analogical"] = [
            {
                "name": "analogy",
                "pattern": {"source": None, "target": None, "shared_properties": []},
                "inference": lambda p: f"{p['target']} likely has {p['inferred_property']}"
                if len(p.get("shared_properties", [])) > 2 else None,
                "certainty": 0.7
            }
        ]

    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a chunk through reasoning and planning.

        Args:
            chunk: The cognitive chunk to process

        Returns:
            Processed cognitive chunk with reasoning and planning results
        """
        # Extract patterns and memory information
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}

        # Extract concepts, patterns and relevant information
        concepts = self._extract_concepts(pattern_data)
        patterns = pattern_data.get("detected_patterns", [])
        memory_concepts = memory_data.get("retrieved_concepts", [])

        # Get wave properties if available
        wave_properties = memory_data.get("wave_properties", {})
        wave_entropy = wave_properties.get("entropy", 0.5)

        # Generate reasoning premises from available information
        premises = self._generate_premises(concepts, patterns, memory_concepts)

        # Apply different reasoning types
        deductive_inferences = self._apply_deductive_reasoning(premises, wave_entropy)
        inductive_inferences = self._apply_inductive_reasoning(premises, wave_entropy)
        abductive_inferences = self._apply_abductive_reasoning(premises, wave_entropy)
        analogical_inferences = self._apply_analogical_reasoning(premises, wave_entropy)

        # Integrate with ECWF for uncertainty handling
        if self.memory_bridge:
            uncertainty_adjustments = self._integrate_wave_uncertainty(
                chunk,
                deductive_inferences + inductive_inferences + abductive_inferences + analogical_inferences
            )
        else:
            uncertainty_adjustments = []

        # Check for logical inconsistencies
        inconsistencies = self._detect_inconsistencies([
            deductive_inferences, inductive_inferences, abductive_inferences, analogical_inferences
        ])

        # Create reasoning plan with steps
        reasoning_plan = self._generate_reasoning_plan(
            premises,
            deductive_inferences + inductive_inferences + abductive_inferences + analogical_inferences,
            uncertainty_adjustments,
            inconsistencies
        )

        # Calculate overall confidence in reasoning
        confidence_score = self._calculate_confidence_score(
            deductive_inferences, inductive_inferences, abductive_inferences, analogical_inferences,
            inconsistencies, wave_entropy
        )

        # Compile all inferences
        all_inferences = {
            "deductive": deductive_inferences,
            "inductive": inductive_inferences,
            "abductive": abductive_inferences,
            "analogical": analogical_inferences
        }

        # Connect ethical principles to reasoning
        ethical_connections = self._connect_ethics_to_reasoning(
            all_inferences, ethics_data, concepts
        )

        # Update chunk with reasoning data
        reasoning_data = {
            "premises": premises,
            "inferences": all_inferences,
            "reasoning_plan": reasoning_plan,
            "inconsistencies": inconsistencies,
            "uncertainty_adjustments": uncertainty_adjustments,
            "ethical_connections": ethical_connections,
            "confidence_score": confidence_score,
            "processed_timestamp": time.time()
        }

        chunk.update_section("reasoning_section", reasoning_data)

        # Log the processing
        self.log_process(chunk, "reasoning", {
            "inference_count": (len(deductive_inferences) + len(inductive_inferences) +
                                len(abductive_inferences) + len(analogical_inferences)),
            "confidence": confidence_score,
            "inconsistencies": len(inconsistencies)
        })

        return chunk

    def _extract_concepts(self, pattern_data: Dict[str, Any]) -> List[str]:
        """Extract concepts from pattern data."""
        concepts = []
        if "extracted_concepts" in pattern_data:
            for concept in pattern_data["extracted_concepts"]:
                if isinstance(concept, dict) and "value" in concept:
                    concepts.append(concept["value"])
                elif isinstance(concept, str):
                    concepts.append(concept)
        return concepts

    def _generate_premises(self, concepts: List[str], patterns: List[Dict[str, Any]],
                             memory_concepts: List[Any]) -> List[Dict[str, Any]]:
        """
        Generate reasoning premises from available information.

        Args:
            concepts: Extracted concepts
            patterns: Detected patterns
            memory_concepts: Concepts from memory

        Returns:
            List of premise structures
        """
        premises = []

        # Convert pattern-based premises
        for pattern in patterns:
            pattern_type = pattern.get("type", "")
            pattern_value = pattern.get("value", "")

            if pattern_type == "topic":
                premises.append({
                    "type": "category",
                    "content": f"This is about {pattern_value}",
                    "category": pattern_value,
                    "confidence": pattern.get("confidence", 0.5)
                })

            elif pattern_type == "emotion":
                premises.append({
                    "type": "emotional_context",
                    "content": f"The emotional context is {pattern_value}",
                    "emotion": pattern_value,
                    "confidence": pattern.get("confidence", 0.5)
                })

            elif pattern_type == "structure":
                premises.append({
                    "type": "structural_relation",
                    "content": f"The structure involves {pattern_value}",
                    "structure": pattern_value,
                    "confidence": pattern.get("confidence", 0.5)
                })

        # Create concept-based premises
        for concept in concepts:
            # Basic concept existence premise
            premises.append({
                "type": "concept_presence",
                "content": f"The concept {concept} is present",
                "concept": concept,
                "confidence": 0.9  # High confidence in explicit concepts
            })

            # Check for relation concepts
            relation_indicators = ["relates", "connects", "affects", "influences", "causes"]
            for indicator in relation_indicators:
                if indicator in concept.lower():
                    relation_parts = concept.split()
                    if len(relation_parts) >= 3:
                        premises.append({
                            "type": "relationship",
                            "content": concept,
                            "source": relation_parts[0],
                            "relation": indicator,
                            "target": relation_parts[-1],
                            "confidence": 0.7
                        })

        # Convert memory concepts to premises
        for item in memory_concepts:
            if isinstance(item, tuple) and len(item) >= 2:
                concept, relevance = item
                premises.append({
                    "type": "memory_concept",
                    "content": f"The concept {concept} is relevant",
                    "concept": concept,
                    "relevance": relevance,
                    "confidence": min(0.9, relevance)  # Cap at 0.9
                })
            elif isinstance(item, str):
                premises.append({
                    "type": "memory_concept",
                    "content": f"The concept {item} is relevant",
                    "concept": item,
                    "relevance": 0.5,  # Default relevance
                    "confidence": 0.5
                })

        return premises

    def _integrate_wave_uncertainty(self, chunk: CognitiveChunk,
                                    inferences: List[str]) -> List[Dict[str, Any]]:
        """
        Integrate ECWF wave function to handle uncertainty in reasoning.

        Args:
            chunk: Current chunk
            inferences: List of inferences

        Returns:
            List of uncertainty adjustments
        """
        adjustments = []

        # Only proceed if memory_bridge is available
        if not self.memory_bridge:
            return adjustments

        # Get memory data
        memory_data = chunk.get_section_content("memory_section") or {}
        wave_properties = memory_data.get("wave_properties", {})

        # Get wave characteristics
        magnitude = wave_properties.get("magnitude", [0.5])
        phase = wave_properties.get("phase", [0.0])
        entropy = wave_properties.get("entropy", 0.5)

        # Process each inference
        for i, inference in enumerate(inferences):
            if i >= len(magnitude):
                break

            # Calculate uncertainty adjustment
            mag = magnitude[i] if isinstance(magnitude, list) else magnitude
            ph = phase[i] if isinstance(phase, list) else phase

            # Calculate inference confidence
            # Higher magnitude and low entropy = higher confidence
            raw_confidence = mag * (1.0 - entropy / 5.0)

            # Apply phase-based adjustment
            # Phase represents the "direction" of confidence
            phase_factor = 0.5 + 0.5 * np.cos(ph)  # 0.0 to 1.0
            adjusted_confidence = raw_confidence * phase_factor

            # Record adjustment if there is a meaningful change
            if abs(adjusted_confidence - raw_confidence) > 0.1:
                adjustments.append({
                    "inference": inference,
                    "raw_confidence": float(raw_confidence),
                    "adjusted_confidence": float(adjusted_confidence),
                    "magnitude": float(mag),
                    "phase": float(ph),
                    "entropy": float(entropy)
                })

        return adjustments

    def _apply_deductive_reasoning(self, premises: List[Dict[str, Any]],
                                   wave_entropy: float) -> List[str]:
        """
        Apply deductive reasoning rules.

        Args:
            premises: List of premises
            wave_entropy: Entropy from wave function

        Returns:
            List of deductive inferences
        """
        inferences = []

        # Look for categorical premises
        categories = {}
        properties = {}

        for premise in premises:
            if premise["type"] == "category":
                categories[premise["category"]] = premise["confidence"]

            if "concept" in premise:
                # Extract potential properties from concept names
                concept = premise["concept"]
                concept_parts = concept.split()

                # Check for "is" or "has" statements
                for i, part in enumerate(concept_parts):
                    if part.lower() in ["is", "has", "contains"] and i > 0 and i < len(concept_parts) - 1:
                        subject = " ".join(concept_parts[:i])
                        predicate = " ".join(concept_parts[i+1:])
                        if subject not in properties:
                            properties[subject] = []
                        properties[subject].append({
                            "predicate": predicate,
                            "relation": part.lower(),
                            "confidence": premise.get("confidence", 0.5)
                        })

        # (Placeholder) Apply categorical syllogisms and other deductive logic here.
        # For demonstration, we simply add a sample inference if a category exists.
        for category, conf in categories.items():
            inferences.append(f"Deductively inferred that topic '{category}' is central.")

        # Apply entropy-based confidence reduction for deductive reasoning
        if wave_entropy > 1.0:
            if inferences and len(inferences) > 1:
                inferences = inferences[:max(1, int(len(inferences) * (1 - wave_entropy / 5)))]
        return inferences

    def _apply_inductive_reasoning(self, premises: List[Dict[str, Any]], wave_entropy: float) -> List[str]:
        """
        Apply inductive reasoning rules.

        Args:
            premises: List of premises
            wave_entropy: Entropy from wave function

        Returns:
            List of inductive inferences
        """
        inferences = []
        # Placeholder implementation: For each memory_concept with lower confidence, infer inductively.
        for premise in premises:
            if premise.get("type") == "memory_concept" and premise.get("confidence", 0) < 0.7:
                inference = f"Inductively, {premise.get('concept')} might be significant."
                inferences.append(inference)
        return inferences

    def _apply_abductive_reasoning(self, premises: List[Dict[str, Any]], wave_entropy: float) -> List[str]:
        """
        Apply abductive reasoning rules.

        Args:
            premises: List of premises
            wave_entropy: Entropy from wave function

        Returns:
            List of abductive inferences
        """
        inferences = []
        # Placeholder implementation: Use emotional context to suggest a best explanation.
        for premise in premises:
            if premise.get("type") == "emotional_context":
                inference = f"Abductively, the observed emotion '{premise.get('emotion')}' may be due to underlying factors."
                inferences.append(inference)
        return inferences

    def _apply_analogical_reasoning(self, premises: List[Dict[str, Any]], wave_entropy: float) -> List[str]:
        """
        Apply analogical reasoning (inference by similarity).

        Args:
            premises: List of premises
            wave_entropy: Entropy from wave function

        Returns:
            List of analogical inferences
        """
        inferences = []

        # Gather concepts from premises
        concepts = []
        for premise in premises:
            if "concept" in premise:
                concepts.append({
                    "name": premise["concept"],
                    "confidence": premise.get("confidence", 0.5)
                })

        # Generate concept pairs for comparison
        concept_pairs = []
        for i, concept1 in enumerate(concepts):
            for j in range(i + 1, len(concepts)):
                concept2 = concepts[j]
                # Calculate similarity
                similarity = self._calculate_concept_similarity(concept1["name"], concept2["name"])
                if similarity > 0.3:  # Threshold for similarity
                    concept_pairs.append({
                        "concept1": concept1["name"],
                        "concept2": concept2["name"],
                        "similarity": similarity
                    })

        # Generate analogical inferences from concept pairs
        for pair in concept_pairs:
            # Find properties for each concept
            properties1 = self._extract_concept_properties(pair["concept1"], premises)
            properties2 = self._extract_concept_properties(pair["concept2"], premises)
            # Find shared properties
            shared_properties = set(properties1.keys()) & set(properties2.keys())
            # Find properties unique to concept1
            unique_properties1 = set(properties1.keys()) - shared_properties

            # Generate inferences by transferring unique properties
            for property_name in unique_properties1:
                property_value = properties1[property_name]
                confidence = pair["similarity"] * property_value["confidence"]
                if confidence > 0.4:  # Threshold for inference
                    inference = f"{pair['concept2']} may also {property_name} {property_value['value']}"
                    inferences.append(inference)

        # Adjust inferences based on wave entropy (optimal around 1.5)
        optimal_entropy = 1.5
        entropy_factor = 1.0 - abs(wave_entropy - optimal_entropy) / 5.0  # value between 0.0 and 1.0
        if inferences:
            keep_count = max(1, int(len(inferences) * entropy_factor))
            inferences = inferences[:keep_count]

        return inferences

    def _calculate_concept_similarity(self, concept1: str, concept2: str) -> float:
        """Calculate similarity between two concepts using Jaccard similarity."""
        words1 = set(concept1.lower().split())
        words2 = set(concept2.lower().split())
        if not words1 or not words2:
            return 0.0
        overlap = words1 & words2
        union = words1 | words2
        return len(overlap) / len(union)

    def _extract_concept_properties(self, concept: str, premises: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract properties associated with a concept from premises."""
        properties = {}
        for premise in premises:
            if premise.get("concept") == concept:
                content = premise.get("content", "").lower()
                property_indicators = ["is", "has", "contains", "shows", "exhibits"]
                for indicator in property_indicators:
                    if indicator in content:
                        try:
                            property_match = re.search(f"{indicator}\\s+(.*)", content)
                            if property_match:
                                property_value = property_match.group(1)
                                properties[indicator] = {
                                    "value": property_value,
                                    "confidence": premise.get("confidence", 0.5)
                                }
                        except (AttributeError, IndexError):
                            continue
        return properties

    def _detect_inconsistencies(self, inference_groups: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Detect logical inconsistencies in inferences.

        Args:
            inference_groups: Grouped inferences by type

        Returns:
            List of detected inconsistencies
        """
        inconsistencies = []
        # Flatten all inferences
        all_inferences = []
        for group in inference_groups:
            all_inferences.extend(group)

        # Look for contradictory statements
        for i, inf1 in enumerate(all_inferences):
            for j in range(i + 1, len(all_inferences)):
                inf2 = all_inferences[j]
                # Check for direct contradictions (e.g., "not" statements)
                if "not" in inf1 and inf1.replace("not", "").strip() in inf2:
                    inconsistencies.append({
                        "type": "direct_contradiction",
                        "inference1": inf1,
                        "inference2": inf2,
                        "severity": 1.0
                    })
                # Check for incompatible attributes
                incompatible_pairs = [
                    ("is good", "is bad"),
                    ("is high", "is low"),
                    ("increases", "decreases"),
                    ("always", "never"),
                    ("must", "cannot")
                ]
                for pair in incompatible_pairs:
                    if pair[0] in inf1 and pair[1] in inf2:
                        inconsistencies.append({
                            "type": "incompatible_attributes",
                            "inference1": inf1,
                            "inference2": inf2,
                            "severity": 0.8
                        })
        return inconsistencies

    def _generate_reasoning_plan(self, premises: List[Dict[str, Any]],
                                 inferences: List[str],
                                 uncertainty_adjustments: List[Dict[str, Any]],
                                 inconsistencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate a reasoning plan with steps.

        Args:
            premises: List of premises
            inferences: All inferences
            uncertainty_adjustments: Uncertainty adjustments
            inconsistencies: Logical inconsistencies

        Returns:
            List of reasoning steps
        """
        plan = []

        # Step 1: Identify key premises
        key_premises = sorted(premises, key=lambda p: p.get("confidence", 0), reverse=True)[:5]
        plan.append({
            "step": 1,
            "type": "premise_identification",
            "description": "Identify key premises from available information",
            "content": [p["content"] for p in key_premises],
            "confidence": sum(p.get("confidence", 0) for p in key_premises) / max(1, len(key_premises))
        })

        # Step 2: Apply primary reasoning
        best_inferences = inferences[:min(3, len(inferences))]
        plan.append({
            "step": 2,
            "type": "inference_generation",
            "description": "Generate primary inferences from premises",
            "content": best_inferences,
            "confidence": 0.7 if best_inferences else 0.3
        })

        # Step 3: Evaluate uncertainty
        if uncertainty_adjustments:
            plan.append({
                "step": 3,
                "type": "uncertainty_evaluation",
                "description": "Evaluate confidence and uncertainty in inferences",
                "content": [f"Adjusted confidence for '{adj['inference']}' from {adj['raw_confidence']:.2f} to {adj['adjusted_confidence']:.2f}"
                            for adj in uncertainty_adjustments],
                "confidence": 0.8
            })

        # Step 4: Address inconsistencies
        if inconsistencies:
            plan.append({
                "step": 4,
                "type": "inconsistency_resolution",
                "description": "Identify and address logical inconsistencies",
                "content": [f"Inconsistency between '{inc['inference1']}' and '{inc['inference2']}'"
                            for inc in inconsistencies],
                "confidence": 0.6
            })

        # Step 5: Form conclusions from consistent inferences
        if inferences:
            inconsistent_infs = set()
            for inc in inconsistencies:
                inconsistent_infs.add(inc["inference1"])
                inconsistent_infs.add(inc["inference2"])
            consistent_infs = [inf for inf in inferences if inf not in inconsistent_infs]
            plan.append({
                "step": 5,
                "type": "conclusion_formation",
                "description": "Form coherent conclusions from consistent inferences",
                "content": consistent_infs[:3],
                "confidence": 0.7 if consistent_infs else 0.4
            })

        return plan

    def _calculate_confidence_score(self, deductive_inferences: List[str],
                                    inductive_inferences: List[str],
                                    abductive_inferences: List[str],
                                    analogical_inferences: List[str],
                                    inconsistencies: List[Dict[str, Any]],
                                    wave_entropy: float) -> float:
        """
        Calculate overall confidence score for reasoning.

        Args:
            deductive_inferences: Deductive inferences
            inductive_inferences: Inductive inferences
            abductive_inferences: Abductive inferences
            analogical_inferences: Analogical inferences
            inconsistencies: Logical inconsistencies
            wave_entropy: Entropy from wave function

        Returns:
            Confidence score (0-1)
        """
        base_confidence = 0.5
        inference_count = (len(deductive_inferences) + len(inductive_inferences) +
                           len(abductive_inferences) + len(analogical_inferences))

        if inference_count > 0:
            inference_factor = min(0.3, 0.05 * inference_count)
            base_confidence += inference_factor

        if deductive_inferences:
            deductive_factor = 0.2 * min(1.0, len(deductive_inferences) / 3)
            base_confidence += deductive_factor

        if inconsistencies:
            inconsistency_penalty = 0.1 * min(1.0, len(inconsistencies) / 2)
            base_confidence -= inconsistency_penalty

        if deductive_inferences and len(deductive_inferences) > len(inductive_inferences):
            entropy_factor = max(0, 0.2 - 0.04 * wave_entropy)
        else:
            entropy_factor = 0.1 - 0.02 * abs(wave_entropy - 2.0)

        base_confidence += entropy_factor
        confidence = max(0.1, min(0.95, base_confidence))
        return confidence

    def _connect_ethics_to_reasoning(self, all_inferences: Dict[str, List[str]],
                                     ethics_data: Dict[str, Any],
                                     concepts: List[str]) -> List[Dict[str, Any]]:
        """
        Connect ethical principles to reasoning outputs.

        Args:
            all_inferences: All inferences grouped by type
            ethics_data: Ethics evaluation data
            concepts: Extracted concepts

        Returns:
            List of ethical connections
        """
        connections = []
        # Extract ethical principles and concerns
        principles = {}
        if "evaluation" in ethics_data:
            principles = ethics_data.get("evaluation", {}).get("principle_scores", {})

        concerns = ethics_data.get("evaluation", {}).get("concerns", [])

        # Check each inference for ethical relevance
        for inf_type, inferences in all_inferences.items():
            for inference in inferences:
                inference_lower = inference.lower()
                mentioned_principles = []
                for principle in principles:
                    if principle.lower() in inference_lower:
                        mentioned_principles.append(principle)
                mentioned_concerns = []
                for concern in concerns:
                    if concern.lower() in inference_lower:
                        mentioned_concerns.append(concern)
                if mentioned_principles or mentioned_concerns:
                    connections.append({
                        "inference": inference,
                        "mentioned_principles": mentioned_principles,
                        "mentioned_concerns": mentioned_concerns,
                        "relevance": 0.8  # Default relevance score
                    })

        return connections