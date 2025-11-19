from typing import Dict, List, Union, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime, timezone
import sys
import os
import pandas as pd
from pathlib import Path
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


from supervisor import supervisor_node
from schema_inference import schema_inference_node
from meta_parser import parser_node
from refinement import refinement_agent
from validator import validator_node
from imagoScribe import summarizeTransformations, html_template


sys.path.append(str(Path(__file__).resolve().parent.parent))



from utils.thread import generate_thread_id
from utils.MetaMorphState import tracker, MetaMorphState, InputColumnData
from utils.tools import get_key, get_attr_or_item
from input import build_sample_data


graph = StateGraph(MetaMorphState)

graph.add_node("supervisor", supervisor_node)
graph.add_node("schemaInference", schema_inference_node)
graph.add_node("parser_agent", parser_node)
graph.add_node("refinement_agent", refinement_agent)
graph.add_node("validator_agent", validator_node)


graph.set_entry_point("supervisor")

JSONScalar = Union[str, int, float, bool, None]

class FinalDataSummary(BaseModel):
    trackerInfo: tracker
    confidence: float
    ColNames: Dict[str, List[str]]
    TransformedValues: List[List[JSONScalar]]
    error: Optional[str] = None

class DatasetSummary(BaseModel):
    dataset_id: str
    started_at: str
    finished_at: str
    n_success: int
    n_failed: int
    colData: Dict[str, FinalDataSummary]


async def colRunner(app, dataset_id: str, col_name: str, col_values: list, col_sample):
    init = MetaMorphState(
        input_column_data=InputColumnData(
            column_name=col_name,
            values=col_values),
        ColumnSample=col_sample,
    )
    thread_id = generate_thread_id(dataset_id)
    config = {"configurable": {"thread_id": f"{thread_id}:{col_name}"}}

    FinalState = await app.ainvoke(init, config=config)

    try:

        ParsedOut = get_key(FinalState, "parsed_data_output")
        Refined = get_key(FinalState, "refinement_results")
        TrackerInfo = get_key(FinalState, "Node_Col_Tracker")


        ColumnNames = get_attr_or_item(ParsedOut, "column_name")
        TransformedData = get_attr_or_item(Refined, "cleaned_values")
        ModelConfidence = get_attr_or_item(Refined, "confidence", 0.0)
        
        #print(f"ColNames: {ColumnNames}\n")
        ColumnNames 

        return FinalDataSummary(
            trackerInfo=TrackerInfo,
            confidence=ModelConfidence,
            ColNames=ColumnNames,
            TransformedValues=TransformedData,
        )

    except Exception as e:
        return FinalDataSummary(
            trackerInfo=tracker(),
            confidence=0.0,
            ColNames={col_name: []}, #double check later
            TransformedValues=[],
            error=f"{type(e).__name__}: {e}",
        )
    
async def run_all(dataset_id: str, columns: Dict[str, list], max_concurrency=5) -> DatasetSummary:

    #cp = AsyncSqliteSaver.from_conn_string("metamorph.db")

    #async with cp as checkpointer:
        #app = graph.compile(checkpointer=checkpointer)
    app = graph.compile()
    sem = asyncio.Semaphore(max_concurrency)
        
    StartTime = datetime.now(timezone.utc).isoformat()

    async def _colTask(col, val):
        async with sem:
            #inserting panda series for each column
            series_data = pd.Series(val, name=col)

            col_sample = build_sample_data(series_data)
            return col, await colRunner(app, dataset_id, col, val, col_sample)
            
    results = await asyncio.gather(*[_colTask(c, v) for c, v in columns.items()], return_exceptions=False)

    col_summaries: Dict[str, FinalDataSummary] = {}
    n_success = n_failed = 0
    for col, summary in results:
        col_summaries[col] = summary
        if summary.error:
            n_failed += 1
        else:
            n_success += 1

    EndTime = datetime.now(timezone.utc).isoformat()

    return DatasetSummary(
        dataset_id=dataset_id,
        started_at=StartTime,
        finished_at=EndTime,
        n_success=n_success,
        n_failed=n_failed,
        colData=col_summaries,
    )

#>>>>>> Testing <<<<<<<<
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

"""
from data.data3 import camera_storage_moderate


CleanedData = asyncio.run(
    run_all(
        "CameraStorageModerate",
        camera_storage_moderate,
    )
)
"""

csv_path = Path(__file__).resolve().parent.parent /"data"/"data1.csv"
df = pd.read_csv(csv_path)
columns = {col: df[col].tolist() for col in df.columns}

CleanedData = asyncio.run(run_all(
    "data1",
    columns,

))

"""
CleanedData = asyncio.run(run_all(
    "DatasetAlpha",
    {"patient_id": ["P001","P002","P003","P004","P005","P006"],
    "age_years": [34, 58, None, 45, 29, 72]},
))
"""

#print(CleanedData.model_dump())
report_md = summarizeTransformations(CleanedData.model_dump())
print(report_md)

with open(f"MetaMorph_Report_{stamp}.md", "w", encoding="utf-8") as f:
    f.write(report_md)

html_report = html_template.render(**CleanedData.model_dump())
with open(f"MetaMorph_Report_{stamp}.html", "w") as f:
    f.write(html_report)

