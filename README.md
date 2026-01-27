# MetaMorph 🦋 — LLM Agent Framework for Metadata Transformation

**Transform your metadata. Transform your models.**

MetaMorph is an open-source **LLM-powered agent system** for **metadata extraction, normalization, and structuring**. It converts messy, unstructured, or heterogeneous dataset columns into **machine-readable features** using an **agentic workflow** (multi-step LLM pipeline) with **provenance tracking** and optional **HTML reporting**, designed for reliable downstream analytics, ML, and RAG-ready data prep.

> **Keywords:** LLM agents, agentic workflows, multi-agent systems, LLM data extraction, metadata normalization, schema inference, structured outputs, LangGraph, LangChain, RAG data preparation, dataset cleaning, feature engineering, unstructured-to-structured, data pipelines, AI data wrangling.

---

## Why MetaMorph?

High-quality metadata is the backbone of meaningful machine learning. But in the real world, metadata often lives in:
- free-text columns (`notes`, `comments`, `sample description`)
- inconsistent formats (dates, IDs, units)
- messy categorical labels (typos, aliases, abbreviations)
- semi-structured strings (`WT1: 0.4 | WT2: 0.6`)
- undocumented conventions and hidden context

This makes models brittle, reduces reproducibility, and slows down iteration.

**MetaMorph solves this by:**
- Parsing free-text and semi-structured metadata with LLMs.
- Standardizing units, formats, and categories.
- Extracting domain-relevant entities and numeric values.
- Producing schema-aligned, machine-readable columns for ML pipelines.
- Recording uncertainty and transformation decisions with traceability.

---

## What makes MetaMorph different?

### Agentic workflow (LLM Agent System)
MetaMorph is not “one prompt.” It’s an **LLM agent pipeline** (supervisor + specialized nodes) designed for robust transformation:
- parsing
- schema/type inference
- refinement / normalization
- validation
- error handling & retries

This structure supports **repeatable, testable LLM behavior** and safer scaling across columns and datasets.

### Column-level provenance (audit trail)
Each processed column can maintain a tracker containing:
- **events_path** — which agents/nodes touched the column (optionally timestamped)
- **node_path** — summaries/reasons from each node, per column
- uncertainty markers + error messages

So you can answer: *“What changed, when, and why?”*

### Human-readable HTML reports 🐛→🦋
MetaMorph can generate an HTML report to review results quickly:
- success/failure per column
- confidence + output shape
- mapped output columns
- node summaries (with timestamps)
- error blocks for debugging

---

## Features (v1.1)

- **Plug-and-play metadata transformation** → structured outputs ready for ML  
- **LLM-powered extraction + normalization** (units, dates, entities, categories)  
- **Agent system architecture** for reliability and modularity  
- **Structured outputs + validation** friendly design patterns  
- **Domain-agnostic core** with hooks for domain constraints/ontologies  
- **Provenance + reporting** for transparency and debugging  

---

## Example use cases

- **Environmental / exposure science:** parse lab notes + units into consistent exposure variables for prediction models  
- **Clinical / biomedical:** normalize clinical metadata fields for patient stratification and risk models  
- **Drug discovery / QSAR:** structure assay conditions, doses, readouts to improve bioactivity prediction  
- **Materials informatics:** extract synthesis parameters into consistent numeric/categorical columns  
- **RAG & analytics prep:** convert unstructured columns into structured fields for indexing and retrieval  

---

## Installation (Pixi)

This project uses **Pixi** for environment management.

```bash
git clone https://github.com/Michael000777/MetaMorph.git
cd MetaMorph
pixi install

pixi run python metamorph/mainConcurrent.py --help

```

## 🏁 Quick Start
Example usage:
```bash
pixi run python metamorph/mainConcurrent.py --input examples/data1.csv -d testRob -o examples/ -l gpt-5-mini

```
### Common arguments
- --input : path to your dataset (CSV)
- -d / --dataset-id : identifier used in outputs and reporting
- -o / --outdir : output directory (created if missing)
- -l / --llm : model selection (e.g., gpt-5-mini). Currently GPT moels only

## MCP (Model Context Protocol) Support

MetaMorph can be exposed as a **local MCP server**, allowing any MCP-compatible client (IDE agents, desktop apps, or other LLM orchestrators) to invoke MetaMorph as a structured tool.

This enables MetaMorph to be used **programmatically by external agents**, without deploying a web service.

### Why MCP?
- Standardized tool interface for LLMs (no custom APIs)
- Local execution over **stdio** (no ports, no HTTP)
- Explicit, minimal surface area
- Same transformation pipeline as the CLI

---

## Running MetaMorph as an MCP Server

Start the MCP server locally:

```bash
pixi run python -m metamorph.mcp_server
```

The server runs over **stdio** and waits for tool invocations from an MCP client.

---
## Exposed MCP Tools

The MCP server intentionally exposes a **minimal API**.

### `metamorph_run`

Runs the full MetaMorph transformation pipeline on a CSV dataset.

**Inputs**
- `input_path` — path to CSV file  
- `outdir` — output directory  
- `dataset_id` (optional)  
- `llm` (optional)  
- `max_concurrency` (optional)  

**Outputs**
- path to cleaned CSV  
- Markdown + HTML transformation reports  
- short report preview for client inspection  

### `metamorph_info`

Returns basic capability metadata about the MetaMorph server.

**Outputs**
- tool name and purpose  
- supported input types  
- generated output artifacts

---

## Outputs
MetaMorph can generate:
- structured values (normalized units, parsed categories, extracted fields)
- mapped feature columns (one-to-many expansion when needed)
- per-column summaries (confidence, errors, notes)
- provenance tracking (events_path, node_path)
- optional HTML report for debugging and review


---

## Example: one column, end-to-end

### Input

```text
height
"5 ft 10 in"
"170 cm"
"6'2\""
"1.75 m"
"unknown"
```

### Output

```text
height_cm
177.8
170.0
188.0
175.0
null
```
---

## Roadmap: v1.2 (planned)

Version 1.2 focuses on extensibility and alignment with production-ready pipelines.

### Backend model abstraction
- Decouple agent logic from LLM providers.
- Support local models and multiple backends per stage.
- Enable cost-aware routing while preserving structured-output contracts.

### Structured JSON outputs
- Convert complex free-text metadata into explicit JSON or dictionary representations.
- Support richer validation, downstream modeling, and RAG-style workflows.
