from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field
import operator 
import sys 
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.deep_union import deep_union



class InputColumnData(BaseModel):
    column_name: str = Field(default_factory=str)
    values: List[Optional[Any]] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.values)
    
    @property
    def n_non_null(self) -> int:
        return sum(v is not None for v in self.values)
    

class parsedData(BaseModel):
    column_name: str = Field(default_factory=str)
    parsed_output: List[Optional[Any]] = Field(default_factory=list)
    model_confidence: float = Field(default_factory=float)
    notes: Optional[str] = Field(default_factory=str)

class SchemaInferenceResults(BaseModel):
    inferred_type: str = Field(default_factory=str)
    confidence: float = Field(default_factory=float)
    notes: Optional[str] = Field(default_factory=str)

class RefinementResults(BaseModel):
    cleaned_values: List[Optional[Any]]
    confidence: float
    refinement_attempts: float

class ValidatorData(BaseModel):
    passed: bool
    failed_rows: List[int]
    message: Optional[str] = None

class ColSample(BaseModel):
    column_name: str = Field(default_factory=str)
    head: List[Any] = Field(default_factory=list)
    tail: List[Any] = Field(default_factory=list)
    random_sample: List[Any] = Field(default_factory=list)
    n_unique_preview: int | None = None
    unique_preview: List[Any] = Field(default_factory=list)
    row_count: int
    note: str | None = "Values truncated for token budget"

class tracker(BaseModel):
    processed_column : List[str] = Field(default_factory=list)
    node_path : Dict[str, Dict[str, Optional[str]]] = Field(default_factory=dict)
    events_path: List[str] = Field(default_factory=list)


def _to_tracker(x: Optional[tracker | Dict[str, Any]]) -> tracker:
    if x is None:
        return tracker()
    if isinstance(x, tracker):
        return x
    if isinstance(x, dict):
        # tolerating partial patches
        return tracker(
            processed_column=x.get("processed_column", []),
            node_path=x.get("node_path", {}),
            events_path=x.get("events_path", []),
        )
    # last resort: trying pydantic coercion
    return tracker.model_validate(x)

def merge_tracker(left: Optional[tracker], right: Optional[tracker]) -> tracker:
    left = _to_tracker(left)
    right = _to_tracker(right)
    return tracker(
        processed_column = [*left.processed_column, *right.processed_column],
        node_path = deep_union(left.node_path, right.node_path),
        events_path = [*left.events_path, *right.events_path]
    )



#Main MetaMorph State:

class MetaMorphState(BaseModel):
    input_column_data: InputColumnData = Field(default_factory=InputColumnData)
    ColumnSample: ColSample = Field(default_factory=ColSample)
    parsed_data_output: parsedData = Field(default_factory=parsedData)
    schema_inference: SchemaInferenceResults = Field(default_factory=SchemaInferenceResults)
    refinement_results: Optional[RefinementResults] = None
    validator_data: Optional[ValidatorData] = None
    Node_Col_Tracker: Annotated[tracker, merge_tracker] = Field(default_factory=tracker)

