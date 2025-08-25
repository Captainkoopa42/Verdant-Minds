import time
import re
from typing import Dict, Any, Optional

from src.blocks.base_block import BaseBlock
from src.core.cognitive_chunk import CognitiveChunk

class SensoryInputBlock(BaseBlock):
    """
    Block 1: Sensory Input
    
    Serves as the perceptual interface for the Unified Synthetic Mind,
    processing and normalizing raw input for further processing.
    """
    
    def __init__(self):
        """Initialize the Sensory Input block."""
        super().__init__("SensoryInput")
        
        # Initialize sensory buffer for temporal pattern detection
        self.sensory_buffer = []
        self.buffer_max_size = 10
        
        # Initialize input preprocessors
        self.preprocessors = {
            "text": self._preprocess_text,
            "structured_data": self._preprocess_structured_data,
            "image": self._preprocess_image,
            "audio": self._preprocess_audio
        }
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a chunk through sensory input.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk
        """
        # Extract sensory section if it exists
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        
        # Ensure we have the input
        if not sensory_data or "input_text" not in sensory_data:
            self.log_process(chunk, "error", {"message": "No input text provided"})
            return chunk
        
        # Process the input
        input_text = sensory_data["input_text"]
        processed_data = self._process_input(input_text)
        
        # Update the sensory section
        sensory_data.update(processed_data)
        chunk.update_section("sensory_input_section", sensory_data)
        
        # Log processing
        self.log_process(chunk, "input_processing", {
            "input_length": len(input_text),
            "token_count": len(input_text.split()),
            "input_type": processed_data["input_type"]
        })
        
        return chunk
    
    def create_chunk_from_input(self, input_text: str, metadata: Dict[str, Any] = None) -> CognitiveChunk:
        """
        Create a new cognitive chunk from input text.
        
        Args:
            input_text: The input text to process
            metadata: Optional metadata about the input
            
        Returns:
            A new cognitive chunk with sensory processing
        """
        # Create a new chunk
        chunk = CognitiveChunk()
        
        # Initial sensory data
        sensory_data = {
            "input_text": input_text,
            "input_timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Add initial sensory section
        chunk.add_section("sensory_input_section", sensory_data)
        
        # Process the chunk
        return self.process_chunk(chunk)
    
    def _process_input(self, input_text: str) -> Dict[str, Any]:
        """
        Process input text to extract features and annotate with metadata.
        
        Args:
            input_text: Raw input text
            
        Returns:
            Dictionary with processed input features
        """
        # Determine input type
        input_type = self._determine_input_type(input_text)
        
        # Basic tokenization and analysis
        tokens = self._tokenize(input_text)
        
        # Apply appropriate preprocessor
        preprocessed_data = self.preprocessors.get(input_type, self.preprocessors["text"])(input_text)
        
        # Add to sensory buffer for temporal pattern detection
        self._update_sensory_buffer(input_text)
        
        # Process data with basic feature extraction
        features = {
            "input_type": input_type,
            "token_count": len(tokens),
            "character_count": len(input_text),
            "sentiment_indicators": self._detect_sentiment_indicators(input_text),
            "tokens": tokens,
            "detected_languages": self._detect_language(input_text),
            "preprocessed_data": preprocessed_data,
            "temporal_context": self._get_temporal_context()
        }
        
        return features
    
    def _determine_input_type(self, input_text: str) -> str:
        """
        Determine the type of input (text, structured, etc.).
        
        Args:
            input_text: Input text to analyze
            
        Returns:
            Input type string
        """
        # Check for structured data indicators (JSON, CSV format)
        if (input_text.strip().startswith('{') and input_text.strip().endswith('}')) or \
           (input_text.strip().startswith('[') and input_text.strip().endswith(']')) or \
           re.search(r'\w+,\w+,\w+', input_text):
            return "structured_data"
            
        # Check for image descriptions
        if input_text.lower().startswith(('image:', 'pic:', 'picture:', 'photo:')):
            return "image"
            
        # Check for audio descriptions
        if input_text.lower().startswith(('audio:', 'sound:', 'recording:')):
            return "audio"
            
        # Default to text
        return "text"
    
    def _tokenize(self, text: str) -> list:
        """
        Simple tokenization of input text.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Simple word-based tokenization with basic punctuation handling
        return re.findall(r'\b[\w\']+\b|[.,!?;:]', text)
    
    def _detect_sentiment_indicators(self, text: str) -> Dict[str, float]:
        """
        Detect basic sentiment indicators in text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with sentiment scores
        """
        # Very simple sentiment detection based on keyword matching
        positive_words = ['good', 'great', 'excellent', 'happy', 'positive', 'like', 'love']
        negative_words = ['bad', 'terrible', 'horrible', 'sad', 'negative', 'dislike', 'hate']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(self._tokenize(text))
        
        positive_score = positive_count / max(1, total_words)
        negative_score = negative_count / max(1, total_words)
        
        return {
            "positive_score": positive_score,
            "negative_score": negative_score,
            "net_sentiment": positive_score - negative_score
        }
    
    def _detect_language(self, text: str) -> Dict[str, float]:
        """
        Detect the likely language of the text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with language probabilities
        """
        # In a real implementation, this would use a language detection library
        # For now, return a simple placeholder
        return {"english": 1.0}
    
    def _update_sensory_buffer(self, input_text: str):
        """
        Update the sensory buffer with new input.
        
        Args:
            input_text: New input text
        """
        # Add new input to buffer
        self.sensory_buffer.append({
            "text": input_text,
            "timestamp": time.time()
        })
        
        # Maintain buffer size
        if len(self.sensory_buffer) > self.buffer_max_size:
            self.sensory_buffer.pop(0)
    
    def _get_temporal_context(self) -> Dict[str, Any]:
        """
        Get temporal context from sensory buffer.
        
        Returns:
            Dictionary with temporal context information
        """
        # Create temporal context from buffer
        return {
            "buffer_size": len(self.sensory_buffer),
            "recent_inputs": [item["text"] for item in self.sensory_buffer[-3:]],
            "time_since_first_buffer_item": time.time() - self.sensory_buffer[0]["timestamp"] if self.sensory_buffer else 0
        }
    
    # Input preprocessing methods
    def _preprocess_text(self, text: str) -> Dict[str, Any]:
        """Preprocess plain text input."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return {
            "sentences": sentences,
            "sentence_count": len(sentences),
            "avg_sentence_length": sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        }
    
    def _preprocess_structured_data(self, text: str) -> Dict[str, Any]:
        """Preprocess structured data input (JSON, CSV, etc.)."""
        # In a real implementation, this would parse the structured data
        return {
            "format": "unknown",
            "is_valid": True,
            "structure_summary": "Structured data detected, pending detailed analysis"
        }
    
    def _preprocess_image(self, text: str) -> Dict[str, Any]:
        """Preprocess image description input."""
        return {
            "image_description": text.split(':', 1)[1] if ':' in text else text,
            "described_objects": []  # In a real implementation, this would extract objects
        }
    
    def _preprocess_audio(self, text: str) -> Dict[str, Any]:
        """Preprocess audio description input."""
        return {
            "audio_description": text.split(':', 1)[1] if ':' in text else text,
            "described_sounds": []  # In a real implementation, this would extract sounds
        }