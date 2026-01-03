from typing import Dict, List, Union, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime, timezone
import sys
import os
import pandas as pd
from pathlib import Path
from langgraph.graph import StateGraph
#from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import argparse





sys.path.append(str(Path(__file__).resolve().parent.parent))



from utils.thread import generate_thread_id
from utils.MetaMorphState import tracker, MetaMorphState, InputColumnData
from utils.tools import get_key, get_attr_or_item
from utils.ScribeTemplate import html_template
from input import build_sample_data




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
    
async def run_all(graph, dataset_id: str, columns: Dict[str, list], max_concurrency=5) -> DatasetSummary:

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

            try:
                summary = await colRunner(app, dataset_id, col, val, col_sample)
                return col, summary
            except Exception as e:
                return col, e
            
    results = await asyncio.gather(*[_colTask(c, v) for c, v in columns.items()])

    col_summaries: Dict[str, FinalDataSummary] = {}
    n_success = 0
    n_failed = 0

    for col, out in results:
        if isinstance(out, Exception):
            n_failed += 1
            col_summaries[col] = FinalDataSummary(
                trackerInfo=tracker(),
                confidence=0.0,
                ColNames={col: []},
                TransformedValues=[],
                error=f"{type(out).__name__}: {out}",
            )
            continue
    
        summary = out
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
"""
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

CleanedData = asyncio.run(run_all(
    "DatasetAlpha",
    {"patient_id": ["P001","P002","P003","P004","P005","P006"],
    "age_years": [34, 58, None, 45, 29, 72]},
))

#print(CleanedData.model_dump())
report_md = summarizeTransformations(CleanedData.model_dump())
print(report_md)

with open(f"MetaMorph_Report_{stamp}.md", "w", encoding="utf-8") as f:
    f.write(report_md)

html_report = html_template.render(**CleanedData.model_dump())
with open(f"MetaMorph_Report_{stamp}.html", "w") as f:
    f.write(html_report)
"""

# Final DF builder
def BuildFinalDf(df: pd.DataFrame, cleaned_data: DatasetSummary):
    """
    Building a final dataframe after transformation

    Key Rules Applied Here:
    - Failed columns are replaced with originals 
    - Missing column names will be replaced with originals 
    - Ensures number of rows are matching 
    """

    n_rows = len(df)
    out = pd.DataFrame(index=df.index)

    for col in df.columns:
        ColSumm = cleaned_data.colData.get(col)

        if ColSumm is None or ColSumm.error:
            out[col] = df[col]
            continue

        Transformed = ColSumm.TransformedValues or []
        k = len(Transformed)

        if k == 0:
            out[col] = df[col]
            continue

        names = (ColSumm.ColNames.get(col) if ColSumm.ColNames else None) or []
        if len(names) != k:
            names = [f"{col}__{i + 1}" for i in range(k)]

        for i in range(k):
            vals = Transformed[i] if i < len(Transformed) else []

            if len(vals) < n_rows:
                vals = vals + [None]*(n_rows - len(vals))
                print("Mismatch in row number, less in transfomed")

            elif len(vals) > n_rows:
                vals = vals[:n_rows]
                print("Mismatch in row number, more in transfomed")

            out[names[i]] = vals

    return out




#Implementing file parsing logic 
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Run MetaMorph concurrently on a dataset and generated a report."
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to CSV file to process."
    )

    parser.add_argument(
        "--dataset-id", "-d",
        help="Optional dataset identifier. Defaults to the input filename stem."
    )
    parser.add_argument(
        "--outdir", "-o",
        #default="./Reports/",
        help="Output directory for the generated report files."
    )
    parser.add_argument(
        "--llm", "-l",
        type=str,
        default="gpt-5-nano",
        help="OpenAI LLM model to use"
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=2,
        help="Maximum number of columns to process concurrently."
    )
    args = parser.parse_args()
    
    from utils.llm import set_llm_model
    set_llm_model(args.llm)
    
    from utils.llm import get_llm
    print("Using model:", get_llm().model_name)
    
    from supervisor import supervisor_node
    from schema_inference import schema_inference_node
    from meta_parser import parser_node
    from refinement import refinement_agent
    from validator import validator_node
    from imagoScribe import summarizeTransformations
    
    graph = StateGraph(MetaMorphState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("schemaInference", schema_inference_node)
    graph.add_node("parser_agent", parser_node)
    graph.add_node("refinement_agent", refinement_agent)
    graph.add_node("validator_agent", validator_node)

    graph.set_entry_point("supervisor")

    csv_path = Path(args.input).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    # Loading the CSV
    df = pd.read_csv(csv_path)
    columns = {col: df[col].tolist() for col in df.columns}

    dataset_id = args.dataset_id or csv_path.stem
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # Running METAMORPH on all columns 
    cleaned_data = asyncio.run(
        run_all(
            graph=graph,
            dataset_id=dataset_id,
            columns=columns,
            max_concurrency=args.max_concurrency,
        )
    )

    report_md = summarizeTransformations(cleaned_data.model_dump())
    print(report_md)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with open(f"{outdir}/MetaMorph_Report_{stamp}.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    html_report = html_template.render(**cleaned_data.model_dump())
    with open(f"{outdir}/MetaMorph_Report_{stamp}.html", "w") as f:
        f.write(html_report)

    #writing out final df
    cleaned_df = BuildFinalDf(df, cleaned_data)

    cleaned_csv_path = outdir / f"MetaMorph_Cleaned_{stamp}.csv"
    cleaned_df.to_csv(cleaned_csv_path, index=False)
    print(f"Wrote cleaned CSV: {cleaned_csv_path}")