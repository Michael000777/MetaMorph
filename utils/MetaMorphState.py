from typing import Optional, List, Dict, Any
from pydantic import BaseModel


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



#Main MetaMorph State:

class MetaMorphState(BaseModel):
    input_column_data: Optional[InputColumnData] = None
    parsed_data_output: Optional[parsedData] = None
    schema_inference: Optional[SchemaInferenceResults] = None
    refinement_results: Optional[RefinementResults] = None
    validator_data: Optional[ValidatorData] = None
