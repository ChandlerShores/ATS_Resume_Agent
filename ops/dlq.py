"""Dead Letter Queue (DLQ) for handling permanent failures."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class DLQEntry:
    """Represents a failed job in the DLQ."""
    
    job_id: str
    stage: str
    reason: str
    timestamp: str
    input_data: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class DeadLetterQueue:
    """
    Dead Letter Queue for storing and managing failed jobs.
    
    Failed jobs are written to a JSONL file for later replay or analysis.
    """
    
    def __init__(self, dlq_file: str = "out/dlq.jsonl"):
        self.dlq_file = Path(dlq_file)
        self.dlq_file.parent.mkdir(parents=True, exist_ok=True)
    
    def add_entry(
        self,
        job_id: str,
        stage: str,
        reason: str,
        input_data: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> DLQEntry:
        """
        Add a failed job to the DLQ.
        
        Args:
            job_id: Unique job identifier
            stage: State machine stage where failure occurred
            reason: Human-readable failure reason
            input_data: Original input data (optional)
            error_details: Additional error information (optional)
            
        Returns:
            DLQEntry: The created DLQ entry
        """
        entry = DLQEntry(
            job_id=job_id,
            stage=stage,
            reason=reason,
            timestamp=datetime.utcnow().isoformat() + "Z",
            input_data=input_data,
            error_details=error_details
        )
        
        # Append to JSONL file
        with open(self.dlq_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')
        
        return entry
    
    def get_entries(self, limit: Optional[int] = None) -> List[DLQEntry]:
        """
        Retrieve entries from the DLQ.
        
        Args:
            limit: Maximum number of entries to return (None for all)
            
        Returns:
            List[DLQEntry]: List of DLQ entries
        """
        if not self.dlq_file.exists():
            return []
        
        entries = []
        with open(self.dlq_file, 'r', encoding='utf-8') as f:
            for line in f:
                if limit and len(entries) >= limit:
                    break
                entry_dict = json.loads(line.strip())
                entries.append(DLQEntry(**entry_dict))
        
        return entries
    
    def clear(self):
        """Clear all entries from the DLQ."""
        if self.dlq_file.exists():
            self.dlq_file.unlink()
    
    def get_by_job_id(self, job_id: str) -> Optional[DLQEntry]:
        """
        Find a DLQ entry by job_id.
        
        Args:
            job_id: Job identifier to search for
            
        Returns:
            Optional[DLQEntry]: Entry if found, None otherwise
        """
        entries = self.get_entries()
        for entry in entries:
            if entry.job_id == job_id:
                return entry
        return None


# Global DLQ instance
dlq = DeadLetterQueue()

