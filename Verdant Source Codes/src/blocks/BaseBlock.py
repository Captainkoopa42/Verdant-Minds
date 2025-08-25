from typing import Dict, Any

from src.core.cognitive_chunk import CognitiveChunk

class BaseBlock:
    """
    Base class for all processing blocks in the Unified Synthetic Mind.
    Defines common interface and functionality for all blocks.
    """
    
    def __init__(self, block_name: str):
        """
        Initialize a new processing block.
        
        Args:
            block_name: Name of the block
        """
        self.block_name = block_name
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a cognitive chunk. Must be implemented by subclasses.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk
        """
        raise NotImplementedError(f"{self.block_name} must implement process_chunk")
    
    def log_process(self, chunk: CognitiveChunk, operation: str, details: Dict[str, Any]):
        """
        Log the processing step to the chunk's processing log.
        
        Args:
            chunk: The chunk being processed
            operation: Type of operation performed
            details: Details about the processing step
        """
        chunk.add_processing_step(self.block_name, operation, details)
    
    def get_block_name(self) -> str:
        """
        Get the name of this block.
        
        Returns:
            Block name
        """
        return self.block_name