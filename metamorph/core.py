from __future__ import annotations

from typing import Any, Dict, List, Union, Optional
from pydantic import BaseModel, Field
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import sys
import json
import logging
import pandas as pd
from pathlib import Path
from langgraph.graph import StateGraph
from langgraph.errors import GraphRecursionError
import argparse





sys.path.append(str(Path(__file__).resolve().parent.parent))

from .supervisor import supervisor_node
from .schema_inference import schema_inference_node
from .meta_parser import parser_node
from .refinement import refinement_agent
from .validator import validator_node
from .imagoScribe import summarizeTransformations


from utils.llm import LLMClientProvider, LLMProviderConfig, use_llm_provider
from utils.thread import generate_thread_id
from utils.MetaMorphState import tracker, MetaMorphState, InputColumnData
from utils.tools import get_key, get_attr_or_item
from utils.ScribeTemplate import html_template
from .input import build_sample_data




JSONScalar = Union[str, int, float, bool, None]
DEFAULT_OUTDIR = "Reports"
DEFAULT_GRAPH_RECURSION_LIMIT = 24
RUN_MANIFEST_FILENAME = "run.json"
SUPPORTED_NODE_MODEL_KEYS = {
    "supervisor",
    "schemaInference",
    "parser_agent",
    "refinement_agent",
    "validator_agent",
}

logger = logging.getLogger(__name__)


def parse_node_model_overrides(overrides: List[str] | None) -> Dict[str, str]:
    node_models: Dict[str, str] = {}
    for override in overrides or []:
        if "=" not in override:
            raise ValueError(f"Node model override must use NODE=MODEL format: {override!r}")
        node, model = override.split("=", 1)
        node = node.strip()
        model = model.strip()
        if not node or not model:
            raise ValueError(f"Node model override must include both node and model: {override!r}")
        if node not in SUPPORTED_NODE_MODEL_KEYS:
            supported = ", ".join(sorted(SUPPORTED_NODE_MODEL_KEYS))
            raise ValueError(f"Unsupported node override '{node}'. Supported nodes: {supported}.")
        node_models[node] = model
    return node_models

class RunConfig(BaseModel):
    provider: str = "openai"
    requested_model: str
    resolved_model: str
    node_models: Dict[str, str] = Field(default_factory=dict)
    max_concurrency: int = 2
    graph_recursion_limit: int = DEFAULT_GRAPH_RECURSION_LIMIT
    output_dir: str
    write_markdown_report: bool = True
    write_html_report: bool = True
    write_cleaned_csv: bool = True
    write_run_manifest: bool = True
    sample_strategy: str = "head_tail_random_unique_preview"
    debug: bool = False

class FinalDataSummary(BaseModel):
    trackerInfo: tracker
    confidence: float
    ColNames: Dict[str, List[str]]
    TransformedValues: List[List[JSONScalar]]
    retryCount: int = 0
    validationStatus: Optional[str] = None
    validationMessage: Optional[str] = None
    finalRoute: Optional[str] = None
    error: Optional[str] = None

class DatasetSummary(BaseModel):
    dataset_id: str
    started_at: str
    finished_at: str
    duration_seconds: float = 0.0
    n_success: int
    n_failed: int
    total_retry_count: int = 0
    validation_status_counts: Dict[str, int] = Field(default_factory=dict)
    colData: Dict[str, FinalDataSummary]

class RunOutputFiles(BaseModel):
    cleaned_csv: str
    report_md: str
    report_html: str
    run_manifest: str

class NodeTiming(BaseModel):
    node: str
    timestamp: Optional[str] = None
    duration_to_next_seconds: Optional[float] = None

class ColumnRunSummary(BaseModel):
    status: str
    validation_status: Optional[str] = None
    validation_message: Optional[str] = None
    retry_count: int = 0
    final_route: Optional[str] = None
    confidence: float = 0.0
    output_columns: List[str] = Field(default_factory=list)
    output_shape: Dict[str, int] = Field(default_factory=dict)
    node_count: int = 0
    node_timings: List[NodeTiming] = Field(default_factory=list)
    model_name: Optional[str] = None
    estimated_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    error: Optional[str] = None

class RunManifest(BaseModel):
    schema_version: str = "1.0"
    dataset_id: str
    input_path: str
    started_at: str
    finished_at: str
    duration_seconds: float
    model: str
    config: RunConfig
    outputs: RunOutputFiles
    summary: Dict[str, Any]
    columns: Dict[str, ColumnRunSummary]

@dataclass
class MetaMorphResults:
    dataset_id: str
    model: str
    stamp: str
    report_md_path: str
    report_html_path: str
    cleaned_csv_path: str
    run_manifest_path: str
    report_md_preview: str


def _parse_event(event: str) -> tuple[str, Optional[str]]:
    node, sep, ts = event.partition("@")
    return node, ts if sep and ts else None


def _parse_iso_seconds(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _node_timings(events: List[str]) -> List[NodeTiming]:
    parsed = [_parse_event(event) for event in events]
    timings: List[NodeTiming] = []
    for idx, (node, ts) in enumerate(parsed):
        current_ts = _parse_iso_seconds(ts)
        next_ts = _parse_iso_seconds(parsed[idx + 1][1]) if idx + 1 < len(parsed) else None
        duration = None
        if current_ts and next_ts:
            duration = max((next_ts - current_ts).total_seconds(), 0.0)
        timings.append(
            NodeTiming(
                node=node,
                timestamp=ts,
                duration_to_next_seconds=duration,
            )
        )
    return timings


def _duration_seconds(started_at: str, finished_at: str) -> float:
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    return max((finish - start).total_seconds(), 0.0)


def _column_output_shape(summary: FinalDataSummary) -> Dict[str, int]:
    values = summary.TransformedValues or []
    return {
        "rows": len(values[0]) if values and isinstance(values[0], list) else 0,
        "columns": len(values),
    }


def _build_column_manifest(col: str, summary: FinalDataSummary, model_name: str) -> ColumnRunSummary:
    events = summary.trackerInfo.events_path if summary.trackerInfo else []
    output_columns = summary.ColNames.get(col, []) if summary.ColNames else []
    return ColumnRunSummary(
        status="failed" if summary.error else "success",
        validation_status=summary.validationStatus,
        validation_message=summary.validationMessage,
        retry_count=summary.retryCount,
        final_route=summary.finalRoute,
        confidence=summary.confidence,
        output_columns=output_columns,
        output_shape=_column_output_shape(summary),
        node_count=len(events),
        node_timings=_node_timings(events),
        model_name=model_name,
        error=summary.error,
    )


def build_run_manifest(
    *,
    input_path: Path,
    cleaned_data: DatasetSummary,
    model_name: str,
    config: RunConfig,
    output_files: RunOutputFiles,
) -> RunManifest:
    return RunManifest(
        dataset_id=cleaned_data.dataset_id,
        input_path=str(input_path),
        started_at=cleaned_data.started_at,
        finished_at=cleaned_data.finished_at,
        duration_seconds=cleaned_data.duration_seconds,
        model=model_name,
        config=config,
        outputs=output_files,
        summary={
            "n_success": cleaned_data.n_success,
            "n_failed": cleaned_data.n_failed,
            "n_columns": len(cleaned_data.colData),
            "total_retry_count": cleaned_data.total_retry_count,
            "validation_status_counts": cleaned_data.validation_status_counts,
        },
        columns={
            col: _build_column_manifest(col, summary, model_name)
            for col, summary in cleaned_data.colData.items()
        },
    )


async def colRunner(
    app,
    dataset_id: str,
    col_name: str,
    col_values: list,
    col_sample,
    graph_recursion_limit: int = DEFAULT_GRAPH_RECURSION_LIMIT,
):
    logger.info(
        "Starting column run dataset_id=%s column_name=%s",
        dataset_id,
        col_name,
        extra={"dataset_id": dataset_id, "column_name": col_name},
    )
    init = MetaMorphState(
        input_column_data=InputColumnData(
            column_name=col_name,
            values=col_values),
        ColumnSample=col_sample,
    )
    thread_id = generate_thread_id(dataset_id)
    config = {
        "configurable": {"thread_id": f"{thread_id}:{col_name}"},
        "recursion_limit": graph_recursion_limit,
    }

    try:
        FinalState = await app.ainvoke(init, config=config)
    except GraphRecursionError as e:
        logger.warning(
            "Column run hit graph recursion limit dataset_id=%s column_name=%s",
            dataset_id,
            col_name,
            extra={"dataset_id": dataset_id, "column_name": col_name},
        )
        return FinalDataSummary(
            trackerInfo=tracker(),
            confidence=0.0,
            ColNames={col_name: []},
            TransformedValues=[],
            validationStatus="graph_step_limit",
            validationMessage=str(e),
            finalRoute="GraphRecursionError",
            error=f"GraphRecursionError: {e}",
        )

    try:

        ParsedOut = get_key(FinalState, "parsed_data_output")
        Refined = get_key(FinalState, "refinement_results")
        TrackerInfo = get_key(FinalState, "Node_Col_Tracker")
        ValidatorInfo = get_key(FinalState, "validator_data")


        ColumnNames = get_attr_or_item(ParsedOut, "column_name")
        TransformedData = get_attr_or_item(Refined, "cleaned_values")
        ModelConfidence = get_attr_or_item(Refined, "confidence", 0.0)
        retry_count = get_attr_or_item(ValidatorInfo, "retry_count", 0) if ValidatorInfo else 0
        validation_status = get_attr_or_item(ValidatorInfo, "status", None) if ValidatorInfo else None
        validation_message = get_attr_or_item(ValidatorInfo, "message", None) if ValidatorInfo else None
        final_route = get_attr_or_item(ValidatorInfo, "final_route", None) if ValidatorInfo else None
        validation_passed = get_attr_or_item(ValidatorInfo, "passed", True) if ValidatorInfo else True
        error_message = None if validation_passed else validation_message
        
        #print(f"ColNames: {ColumnNames}\n")
        ColumnNames 

        summary = FinalDataSummary(
            trackerInfo=TrackerInfo,
            confidence=ModelConfidence,
            ColNames=ColumnNames,
            TransformedValues=TransformedData,
            retryCount=retry_count,
            validationStatus=validation_status,
            validationMessage=validation_message,
            finalRoute=final_route,
            error=error_message,
        )
        logger.info(
            "Finished column run dataset_id=%s column_name=%s validation_status=%s retry_count=%s",
            dataset_id,
            col_name,
            summary.validationStatus,
            summary.retryCount,
            extra={
                "dataset_id": dataset_id,
                "column_name": col_name,
                "validation_status": summary.validationStatus,
                "retry_count": summary.retryCount,
            },
        )
        return summary

    except Exception as e:
        logger.exception(
            "Column run summary extraction failed dataset_id=%s column_name=%s",
            dataset_id,
            col_name,
            extra={"dataset_id": dataset_id, "column_name": col_name},
        )
        return FinalDataSummary(
            trackerInfo=tracker(),
            confidence=0.0,
            ColNames={col_name: []}, #double check later
            TransformedValues=[],
            error=f"{type(e).__name__}: {e}",
        )
    
async def run_all(
    graph,
    dataset_id: str,
    columns: Dict[str, list],
    max_concurrency=5,
    graph_recursion_limit: int = DEFAULT_GRAPH_RECURSION_LIMIT,
) -> DatasetSummary:

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
                summary = await colRunner(
                    app,
                    dataset_id,
                    col,
                    val,
                    col_sample,
                    graph_recursion_limit=graph_recursion_limit,
                )
                return col, summary
            except Exception as e:
                return col, e
            
    results = await asyncio.gather(*[_colTask(c, v) for c, v in columns.items()])

    col_summaries: Dict[str, FinalDataSummary] = {}
    n_success = 0
    n_failed = 0
    total_retry_count = 0
    validation_status_counts: Dict[str, int] = {}

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
        total_retry_count += summary.retryCount
        validation_key = summary.validationStatus or "unknown"
        validation_status_counts[validation_key] = validation_status_counts.get(validation_key, 0) + 1
        if summary.error:
            n_failed += 1
        else:
            n_success += 1

    EndTime = datetime.now(timezone.utc).isoformat()
    duration = _duration_seconds(StartTime, EndTime)

    return DatasetSummary(
        dataset_id=dataset_id,
        started_at=StartTime,
        finished_at=EndTime,
        duration_seconds=duration,
        n_success=n_success,
        n_failed=n_failed,
        total_retry_count=total_retry_count,
        validation_status_counts=validation_status_counts,
        colData=col_summaries,
    )


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


def run_MetaMorph_on_csv(
    input_path: str,
    outdir: str | Path = DEFAULT_OUTDIR,
    dataset_id: str | None = None,
    provider: str = "openai",
    llm: str = "gpt-5-nano",
    node_models: Dict[str, str] | None = None,
    max_concurrency: int = 2,    
    debug: bool = False,
) -> MetaMorphResults:
    
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    llm_provider = LLMClientProvider(
        LLMProviderConfig(
            provider=provider,
            default_model=llm,
            node_models=node_models or {},
        )
    )
    model_name = llm_provider.default_model
    config = RunConfig(
        provider=llm_provider.provider,
        requested_model=llm,
        resolved_model=model_name,
        node_models=dict(node_models or {}),
        max_concurrency=max_concurrency,
        graph_recursion_limit=DEFAULT_GRAPH_RECURSION_LIMIT,
        output_dir=str(outdir),
        debug=debug,
    )
    logger.info(
        "Starting MetaMorph run dataset_id=%s model=%s",
        dataset_id or input_path.stem,
        model_name,
        extra={"dataset_id": dataset_id or input_path.stem, "model": model_name},
    )

    graph = StateGraph(MetaMorphState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("schemaInference", schema_inference_node)
    graph.add_node("parser_agent", parser_node)
    graph.add_node("refinement_agent", refinement_agent)
    graph.add_node("validator_agent", validator_node)

    graph.set_entry_point("supervisor")

    # Loading the CSV
    df = pd.read_csv(input_path)
    columns = {col: df[col].tolist() for col in df.columns}

    dataset_id = dataset_id or input_path.stem
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # Running METAMORPH on all columns 
    with use_llm_provider(llm_provider):
        cleaned_data = asyncio.run(
            run_all(
                graph=graph,
                dataset_id=dataset_id,
                columns=columns,
                max_concurrency=max_concurrency,
                graph_recursion_limit=config.graph_recursion_limit,
            )
        )

    report_md = summarizeTransformations(cleaned_data.model_dump())

    report_md_path = outdir / f"MetaMorph_Report_{stamp}.md"
    report_html_path = outdir / f"MetaMorph_Report_{stamp}.html"
    cleaned_csv_path = outdir / f"MetaMorph_Cleaned_{stamp}.csv"
    run_manifest_path = outdir / RUN_MANIFEST_FILENAME

    report_md_path.write_text(report_md, encoding="utf-8")

    html_report = html_template.render(**cleaned_data.model_dump())
    report_html_path.write_text(html_report, encoding="utf-8")

    cleaned_df = BuildFinalDf(df, cleaned_data)
    cleaned_df.to_csv(cleaned_csv_path, index=False)

    output_files = RunOutputFiles(
        cleaned_csv=str(cleaned_csv_path),
        report_md=str(report_md_path),
        report_html=str(report_html_path),
        run_manifest=str(run_manifest_path),
    )
    run_manifest = build_run_manifest(
        input_path=input_path,
        cleaned_data=cleaned_data,
        model_name=model_name,
        config=config,
        output_files=output_files,
    )
    run_manifest_path.write_text(
        json.dumps(run_manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Finished MetaMorph run dataset_id=%s model=%s run_manifest=%s",
        dataset_id,
        model_name,
        run_manifest_path,
        extra={
            "dataset_id": dataset_id,
            "model": model_name,
            "run_manifest": str(run_manifest_path),
        },
    )

    return MetaMorphResults(
        dataset_id=dataset_id,
        model=model_name,
        stamp=stamp,
        report_md_path=str(report_md_path),
        report_html_path=str(report_html_path),
        cleaned_csv_path=str(cleaned_csv_path),
        run_manifest_path=str(run_manifest_path),
        report_md_preview=report_md[:1200],
    )

    



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
        default=DEFAULT_OUTDIR,
        help=f"Output directory for the generated report files. Defaults to {DEFAULT_OUTDIR}/."
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "groq"],
        help="LLM provider to use. Defaults to openai."
    )
    parser.add_argument(
        "--llm", "-l",
        type=str,
        default="gpt-5-nano",
        help="Default LLM model to use"
    )
    parser.add_argument(
        "--node-model",
        action="append",
        default=[],
        metavar="NODE=MODEL",
        help=(
            "Override the model for a graph node. Can be repeated. "
            "Nodes: supervisor, schemaInference, parser_agent, refinement_agent, validator_agent."
        )
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=2,
        help="Maximum number of columns to process concurrently."
    )
    args = parser.parse_args()

    res = run_MetaMorph_on_csv(
        input_path=args.input,
        outdir=args.outdir,
        dataset_id=args.dataset_id,
        provider=args.provider,
        llm=args.llm,
        node_models=parse_node_model_overrides(args.node_model),
        max_concurrency=args.max_concurrency,
    )
