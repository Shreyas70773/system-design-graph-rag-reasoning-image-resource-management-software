"""
Pipeline Logger for GraphRAG Generation
========================================
Provides detailed logging and visualization of the generation pipeline
for demonstration and debugging purposes.

This module captures every step of the GraphRAG process:
1. Scene Decomposition
2. Constraint Resolution  
3. Preference Application
4. Prompt Compilation
5. Image Generation
6. Feedback Recording

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import uuid


class PipelineStage(str, Enum):
    """Stages in the generation pipeline."""
    RECEIVED = "received"
    SCENE_DECOMPOSITION = "scene_decomposition"
    CONSTRAINT_QUERY = "constraint_query"
    PREFERENCE_RETRIEVAL = "preference_retrieval"
    CONFLICT_RESOLUTION = "conflict_resolution"
    PROMPT_COMPILATION = "prompt_compilation"
    IMAGE_GENERATION = "image_generation"
    TEXT_GENERATION = "text_generation"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PipelineStep:
    """A single step in the pipeline execution."""
    stage: PipelineStage
    timestamp: datetime
    duration_ms: float
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    details: str
    neo4j_queries: List[str] = field(default_factory=list)
    relationships_created: List[Dict[str, str]] = field(default_factory=list)
    relationships_read: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "stage": self.stage.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "details": self.details,
            "neo4j_queries": self.neo4j_queries,
            "relationships_created": self.relationships_created,
            "relationships_read": self.relationships_read
        }


@dataclass
class PipelineExecution:
    """Complete pipeline execution log."""
    execution_id: str
    brand_id: str
    prompt: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[PipelineStep] = field(default_factory=list)
    total_duration_ms: float = 0
    success: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "execution_id": self.execution_id,
            "brand_id": self.brand_id,
            "prompt": self.prompt,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict:
        """Generate a human-readable summary."""
        return {
            "total_steps": len(self.steps),
            "stages_completed": [s.stage.value for s in self.steps],
            "total_neo4j_queries": sum(len(s.neo4j_queries) for s in self.steps),
            "relationships_read": sum(len(s.relationships_read) for s in self.steps),
            "relationships_created": sum(len(s.relationships_created) for s in self.steps),
            "slowest_stage": max(self.steps, key=lambda s: s.duration_ms).stage.value if self.steps else None
        }


class PipelineLogger:
    """
    Logger for capturing and visualizing the GraphRAG pipeline.
    
    Usage:
        logger = PipelineLogger("brand_123", "Create modern product image")
        
        with logger.stage(PipelineStage.SCENE_DECOMPOSITION) as step:
            step.input_data = {"prompt": "..."}
            result = decompose(prompt)
            step.output_data = {"elements": result.elements}
            step.details = f"Decomposed into {len(result.elements)} elements"
        
        execution_log = logger.get_execution()
    """
    
    def __init__(self, brand_id: str, prompt: str):
        self.execution = PipelineExecution(
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
            brand_id=brand_id,
            prompt=prompt,
            started_at=datetime.now()
        )
        self._current_step: Optional[PipelineStep] = None
        self._step_start: Optional[datetime] = None
    
    def start_stage(self, stage: PipelineStage, input_data: Dict = None) -> 'PipelineLogger':
        """Start a new pipeline stage."""
        self._step_start = datetime.now()
        self._current_step = PipelineStep(
            stage=stage,
            timestamp=self._step_start,
            duration_ms=0,
            input_data=input_data or {},
            output_data={},
            details=""
        )
        return self
    
    def add_neo4j_query(self, query: str, params: Dict = None):
        """Log a Neo4j query executed during this stage."""
        if self._current_step:
            # Truncate long queries for readability
            query_display = query[:200] + "..." if len(query) > 200 else query
            self._current_step.neo4j_queries.append(query_display)
    
    def add_relationship_read(self, from_node: str, relationship: str, to_node: str):
        """Log a relationship that was read from the graph."""
        if self._current_step:
            self._current_step.relationships_read.append({
                "from": from_node,
                "relationship": relationship,
                "to": to_node
            })
    
    def add_relationship_created(self, from_node: str, relationship: str, to_node: str):
        """Log a relationship that was created in the graph."""
        if self._current_step:
            self._current_step.relationships_created.append({
                "from": from_node,
                "relationship": relationship,
                "to": to_node
            })
    
    def end_stage(self, output_data: Dict = None, details: str = ""):
        """Complete the current stage."""
        if self._current_step and self._step_start:
            end_time = datetime.now()
            self._current_step.duration_ms = (end_time - self._step_start).total_seconds() * 1000
            self._current_step.output_data = output_data or {}
            self._current_step.details = details
            self.execution.steps.append(self._current_step)
            self._current_step = None
            self._step_start = None
    
    def log_error(self, error_message: str):
        """Log an error and mark execution as failed."""
        self.execution.error_message = error_message
        self.execution.success = False
        if self._current_step:
            self._current_step.stage = PipelineStage.ERROR
            self._current_step.details = error_message
            self.end_stage()
    
    def complete(self):
        """Mark the pipeline execution as complete."""
        self.execution.completed_at = datetime.now()
        self.execution.total_duration_ms = (
            self.execution.completed_at - self.execution.started_at
        ).total_seconds() * 1000
        self.execution.success = True
    
    def get_execution(self) -> PipelineExecution:
        """Get the complete execution log."""
        return self.execution
    
    def get_execution_dict(self) -> Dict:
        """Get execution log as dictionary."""
        return self.execution.to_dict()
    
    def print_summary(self):
        """Print a formatted summary to console."""
        print("\n" + "="*60)
        print(f"📊 PIPELINE EXECUTION: {self.execution.execution_id}")
        print("="*60)
        print(f"Brand: {self.execution.brand_id}")
        print(f"Prompt: {self.execution.prompt[:50]}...")
        print(f"Status: {'✅ SUCCESS' if self.execution.success else '❌ FAILED'}")
        print(f"Total Duration: {self.execution.total_duration_ms:.0f}ms")
        print("\n📋 STAGES:")
        
        for i, step in enumerate(self.execution.steps, 1):
            icon = self._get_stage_icon(step.stage)
            print(f"  {i}. {icon} {step.stage.value.upper()}")
            print(f"     Duration: {step.duration_ms:.0f}ms")
            print(f"     Details: {step.details}")
            if step.neo4j_queries:
                print(f"     Neo4j Queries: {len(step.neo4j_queries)}")
            if step.relationships_read:
                print(f"     Relationships Read: {len(step.relationships_read)}")
            if step.relationships_created:
                print(f"     Relationships Created: {len(step.relationships_created)}")
            print()
        
        print("="*60 + "\n")
    
    def _get_stage_icon(self, stage: PipelineStage) -> str:
        icons = {
            PipelineStage.RECEIVED: "📥",
            PipelineStage.SCENE_DECOMPOSITION: "🎬",
            PipelineStage.CONSTRAINT_QUERY: "🔍",
            PipelineStage.PREFERENCE_RETRIEVAL: "💡",
            PipelineStage.CONFLICT_RESOLUTION: "⚖️",
            PipelineStage.PROMPT_COMPILATION: "📝",
            PipelineStage.IMAGE_GENERATION: "🎨",
            PipelineStage.TEXT_GENERATION: "✍️",
            PipelineStage.POST_PROCESSING: "🔧",
            PipelineStage.COMPLETED: "✅",
            PipelineStage.ERROR: "❌"
        }
        return icons.get(stage, "•")


# Global storage for recent executions (for demo purposes)
_recent_executions: List[PipelineExecution] = []
MAX_STORED_EXECUTIONS = 50


def store_execution(execution: PipelineExecution):
    """Store an execution for later retrieval."""
    global _recent_executions
    _recent_executions.insert(0, execution)
    if len(_recent_executions) > MAX_STORED_EXECUTIONS:
        _recent_executions = _recent_executions[:MAX_STORED_EXECUTIONS]


def get_recent_executions(limit: int = 10) -> List[Dict]:
    """Get recent pipeline executions."""
    return [e.to_dict() for e in _recent_executions[:limit]]


def get_execution_by_id(execution_id: str) -> Optional[Dict]:
    """Get a specific execution by ID."""
    for execution in _recent_executions:
        if execution.execution_id == execution_id:
            return execution.to_dict()
    return None
