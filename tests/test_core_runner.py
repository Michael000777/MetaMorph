import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from metamorph import core
from metamorph import mainConcurrent
from metamorph import mcp_server
from utils.MetaMorphState import tracker


class CoreRunnerTests(unittest.TestCase):
    def test_parse_node_model_overrides(self):
        self.assertEqual(
            core.parse_node_model_overrides(
                ["schemaInference=schema-model", "parser_agent=parser-model"]
            ),
            {
                "schemaInference": "schema-model",
                "parser_agent": "parser-model",
            },
        )

        with self.assertRaises(ValueError):
            core.parse_node_model_overrides(["unknown=model"])

    def test_runner_uses_parameters_and_default_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "sample_metadata.csv"
            pd.DataFrame({"height": ["5 ft 10 in", "170 cm"]}).to_csv(input_path, index=False)

            captured = {}

            async def fake_run_all(graph, dataset_id, columns, max_concurrency, graph_recursion_limit):
                captured["dataset_id"] = dataset_id
                captured["columns"] = columns
                captured["max_concurrency"] = max_concurrency
                captured["graph_recursion_limit"] = graph_recursion_limit
                return core.DatasetSummary(
                    dataset_id=dataset_id,
                    started_at="2026-05-27T00:00:00+00:00",
                    finished_at="2026-05-27T00:00:01+00:00",
                    duration_seconds=1.0,
                    n_success=1,
                    n_failed=0,
                    total_retry_count=0,
                    validation_status_counts={"pass": 1},
                    colData={
                        "height": core.FinalDataSummary(
                            trackerInfo=tracker(),
                            confidence=0.99,
                            ColNames={"height": ["height_cm"]},
                            TransformedValues=[[177.8, 170.0]],
                        )
                    },
                )

            old_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                with patch.object(core, "run_all", side_effect=fake_run_all):
                    result = core.run_MetaMorph_on_csv(
                        input_path=input_path,
                        llm="test-model",
                        max_concurrency=7,
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(result.dataset_id, "sample_metadata")
            self.assertEqual(result.model, "test-model")
            self.assertEqual(captured["dataset_id"], "sample_metadata")
            self.assertEqual(captured["columns"], {"height": ["5 ft 10 in", "170 cm"]})
            self.assertEqual(captured["max_concurrency"], 7)
            self.assertEqual(captured["graph_recursion_limit"], core.DEFAULT_GRAPH_RECURSION_LIMIT)
            self.assertTrue(Path(result.cleaned_csv_path).exists())
            self.assertTrue(Path(result.report_md_path).exists())
            self.assertTrue(Path(result.report_html_path).exists())
            self.assertTrue(Path(result.run_manifest_path).exists())
            self.assertEqual(Path(result.cleaned_csv_path).parent.name, core.DEFAULT_OUTDIR)

    def test_runner_honors_explicit_dataset_id_and_outdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.csv"
            outdir = tmp_path / "custom_outputs"
            pd.DataFrame({"age": ["10", "11"]}).to_csv(input_path, index=False)

            async def fake_run_all(graph, dataset_id, columns, max_concurrency, graph_recursion_limit):
                return core.DatasetSummary(
                    dataset_id=dataset_id,
                    started_at="2026-05-27T00:00:00+00:00",
                    finished_at="2026-05-27T00:00:01+00:00",
                    duration_seconds=1.0,
                    n_success=1,
                    n_failed=0,
                    colData={
                        "age": core.FinalDataSummary(
                            trackerInfo=tracker(),
                            confidence=1.0,
                            ColNames={"age": ["age_years"]},
                            TransformedValues=[[10, 11]],
                        )
                    },
                )

            with patch.object(core, "run_all", side_effect=fake_run_all):
                result = core.run_MetaMorph_on_csv(
                    input_path=input_path,
                    outdir=outdir,
                    dataset_id="explicit-dataset",
                )

            self.assertEqual(result.dataset_id, "explicit-dataset")
            self.assertEqual(Path(result.cleaned_csv_path).parent, outdir.resolve())
            self.assertTrue(outdir.exists())

    def test_runner_writes_run_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.csv"
            outdir = tmp_path / "outputs"
            pd.DataFrame({"age": ["10", "11"]}).to_csv(input_path, index=False)

            async def fake_run_all(graph, dataset_id, columns, max_concurrency, graph_recursion_limit):
                return core.DatasetSummary(
                    dataset_id=dataset_id,
                    started_at="2026-05-27T00:00:00+00:00",
                    finished_at="2026-05-27T00:00:02+00:00",
                    duration_seconds=2.0,
                    n_success=1,
                    n_failed=0,
                    total_retry_count=1,
                    validation_status_counts={"pass": 1},
                    colData={
                        "age": core.FinalDataSummary(
                            trackerInfo=tracker(events_path=["ValidatorNode@2026-05-27T00:00:01+00:00"]),
                            confidence=0.88,
                            ColNames={"age": ["age_years"]},
                            TransformedValues=[[10, 11]],
                            retryCount=1,
                            validationStatus="pass",
                            validationMessage="Output is row-aligned.",
                            finalRoute="__end__",
                        )
                    },
                )

            with patch.object(core, "run_all", side_effect=fake_run_all):
                result = core.run_MetaMorph_on_csv(
                    input_path=input_path,
                    outdir=outdir,
                    dataset_id="dataset-a",
                    provider="groq",
                    llm="test-model",
                    node_models={"parser_agent": "parser-model"},
                    max_concurrency=3,
                )

            manifest_path = Path(result.run_manifest_path)
            self.assertEqual(manifest_path.name, core.RUN_MANIFEST_FILENAME)
            self.assertTrue(manifest_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["dataset_id"], "dataset-a")
            self.assertEqual(manifest["input_path"], str(input_path.resolve()))
            self.assertEqual(manifest["model"], "test-model")
            self.assertEqual(manifest["config"]["provider"], "groq")
            self.assertEqual(manifest["config"]["requested_model"], "test-model")
            self.assertEqual(manifest["config"]["resolved_model"], "test-model")
            self.assertEqual(manifest["config"]["node_models"], {"parser_agent": "parser-model"})
            self.assertEqual(manifest["config"]["max_concurrency"], 3)
            self.assertEqual(manifest["summary"]["total_retry_count"], 1)
            self.assertEqual(manifest["columns"]["age"]["validation_status"], "pass")
            self.assertEqual(manifest["columns"]["age"]["retry_count"], 1)
            self.assertEqual(manifest["columns"]["age"]["output_shape"], {"rows": 2, "columns": 1})
            self.assertIn("run_manifest", manifest["outputs"])


class CliTests(unittest.TestCase):
    def test_concurrent_cli_help(self):
        repo_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "metamorph/mainConcurrent.py", "--help"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--outdir", completed.stdout)
        self.assertIn("Defaults to Reports/", completed.stdout)

    def test_concurrent_cli_delegates_to_core_runner(self):
        with patch.object(mainConcurrent, "run_MetaMorph_on_csv") as run_csv:
            exit_code = mainConcurrent.main(
                [
                    "--input",
                    "examples/data1.csv",
                    "--dataset-id",
                    "dataset-a",
                    "--outdir",
                    "outputs",
                    "--provider",
                    "groq",
                    "--llm",
                    "test-model",
                    "--node-model",
                    "parser_agent=parser-model",
                    "--max-concurrency",
                    "4",
                ]
            )

        self.assertEqual(exit_code, 0)
        run_csv.assert_called_once_with(
            input_path="examples/data1.csv",
            outdir="outputs",
            dataset_id="dataset-a",
            provider="groq",
            llm="test-model",
            node_models={"parser_agent": "parser-model"},
            max_concurrency=4,
        )


class McpServerTests(unittest.TestCase):
    def test_mcp_run_delegates_to_core_runner_without_cli_globals(self):
        fake_result = SimpleNamespace(
            dataset_id="dataset-a",
            model="fake-model",
            stamp="20260527-000000",
            cleaned_csv_path="/tmp/cleaned.csv",
            report_md_path="/tmp/report.md",
            report_html_path="/tmp/report.html",
            run_manifest_path="/tmp/run.json",
            report_md_preview="preview",
        )

        with patch.object(mcp_server, "run_MetaMorph_on_csv", return_value=fake_result) as run_csv:
            result = mcp_server.metamorph_run(
                input_path="input.csv",
                outdir="outputs",
                dataset_id=None,
                provider="groq",
                llm="test-model",
                node_models={"parser_agent": "parser-model"},
                max_concurrency=3,
            )

        run_csv.assert_called_once_with(
            input_path="input.csv",
            outdir="outputs",
            dataset_id=None,
            provider="groq",
            llm="test-model",
            node_models={"parser_agent": "parser-model"},
            max_concurrency=3,
        )
        self.assertEqual(result["dataset_id"], "dataset-a")
        self.assertEqual(result["model"], "fake-model")
        self.assertEqual(result["outputs"]["cleaned_csv"], "/tmp/cleaned.csv")
        self.assertEqual(result["outputs"]["report_md"], "/tmp/report.md")
        self.assertEqual(result["outputs"]["report_html"], "/tmp/report.html")
        self.assertEqual(result["outputs"]["run_manifest"], "/tmp/run.json")


if __name__ == "__main__":
    unittest.main()
