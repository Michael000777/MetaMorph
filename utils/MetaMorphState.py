from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field
import operator 
import sys 
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.deep_union import deep_union


class InputColumnData(BaseModel):
    column_name: str = Field(default_factory=str)
    values: List[Optional[Any]]

class parsedData(BaseModel):
    column_name: str = Field(default_factory=str)
    parsed_output: List[Optional[Any]]
    model_confidence: float = Field(default_factory=float)
    notes: Optional[str]

class SchemaInferenceResults(BaseModel):
    inferred_type: str = Field(default_factory=str)
    confidence: float = Field(default_factory=float)
    notes: Optional[str]

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
    processed_column : Annotated[List[str], operator.add] = Field(default_factory=list)
    node_path : Annotated[Dict[str, Dict[str, Optional[str]]], deep_union] = Field(default_factory=dict)
    events_path: Annotated[List[str], operator.add] = Field(default_factory=list)



#Main MetaMorph State:

class MetaMorphState(BaseModel):
    input_column_data: InputColumnData = Field(default_factory=InputColumnData)
    ColumnSample: ColSample = Field(default_factory=ColSample)
    parsed_data_output: parsedData = Field(default_factory=parsedData)
    schema_inference: SchemaInferenceResults = Field(default_factory=SchemaInferenceResults)
    refinement_results: Optional[RefinementResults] = None
    validator_data: Optional[ValidatorData] = None
    Node_Col_Tracker: tracker = Field(default_factory=tracker)

