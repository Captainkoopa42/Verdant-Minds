import time
from typing import Dict, List, Tuple, Optional, Any, Set

from core.cognitive_chunk import CognitiveChunk

class BaseKing:
    """
    Base class for all kings in the Three Kings governance architecture.
    
    The Three Kings (Data King, Forefront King, and Ethics King) provide
    oversight and governance for the Unified Synthetic Mind system, each
    specializing in a different aspect of cognitive governance.
    """
    
    def __init__(self, king_name: str):
        """
        Initialize a new King.
        
        Args:
            king_name: Name of the king (e.g., "DataKing")
        """
        self.king_name = king_name
        self.influence_history = []
        self.oversight_metrics = {}
        self.blocks_supervised = []
        
    def oversee_processing(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Oversees processing of a CognitiveChunk. Must be overridden in child classes.
        
        Args:
            chunk: The cognitive chunk to oversee
            
        Returns:
            Processed cognitive chunk with oversight applied
            
        Raises:
            NotImplementedError: If not implemented by a child class
        """
        raise NotImplementedError(f"{self.king_name} must implement its own oversight logic.")

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Wrapper to conform to block interface."""
        print(f"{self.king_name} processing chunk {chunk.chunk_id}")
        return self.oversee_processing(chunk)
    
    def log_influence(self, chunk: CognitiveChunk, influence_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Logs the king's influence on processing.
        
        Args:
            chunk: The cognitive chunk being processed
            influence_type: Type of influence exerted (e.g., "data_oversight")
            details: Details about the influence
            
        Returns:
            Influence record
        """
        influence_record = {
            "king": self.king_name,
            "influence_type": influence_type,
            "timestamp": time.time(),
            "details": details
        }
        
        # Add to chunk's processing log
        chunk.add_processing_step(self.king_name, influence_type, details)
        
        # Add to king's influence history
        self.influence_history.append(influence_record)
        
        # Keep history at a reasonable size
        if len(self.influence_history) > 1000:
            self.influence_history = self.influence_history[-1000:]
            
        return influence_record
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this king.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "total_oversights": len(self.influence_history),
            "supervised_blocks": self.blocks_supervised,
            "metrics": self.oversight_metrics
        }
    
    def update_oversight_metrics(self, metric_name: str, value: Any):
        """
        Update a specific oversight metric.
        
        Args:
            metric_name: Name of the metric to update
            value: New value for the metric
        """
        self.oversight_metrics[metric_name] = value
    
    def evaluate_block_performance(self, block_name: str, chunk: CognitiveChunk) -> float:
        """
        Evaluate the performance of a supervised block.
        
        Args:
            block_name: Name of the block to evaluate
            chunk: Cognitive chunk with the block's processing results
            
        Returns:
            Performance score (0-1)
        """
        # Base implementation returns a neutral score
        # Child classes should override with specific evaluation logic
        return 0.5