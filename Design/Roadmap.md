# 🛣️ MetaMorph Development Roadmap

**Transform your metadata. Transform your models.**

This roadmap outlines the staged development of MetaMorph—from an LLM-powered CLI tool to a full-featured API and UI framework for metadata extraction, enrichment, and structuring.

---

## ✅ v1.0 – Core Metadata Transformer (MVP)

**Goal:** 

Transform your metadata. Transform your models.

This roadmap outlines the staged development of MetaMorph, from an LLM-powered CLI tool to a full-featured API and UI framework for metadata extraction, enrichment, and structuring.

---

v1.0 – Core Metadata Transformer (MVP)


**Key Features:**
- [x] DataFrame ingestion and metadata column profiling
- [x] Agent-based parsing pipeline:
  - Metadata analysis agent
  - LLM extraction agent
  - Optional agent (scraper tool)
- [x] Prompt templates 
- [x] Output validation: 
- [x] CLI tool: 


**Modules:**
- `agents/` – orchestrated agent logic and routing
- `tools/` – custom tools for scraping, unit conversion, dictionary lookup
- `prompts/` – LLM prompt logic
- `cli.py` – command-line entry point


---

## 🚀 v2.0 – REST API Deployment

**Goal:** Serve MetaMorph as a backend microservice via REST API.

**Planned Features:**
- [ ] FastAPI or Flask-based service
- [ ] `POST /transform` endpoint for batch or single-column jobs
- [ ] OpenAPI/Swagger docs for easy client integration
- [ ] Dockerfile and deployment instructions
- [ ] Authentication token support (optional)
- [ ] Lightweight job tracking / status endpoint

**Benefits:**
- Integration into ML workflows, notebooks, and Airflow pipelines
- Remote, repeatable transformation of metadata

---

## 🖼️ v3.0 – Web-Based UI for Manual Review

**Goal:** Provide a user-friendly dashboard for exploring, validating, and editing metadata transformations.

**Planned Features:**
- [ ] File upload and preview (CSV/JSON)
- [ ] Auto-parsed metadata preview with side-by-side comparison
- [ ] Manual correction of extracted values
- [ ] Save/export cleaned metadata
- [ ] Audit trail showing original vs transformed entries
- [ ] Prompt customization interface (advanced users)

**Tech Stack Options:**
- Streamlit (fast prototyping)
- React + FastAPI (production-ready)

---

## 🔄 Future Ideas

- [ ] Prompt versioning + tuning presets
- [ ] Ontology-based autocompletion (UMLS, CHEBI, etc.)
- [ ] Offline mode with open-weight LLMs
- [ ] Integration with MLflow or AutoML systems
- [ ] Plugin system for domain-specific extensions

---

## 📦 Suggested Directory Layout

