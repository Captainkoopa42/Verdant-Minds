import time
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter

import numpy as np

from .base_block import BaseBlock
from ..core.cognitive_chunk import CognitiveChunk

# Try to import spaCy for advanced NLP
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Model not installed, but spaCy is available
        nlp = None
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None


class PatternRecognitionBlock(BaseBlock):
    """
    Block 2: Enhanced Pattern Recognition

    Identifies meaningful patterns at multiple levels:
    - Lexical patterns (keywords, collocations)
    - Semantic patterns (concepts, relationships, analogies)
    - Cognitive patterns (question types, reasoning structures)
    - Affective patterns (sentiment, emotion)
    - Tension patterns (contradictions, opposing values) - KEY FOR HOUSING!
    - Structural patterns (entities, relations)

    The tension detection is CRITICAL for Verdant's thermodynamic
    contradiction handling and Housing operator.
    """

    def __init__(self, memory_bridge=None):
        """
        Initialize the Pattern Recognition block.

        Args:
            memory_bridge: Optional MemoryECWFBridge for concept mapping
        """
        super().__init__("PatternRecognition")
        self.memory_bridge = memory_bridge

        # Opposition pairs for tension detection
        self.opposition_pairs = self._initialize_opposition_pairs()

        # Sentiment lexicon
        self.sentiment_lexicon = self._initialize_sentiment_lexicon()

        # Question patterns
        self.question_patterns = self._initialize_question_patterns()

        # Statistics
        self.stats = {
            "chunks_processed": 0,
            "concepts_mapped": 0,
            "tensions_detected": 0,
            "questions_classified": 0
        }
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process chunk through enhanced pattern recognition.

        Extracts:
        1. Keywords (backward compatible)
        2. Concepts from Memory Web
        3. Opposing concept pairs
        4. Tension coefficients (for Housing operator!)
        5. Question type classification
        6. Sentiment analysis
        7. Named entities

        Args:
            chunk: The cognitive chunk to process

        Returns:
            Processed cognitive chunk with comprehensive pattern data
        """
        # Get sensory data
        sensory_data = chunk.get_section_content("sensory_input_section") or {}

        if not sensory_data or "input_text" not in sensory_data:
            self.log_process(chunk, "error", {"message": "No input text found"})
            return chunk

        input_text = sensory_data["input_text"]
        tokens = sensory_data.get("tokens", [])

        # 1. Extract keywords (BACKWARD COMPATIBLE)
        keywords = self._extract_keywords(tokens, input_text)

        # 2. Map keywords to Memory Web concepts
        concepts = self._map_keywords_to_concepts(keywords)

        # 3. Detect opposing concept pairs (contradictions, tensions)
        oppositions = self._detect_oppositions(concepts, keywords)

        # 4. Compute tension coefficients (CRITICAL FOR HOUSING!)
        tension_coefficients = self._compute_tension_coefficients(oppositions, input_text)

        # 5. Classify question type
        question_type = self._classify_question_type(input_text)

        # 6. Analyze sentiment
        sentiment = self._analyze_sentiment(input_text, keywords)

        # 7. Extract named entities (if spaCy available)
        entities = self._extract_entities(input_text)

        # 8. Detect semantic relations
        relations = self._detect_semantic_relations(concepts, input_text)

        # Create comprehensive pattern data
        pattern_data = {
            # Backward compatible
            "keywords": keywords,

            # NEW: Concept mapping
            "concepts": concepts,
            "concept_count": len(concepts),

            # NEW: Tension detection (KEY FOR VERDANT!)
            "oppositions": oppositions,
            "tension_coefficients": tension_coefficients,
            "max_tension": max(tension_coefficients.values()) if tension_coefficients else 0.0,

            # NEW: Question classification
            "question_type": question_type["type"],
            "question_confidence": question_type["confidence"],
            "question_features": question_type["features"],

            # NEW: Sentiment
            "sentiment": sentiment,

            # NEW: Named entities
            "entities": entities,

            # NEW: Semantic relations
            "relations": relations,

            # Metadata
            "timestamp": time.time(),
            "spacy_available": SPACY_AVAILABLE and nlp is not None,
            "memory_bridge_active": self.memory_bridge is not None
        }

        # Update chunk
        chunk.update_section("pattern_recognition_section", pattern_data)

        # Update statistics
        self.stats["chunks_processed"] += 1
        self.stats["concepts_mapped"] += len(concepts)
        self.stats["tensions_detected"] += len(oppositions)
        self.stats["questions_classified"] += 1

        # Log processing
        self.log_process(chunk, "pattern_recognition", {
            "keywords_extracted": len(keywords),
            "concepts_mapped": len(concepts),
            "oppositions_found": len(oppositions),
            "question_type": question_type["type"],
            "sentiment": sentiment["label"]
        })

        return chunk

    # ============================================================
    # INITIALIZATION METHODS
    # ============================================================

    def _initialize_opposition_pairs(self) -> Dict[Tuple[str, str], float]:
        """
        Initialize known opposition pairs with base tension strengths.

        Returns:
            Dictionary mapping (concept_a, concept_b) tuples to base tension values (0.0-1.0)
        """
        # These pairs represent common conceptual oppositions in various domains
        pairs = {
            # Binary antonyms (high base tension)
            ("good", "bad"): 0.9,
            ("good", "evil"): 0.95,
            ("safe", "dangerous"): 0.85,
            ("secure", "insecure"): 0.8,
            ("true", "false"): 1.0,
            ("right", "wrong"): 0.9,
            ("hot", "cold"): 0.8,
            ("light", "dark"): 0.75,
            ("on", "off"): 1.0,
            ("yes", "no"): 1.0,

            # Value tensions (moderate-high base tension)
            ("privacy", "security"): 0.7,
            ("privacy", "transparency"): 0.75,
            ("individual", "collective"): 0.65,
            ("liberty", "security"): 0.7,
            ("freedom", "control"): 0.75,
            ("autonomy", "paternalism"): 0.8,
            ("innovation", "tradition"): 0.6,
            ("progress", "conservation"): 0.65,
            ("efficiency", "thoroughness"): 0.5,
            ("speed", "accuracy"): 0.6,

            # Ethical tensions (moderate base tension)
            ("utilitarian", "deontological"): 0.6,
            ("consequentialism", "virtue ethics"): 0.55,
            ("benefit", "harm"): 0.85,
            ("help", "hurt"): 0.9,
            ("fair", "unfair"): 0.9,
            ("just", "unjust"): 0.9,

            # Cognitive tensions (lower base tension)
            ("certain", "uncertain"): 0.7,
            ("knowledge", "ignorance"): 0.75,
            ("rational", "emotional"): 0.5,
            ("logic", "intuition"): 0.45,
            ("objective", "subjective"): 0.6,

            # Political/social tensions (moderate base tension)
            ("liberal", "conservative"): 0.65,
            ("left", "right"): 0.7,
            ("public", "private"): 0.55,
            ("cooperation", "competition"): 0.5,
            ("equality", "hierarchy"): 0.7,
        }

        # Create symmetric pairs (both orderings)
        symmetric_pairs = {}
        for (a, b), strength in pairs.items():
            symmetric_pairs[(a, b)] = strength
            symmetric_pairs[(b, a)] = strength

        return symmetric_pairs

    def _initialize_sentiment_lexicon(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize sentiment lexicon with positive/negative words.

        Returns:
            Dictionary with 'positive' and 'negative' word sets
        """
        return {
            "positive": {
                "good", "great", "excellent", "wonderful", "fantastic", "amazing",
                "love", "like", "enjoy", "happy", "joy", "pleased", "glad",
                "best", "better", "improve", "benefit", "helpful", "useful",
                "success", "successful", "win", "achieve", "accomplish",
                "beautiful", "brilliant", "impressive", "outstanding",
                "perfect", "positive", "appreciate", "valuable", "effective",
                "right", "correct", "true", "honest", "fair", "just"
            },
            "negative": {
                "bad", "terrible", "awful", "horrible", "worse", "worst",
                "hate", "dislike", "angry", "sad", "unhappy", "disappointed",
                "problem", "issue", "fail", "failure", "lose", "loss",
                "wrong", "incorrect", "false", "unfair", "unjust",
                "harm", "damage", "hurt", "pain", "danger", "dangerous",
                "difficult", "hard", "impossible", "negative", "poor",
                "waste", "useless", "ineffective", "inadequate"
            }
        }

    def _initialize_question_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Initialize regex patterns for question type classification.

        Returns:
            Dictionary mapping question types to list of pattern dictionaries
        """
        return {
            "factual": [
                {"pattern": r"\bwhat is\b", "weight": 1.0},
                {"pattern": r"\bwhat are\b", "weight": 1.0},
                {"pattern": r"\bwho is\b", "weight": 1.0},
                {"pattern": r"\bwhere is\b", "weight": 1.0},
                {"pattern": r"\bwhen did\b", "weight": 1.0},
                {"pattern": r"\bhow many\b", "weight": 1.0},
                {"pattern": r"\bhow much\b", "weight": 1.0},
            ],
            "ethical": [
                {"pattern": r"\bshould\b", "weight": 0.8},
                {"pattern": r"\bought to\b", "weight": 0.9},
                {"pattern": r"\bis it right\b", "weight": 1.0},
                {"pattern": r"\bis it wrong\b", "weight": 1.0},
                {"pattern": r"\bmorally\b", "weight": 1.0},
                {"pattern": r"\bethical\b", "weight": 1.0},
                {"pattern": r"\bfair\b", "weight": 0.6},
                {"pattern": r"\bjust\b", "weight": 0.6},
            ],
            "hypothetical": [
                {"pattern": r"\bwhat if\b", "weight": 1.0},
                {"pattern": r"\bsuppose\b", "weight": 0.9},
                {"pattern": r"\bimagine\b", "weight": 0.8},
                {"pattern": r"\bcould\b", "weight": 0.5},
                {"pattern": r"\bwould\b", "weight": 0.5},
                {"pattern": r"\bmight\b", "weight": 0.4},
            ],
            "comparative": [
                {"pattern": r"\bbetter than\b", "weight": 1.0},
                {"pattern": r"\bworse than\b", "weight": 1.0},
                {"pattern": r"\bcompare\b", "weight": 0.9},
                {"pattern": r"\bdifference between\b", "weight": 1.0},
                {"pattern": r"\bversus\b", "weight": 0.8},
                {"pattern": r"\bvs\b", "weight": 0.8},
                {"pattern": r"\bmore .* than\b", "weight": 0.7},
                {"pattern": r"\bless .* than\b", "weight": 0.7},
            ],
            "causal": [
                {"pattern": r"\bwhy\b", "weight": 0.9},
                {"pattern": r"\bhow does\b", "weight": 0.8},
                {"pattern": r"\bhow do\b", "weight": 0.8},
                {"pattern": r"\bcause\b", "weight": 0.9},
                {"pattern": r"\breason\b", "weight": 0.7},
                {"pattern": r"\bexplain\b", "weight": 0.8},
                {"pattern": r"\bbecause\b", "weight": 0.6},
            ],
            "definitional": [
                {"pattern": r"\bdefine\b", "weight": 1.0},
                {"pattern": r"\bdefinition of\b", "weight": 1.0},
                {"pattern": r"\bmeaning of\b", "weight": 0.9},
                {"pattern": r"\bmean by\b", "weight": 0.8},
            ],
            "procedural": [
                {"pattern": r"\bhow to\b", "weight": 1.0},
                {"pattern": r"\bhow can i\b", "weight": 0.9},
                {"pattern": r"\bhow do i\b", "weight": 0.9},
                {"pattern": r"\bsteps to\b", "weight": 0.9},
                {"pattern": r"\bprocess for\b", "weight": 0.8},
            ],
        }

    # ============================================================
    # KEYWORD EXTRACTION (BACKWARD COMPATIBLE)
    # ============================================================

    def _extract_keywords(self, tokens: List[str], text: str) -> List[str]:
        """
        Extract keywords from tokens with stopword filtering.
        Maintains backward compatibility with existing pipeline.

        Args:
            tokens: List of tokens from sensory input
            text: Original input text

        Returns:
            List of keyword strings
        """
        # Common English stopwords
        stopwords = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "will", "with", "the", "this", "but", "they", "have",
            "had", "what", "when", "where", "who", "which", "why", "how"
        }

        # If tokens provided, filter stopwords and short words
        if tokens:
            keywords = [
                token.lower() for token in tokens
                if token.lower() not in stopwords
                and len(token) > 2
                and not token.isdigit()
            ]
        else:
            # Fallback: simple tokenization
            words = re.findall(r'\b\w+\b', text.lower())
            keywords = [
                word for word in words
                if word not in stopwords
                and len(word) > 2
                and not word.isdigit()
            ]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords

    # ============================================================
    # CONCEPT MAPPING (MEMORY WEB INTEGRATION)
    # ============================================================

    def _map_keywords_to_concepts(self, keywords: List[str]) -> List[str]:
        """
        Map keywords to concepts in Memory Web using graph relationships.
        Falls back to keywords if Memory Web unavailable.

        Args:
            keywords: List of extracted keywords

        Returns:
            List of concept strings (from Memory Web or keywords)
        """
        # If no memory bridge, use keywords as concepts
        if not self.memory_bridge or not hasattr(self.memory_bridge, 'memory_web'):
            return keywords

        memory_web = self.memory_bridge.memory_web
        concepts = set()

        # Try to find each keyword in the Memory Web
        for keyword in keywords:
            # Direct match
            if memory_web.has_node(keyword):
                concepts.add(keyword)
            else:
                # Fuzzy match: check if keyword is substring of any node
                for node in memory_web.nodes():
                    if keyword in node.lower() or node.lower() in keyword:
                        concepts.add(node)
                        break
                else:
                    # No match found, keep keyword as concept
                    concepts.add(keyword)

        return list(concepts)

    # ============================================================
    # OPPOSITION DETECTION (CRITICAL FOR HOUSING OPERATOR)
    # ============================================================

    def _detect_oppositions(self, concepts: List[str], keywords: List[str]) -> List[Tuple[str, str]]:
        """
        Detect opposing concept pairs (contradictions, antonyms, value tensions).

        This is CRITICAL for Verdant's thermodynamic contradiction handling.
        The Housing operator uses these oppositions to construct contradiction geometry.

        Args:
            concepts: List of concepts from Memory Web
            keywords: List of keywords (fallback)

        Returns:
            List of (concept_a, concept_b) tuples representing oppositions
        """
        oppositions = []
        search_terms = concepts if concepts else keywords

        # 1. Check against known opposition pairs
        for i, term_a in enumerate(search_terms):
            for term_b in search_terms[i+1:]:
                # Check both orderings
                if (term_a, term_b) in self.opposition_pairs:
                    oppositions.append((term_a, term_b))
                elif (term_b, term_a) in self.opposition_pairs:
                    oppositions.append((term_b, term_a))

        # 2. Check for negation patterns (e.g., "safe" vs "unsafe")
        negation_prefixes = ["un", "non", "in", "im", "dis", "anti"]
        for term in search_terms:
            for prefix in negation_prefixes:
                # Check if negated form exists
                if term.startswith(prefix):
                    base_form = term[len(prefix):]
                    if base_form in search_terms:
                        oppositions.append((base_form, term))
                else:
                    # Check if term with prefix exists
                    for p in negation_prefixes:
                        negated = p + term
                        if negated in search_terms:
                            oppositions.append((term, negated))

        return oppositions

    def _compute_tension_coefficients(
        self,
        oppositions: List[Tuple[str, str]],
        text: str
    ) -> Dict[Tuple[str, str], float]:
        """
        Compute tension coefficients for opposing concept pairs.

        Tension coefficients range from 0.0 (no tension) to 1.0 (maximum tension).
        These values feed directly into the Housing operator for contradiction geometry.

        The coefficient is computed by:
        1. Starting with base opposition strength
        2. Modulating by textual proximity (closer = higher tension)
        3. Adjusting for contrastive language patterns

        Args:
            oppositions: List of (concept_a, concept_b) opposition pairs
            text: Input text for context analysis

        Returns:
            Dictionary mapping (concept_a, concept_b) to tension coefficient (0.0-1.0)
        """
        tension_coefficients = {}
        text_lower = text.lower()

        for concept_a, concept_b in oppositions:
            # Start with base strength from opposition pairs
            base_strength = self.opposition_pairs.get(
                (concept_a, concept_b),
                self.opposition_pairs.get((concept_b, concept_a), 0.5)
            )

            # Modulate by proximity in text
            proximity_factor = 1.0
            if self._concepts_are_proximate(concept_a, concept_b, text_lower, window=20):
                proximity_factor = 1.2  # Increase tension if concepts appear close together

            # Adjust for contrastive language
            contrastive_patterns = [
                r"\b" + re.escape(concept_a) + r"\s+(but|however|versus|vs|rather than|not)\s+" + re.escape(concept_b),
                r"\b" + re.escape(concept_b) + r"\s+(but|however|versus|vs|rather than|not)\s+" + re.escape(concept_a),
            ]

            contrastive_factor = 1.0
            for pattern in contrastive_patterns:
                if re.search(pattern, text_lower):
                    contrastive_factor = 1.3  # Significant increase for explicit contrast
                    break

            # Compute final coefficient (clamped to [0.0, 1.0])
            coefficient = min(1.0, base_strength * proximity_factor * contrastive_factor)
            tension_coefficients[(concept_a, concept_b)] = coefficient

        return tension_coefficients

    def _concepts_are_proximate(
        self,
        concept_a: str,
        concept_b: str,
        text: str,
        window: int = 20
    ) -> bool:
        """
        Check if two concepts appear within a word window in the text.

        Args:
            concept_a: First concept
            concept_b: Second concept
            text: Text to search (should be lowercased)
            window: Maximum word distance to consider proximate

        Returns:
            True if concepts appear within window, False otherwise
        """
        # Find all positions of concept_a
        words = text.split()
        positions_a = [i for i, word in enumerate(words) if concept_a in word]
        positions_b = [i for i, word in enumerate(words) if concept_b in word]

        # Check if any positions are within window
        for pos_a in positions_a:
            for pos_b in positions_b:
                if abs(pos_a - pos_b) <= window:
                    return True

        return False

    # ============================================================
    # QUESTION TYPE CLASSIFICATION
    # ============================================================

    def _classify_question_type(self, text: str) -> Dict[str, Any]:
        """
        Classify the question type using pattern matching.

        Types: factual, ethical, hypothetical, comparative, causal, definitional, procedural

        Args:
            text: Input text

        Returns:
            Dictionary with 'type', 'confidence', and 'features' keys
        """
        text_lower = text.lower()

        # Check if it's actually a question
        is_question = "?" in text or any(
            text_lower.startswith(q) for q in ["what", "who", "where", "when", "why", "how", "should", "could", "would"]
        )

        # Score each question type
        type_scores = {}
        matched_patterns = {}

        for qtype, patterns in self.question_patterns.items():
            score = 0.0
            matches = []
            for pattern_dict in patterns:
                pattern = pattern_dict["pattern"]
                weight = pattern_dict["weight"]
                if re.search(pattern, text_lower):
                    score += weight
                    matches.append(pattern)
            type_scores[qtype] = score
            matched_patterns[qtype] = matches

        # Find best match
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            best_score = type_scores[best_type]

            # Normalize confidence to [0, 1]
            # Multiple patterns can match, so we clamp at 1.0
            confidence = min(1.0, best_score)

            return {
                "type": best_type if is_question else "statement",
                "confidence": confidence if is_question else 0.0,
                "features": {
                    "is_question": is_question,
                    "pattern_matches": matched_patterns[best_type] if is_question else [],
                    "all_scores": type_scores
                }
            }
        else:
            return {
                "type": "statement",
                "confidence": 0.0,
                "features": {
                    "is_question": is_question,
                    "pattern_matches": [],
                    "all_scores": {}
                }
            }

    # ============================================================
    # SENTIMENT ANALYSIS
    # ============================================================

    def _analyze_sentiment(self, text: str, keywords: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment using lexicon-based approach.

        Args:
            text: Input text
            keywords: Extracted keywords

        Returns:
            Dictionary with 'label', 'score', and 'details' keys
        """
        text_lower = text.lower()
        words = set(text_lower.split())

        # Count positive and negative words
        positive_words = words & self.sentiment_lexicon["positive"]
        negative_words = words & self.sentiment_lexicon["negative"]

        pos_count = len(positive_words)
        neg_count = len(negative_words)

        # Compute sentiment score (-1.0 to 1.0)
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
            label = "neutral"
        else:
            score = (pos_count - neg_count) / total
            if score > 0.2:
                label = "positive"
            elif score < -0.2:
                label = "negative"
            else:
                label = "neutral"

        return {
            "label": label,
            "score": score,
            "details": {
                "positive_words": list(positive_words),
                "negative_words": list(negative_words),
                "positive_count": pos_count,
                "negative_count": neg_count
            }
        }

    # ============================================================
    # NAMED ENTITY RECOGNITION
    # ============================================================

    def _extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extract named entities using spaCy if available, otherwise simple heuristics.

        Args:
            text: Input text

        Returns:
            List of entity dictionaries with 'text', 'label', and 'source' keys
        """
        entities = []

        # Try spaCy first (if available and loaded)
        if SPACY_AVAILABLE and nlp is not None:
            try:
                doc = nlp(text)
                for ent in doc.ents:
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "source": "spacy"
                    })
                return entities
            except Exception as e:
                # Fall through to heuristic method
                pass

        # Fallback: simple heuristic extraction
        # Find capitalized words (potential proper nouns)
        words = text.split()
        for word in words:
            # Skip first word of sentence
            if word and word[0].isupper() and len(word) > 1:
                # Remove punctuation
                clean_word = re.sub(r'[^\w\s]', '', word)
                if clean_word:
                    entities.append({
                        "text": clean_word,
                        "label": "PROPN",  # Generic proper noun
                        "source": "heuristic"
                    })

        return entities

    # ============================================================
    # SEMANTIC RELATION DETECTION
    # ============================================================

    def _detect_semantic_relations(self, concepts: List[str], text: str) -> List[Dict[str, Any]]:
        """
        Detect semantic relations between concepts (causal, temporal, co-occurrence).

        Args:
            concepts: List of concepts
            text: Input text

        Returns:
            List of relation dictionaries with 'source', 'target', 'type', and 'confidence'
        """
        relations = []
        text_lower = text.lower()

        # Causal patterns
        causal_patterns = [
            (r"(\w+)\s+(causes?|leads? to|results? in|produces?)\s+(\w+)", "causal"),
            (r"(\w+)\s+(because of|due to)\s+(\w+)", "causal_reverse"),
        ]

        # Temporal patterns
        temporal_patterns = [
            (r"(\w+)\s+(before|after|during|while)\s+(\w+)", "temporal"),
        ]

        # Check patterns
        for pattern, rel_type in causal_patterns + temporal_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                if match.lastindex >= 2:
                    source = match.group(1)
                    target = match.group(3) if match.lastindex >= 3 else match.group(2)

                    # Check if source and target are in concepts
                    if any(source in c or c in source for c in concepts) and \
                       any(target in c or c in target for c in concepts):
                        relations.append({
                            "source": source,
                            "target": target,
                            "type": rel_type,
                            "confidence": 0.7
                        })

        # Co-occurrence (concepts appearing in same context)
        for i, concept_a in enumerate(concepts):
            for concept_b in concepts[i+1:]:
                if self._concepts_are_proximate(concept_a, concept_b, text_lower, window=10):
                    relations.append({
                        "source": concept_a,
                        "target": concept_b,
                        "type": "co-occurrence",
                        "confidence": 0.5
                    })

        return relations