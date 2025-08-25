import time
import re
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from src.blocks.base_block import BaseBlock
from src.core.cognitive_chunk import CognitiveChunk

class PatternRecognitionBlock(BaseBlock):
    """
    Block 2: Pattern Recognition
    
    Identifies meaningful patterns in normalized sensory data,
    extracting concepts, relationships, and structures.
    """
    
    def __init__(self):
        """Initialize the Pattern Recognition block."""
        super().__init__("PatternRecognition")
        
        # Initialize pattern detectors
        self.pattern_detectors = {
            "topic": self._detect_topic_patterns,
            "relationship": self._detect_relationship_patterns,
            "structure": self._detect_structural_patterns,
            "temporal": self._detect_temporal_patterns,
            "emotion": self._detect_emotional_patterns
        }
        
        # Initialize concept extractors
        self.concept_extractors = [
            self._extract_noun_phrases,
            self._extract_entities,
            self._extract_key_terms
        ]
        
        # Maintain detector performance statistics
        self.detector_stats = {detector: {"calls": 0, "patterns_found": 0} 
                              for detector in self.pattern_detectors}
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a chunk through pattern recognition.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk with detected patterns
        """
        # Extract sensory data
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        
        # Cannot proceed without sensory data
        if not sensory_data or "input_text" not in sensory_data:
            self.log_process(chunk, "error", {"message": "No input text found"})
            return chunk
        
        input_text = sensory_data["input_text"]
        tokens = sensory_data.get("tokens", [])
        if not tokens and "preprocessed_data" in sensory_data:
            # Try to extract tokens from preprocessed data
            tokens = sensory_data["preprocessed_data"].get("tokens", [])
        
        # Extract concepts
        extracted_concepts = self._extract_concepts(input_text, tokens)
        
        # Detect patterns of various types
        detected_patterns = []
        for detector_name, detector_func in self.pattern_detectors.items():
            detector_patterns = detector_func(input_text, tokens, sensory_data, extracted_concepts)
            detected_patterns.extend(detector_patterns)
            
            # Update detector statistics
            self.detector_stats[detector_name]["calls"] += 1
            self.detector_stats[detector_name]["patterns_found"] += len(detector_patterns)
        
        # Detect intent
        intent = self._detect_intent(input_text, extracted_concepts, detected_patterns)
        
        # Detect ethical dimensions
        ethical_dimensions = self._detect_ethical_dimensions(input_text, extracted_concepts)
        
        # Create pattern recognition data
        pattern_data = {
            "extracted_concepts": extracted_concepts,
            "detected_patterns": detected_patterns,
            "intent": intent["type"],
            "intent_confidence": intent["confidence"],
            "ethical_dimensions": ethical_dimensions,
            "processing_metadata": {
                "detector_calls": {name: stats["calls"] for name, stats in self.detector_stats.items()},
                "concept_count": len(extracted_concepts),
                "pattern_count": len(detected_patterns)
            },
            "processed_timestamp": time.time()
        }
        
        # Update chunk with pattern recognition data
        chunk.update_section("pattern_recognition_section", pattern_data)
        
        # Log processing
        self.log_process(chunk, "pattern_recognition", {
            "concepts_extracted": len(extracted_concepts),
            "patterns_detected": len(detected_patterns),
            "intent": intent["type"]
        })
        
        return chunk

    # Rest of the methods from the previous implementation remain the same...

    def _find_closest_concept(self, text: str, concept_values: List[str]) -> Optional[str]:
        """
        Find the closest matching concept for a given text.
        
        Args:
            text: Text to match
            concept_values: List of concept values to match against
            
        Returns:
            Closest matching concept or None
        """
        text_lower = text.lower()
        
        # Exact match
        for concept in concept_values:
            if concept.lower() == text_lower:
                return concept
        
        # Substring match
        for concept in concept_values:
            if concept.lower() in text_lower or text_lower in concept.lower():
                return concept
        
        # Tokenized match (check if most words match)
        text_tokens = set(text_lower.split())
        if len(text_tokens) >= 2:  # Only consider multi-word phrases
            best_match = None
            best_score = 0.3  # Threshold for considering a match
            
            for concept in concept_values:
                concept_tokens = set(concept.lower().split())
                
                # Try to remove concept from text
                filtered = text_lower.replace(concept.lower(), '') 
                if not re.match(r'\w+', filtered):
                    best_match = concept
                    best_score = 1.0
                    break
                
                # Calculate token overlap score
                overlap = len(text_tokens & concept_tokens) / len(text_tokens | concept_tokens)
                
                if overlap > best_score:
                    best_match = concept
                    best_score = overlap
            
            return best_match
        
        # No match found
        return None

    def _detect_topic_patterns(self, text: str, tokens: List[str], sensory: Dict[str, Any], concepts: List[str]) -> List[Dict[str, Any]]:
        """Very naive topic detector returning empty results."""
        return []

    def _detect_relationship_patterns(self, text: str, tokens: List[str], sensory: Dict[str, Any], concepts: List[str]) -> List[Dict[str, Any]]:
        """Placeholder relationship pattern detector."""
        return []

    def _detect_structural_patterns(self, text: str, tokens: List[str], sensory: Dict[str, Any], concepts: List[str]) -> List[Dict[str, Any]]:
        """Placeholder structural pattern detector."""
        return []

    def _detect_temporal_patterns(self, text: str, tokens: List[str], sensory: Dict[str, Any], concepts: List[str]) -> List[Dict[str, Any]]:
        """Placeholder temporal pattern detector."""
        return []

    def _detect_emotional_patterns(self, text: str, tokens: List[str], sensory: Dict[str, Any], concepts: List[str]) -> List[Dict[str, Any]]:
        """Placeholder emotional pattern detector."""
        return []

    def _extract_concepts(self, text: str, tokens: List[str]) -> List[str]:
        concepts: List[str] = []
        for extractor in self.concept_extractors:
            try:
                concepts.extend(extractor(text, tokens))
            except Exception:
                continue
        return list(dict.fromkeys(concepts))

    def _extract_noun_phrases(self, text: str, tokens: List[str]) -> List[str]:
        return [t for t in tokens if t.isalpha() and t[0].islower()]

    def _extract_entities(self, text: str, tokens: List[str]) -> List[str]:
        return [t for t in tokens if t and t[0].isupper()]

    def _extract_key_terms(self, text: str, tokens: List[str]) -> List[str]:
        return [t for t in tokens if len(t) > 3]

    def _detect_intent(self, text: str, concepts: List[str], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        intent_type = "question" if "?" in text else "statement"
        return {"type": intent_type, "confidence": 0.5}

    def _detect_ethical_dimensions(self, text: str, concepts: List[str]) -> List[str]:
        keywords = {
            "harm": "Non-maleficence",
            "good": "Beneficence",
            "choice": "Autonomy",
            "fair": "Justice",
            "transparent": "Transparency",
        }
        text_lower = text.lower()
        return [dim for word, dim in keywords.items() if word in text_lower]

# Export the block for use in the system
__all__ = ['PatternRecognitionBlock']
