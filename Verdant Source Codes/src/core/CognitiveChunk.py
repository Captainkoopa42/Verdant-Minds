import time
from typing import Dict, Any, List, Optional
from uuid import uuid4

class CognitiveChunk:
    """
    Core data structure for information processing in the Unified Synthetic Mind.
    Represents a cohesive unit of cognitive processing with structured sections.
    """
    
    def __init__(self, chunk_id: str = None):
        """
        Initialize a new cognitive chunk.
        
        Args:
            chunk_id: Optional identifier for the chunk
        """
        self.chunk_id = chunk_id or f"chunk_{time.time_ns()}_{uuid4().hex[:8]}"
        self.creation_time = time.time()
        self.sections = {}
        self.processing_log = []
        
    def add_section(self, section_name: str, content: Dict[str, Any]):
        """
        Add a new section to the chunk.
        
        Args:
            section_name: Name of the section
            content: Dictionary containing section content
        """
        if section_name in self.sections:
            raise ValueError(f"Section {section_name} already exists in this chunk")
            
        self.sections[section_name] = content
        
    def update_section(self, section_name: str, content: Dict[str, Any]):
        """
        Update an existing section or create if it doesn't exist.
        
        Args:
            section_name: Name of the section
            content: Dictionary containing updated section content
        """
        self.sections[section_name] = content
        
    def get_section_content(self, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Get content from a specified section.
        
        Args:
            section_name: Name of the section to retrieve
            
        Returns:
            Section content dictionary or None if section doesn't exist
        """
        return self.sections.get(section_name)
    
    def add_processing_step(self, processor_name: str, operation: str, details: Dict[str, Any]):
        """
        Add a processing step to the chunk's processing log.
        
        Args:
            processor_name: Name of the component that processed the chunk
            operation: Type of operation performed
            details: Details about the processing step
        """
        self.processing_log.append({
            "timestamp": time.time(),
            "processor": processor_name,
            "operation": operation,
            "details": details
        })
        
    def get_processing_history(self, processor_name: str = None) -> List[Dict[str, Any]]:
        """
        Get processing history, optionally filtered by processor.
        
        Args:
            processor_name: Optional processor name to filter by
            
        Returns:
            List of processing steps
        """
        if processor_name:
            return [step for step in self.processing_log if step["processor"] == processor_name]
        return self.processing_log
    
    def merge_chunk(self, other_chunk: 'CognitiveChunk'):
        """
        Merge another chunk into this one.
        
        Args:
            other_chunk: Another CognitiveChunk to merge with this one
        """
        # Merge sections
        for section_name, content in other_chunk.sections.items():
            if section_name in self.sections:
                # For existing sections, update with non-overlapping keys
                for key, value in content.items():
                    if key not in self.sections[section_name]:
                        self.sections[section_name][key] = value
            else:
                # For new sections, simply add them
                self.sections[section_name] = content
                
        # Merge processing log
        self.processing_log.extend(other_chunk.processing_log)
