from mcp.server.fastmcp import FastMCP
from .core import run_MetaMorph_on_csv
import sys

mcp = FastMCP("MetaMorph")

@mcp.tool()
def metamorph_run(
    input_path: str,
    outdir: str,
    dataset_id: str | None = None,
    llm: str = "gpt-5-nano",
    max_concurrency: int = 2,
) -> dict:
    """
    Run MetaMorph on a CSV file and write outputs to outdir.
    Returns paths to cleaned CSV + reports, plus a short markdown preview.
    """
    res = run_MetaMorph_on_csv(
        input_path=input_path,
        outdir=outdir,
        dataset_id=dataset_id,
        llm=llm,
        max_concurrency=max_concurrency,
    )
    return {
        "dataset_id": res.dataset_id,
        "model": res.model,
        "stamp": res.stamp,
        "outputs": {
            "cleaned_csv": res.cleaned_csv_path,
            "report_md": res.report_md_path,
            "report_html": res.report_html_path,
        },
        "report_md_preview": res.report_md_preview,
    }

@mcp.tool()
def metamorph_info() -> dict:
    """Basic server/capabilities info for MetaMorph."""
    return {
        "name": "MetaMorph",
        "purpose": "Transform messy CSV metadata into clean structured outputs + reports",
        "inputs": ["CSV path"],
        "outputs": ["cleaned CSV", "markdown report", "html report"],
    }

if __name__ == "__main__":
    print("MetaMorph MCP server starting…", file=sys.stderr)
    mcp.run()