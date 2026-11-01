# ContractGraph AI

Research prototype: **Retrieval-Augmented Cross-Clause Contract Risk Detection Using Dependency Graphs and Evidence Verification**.

## Implemented
- PDF/TXT/Markdown ingestion and validation
- Clause segmentation, keyword aspect tagging and duration extraction
- TF-IDF retrieval baseline
- Typed NetworkX graph: shared-aspect, potential-conflict and explicit-reference edges
- Rule-based review candidates for payment, termination, confidentiality, liability and exception interactions
- Exact-source evidence traceability checks
- Optional Gemini hypothesis generation
- Streamlit UI, JSON export, evaluation utilities, ablation plan and tests

## Important limitations
Heuristic edges and rules are review candidates, not legal conclusions. A duration difference is not automatically a contradiction. Evidence verification establishes source traceability only, not semantic entailment. The demo is synthetic, not a benchmark. Do not claim measured precision, recall, F1 or improvement until a human-reviewed dataset has been evaluated. This is not legal advice.

## Windows PowerShell setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
python -m pytest -q
python -m streamlit run app.py
```

## Optional Gemini
```powershell
$env:GEMINI_API_KEY = Read-Host "Paste your Gemini API key"
$env:GEMINI_MODEL = "gemini-2.5-flash"
```
Do not commit API keys or send confidential contracts to third-party APIs without authorization.

## Structure
`src/contractgraph/` contains ingestion, segmentation, retrieval, graph, risk, evidence, Gemini and evaluation modules. `tests/` contains unit tests. `docs/EXPERIMENT_PROTOCOL.md` defines the planned benchmark. `data/annotations/README.md` defines the human annotation format.
