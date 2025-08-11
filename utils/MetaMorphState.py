from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class InputColumnData(BaseModel):
    column_name: str
    values: List[Optional[Any]]

class parsedData(BaseModel):
    column_name: str
    parsed_output: List[Optional[Any]]
    model_confidence: float
    notes: Optional[str]

class SchemaInferenceResults(BaseModel):
    inferred_type: str
    confidence: float
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
    column_name: str
    head: List[Any] = Field(default_factory=list)
    tail: List[Any] = Field(default_factory=list)
    random_sample: List[Any] = Field(default_factory=list)
    n_unique_preview: int | None = None
    unique_preview: List[Any] = Field(default_factory=list)
    row_count: int
    note: str | None = "Values truncated for token budget"



#Main MetaMorph State:

class MetaMorphState(BaseModel):
    input_column_data: Optional[InputColumnData] = None
    ColumnSample: Optional[ColSample] = None
    parsed_data_output: Optional[parsedData] = None
    schema_inference: Optional[SchemaInferenceResults] = None
    refinement_results: Optional[RefinementResults] = None
    validator_data: Optional[ValidatorData] = None

