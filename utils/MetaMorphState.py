from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class InputColumnData(BaseModel):
    column_name: str
    values: List[Optional[Any]]

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
    message:




class MetaMorphState(BaseModel):
    input_column_data: Optional[InputColumnData] = None
    schema_inference: Optional[SchemaInferenceResults] = None
    refinement_results: Optional[RefinementResults] = None
    validator_data: Optional[dict] = None
