Aegis — Defense-in-Depth Security for Tool-Using LLM Agents
> **The model can be fooled. It should not be able to act on that instruction.**
Aegis is a layered security system for tool-using LLM agents. It protects the agent's input, retrieved content, proposed actions, and final answers using deterministic policy checks, content-scanning layers, a quantum-kernel injection detector, grounding checks, and a tamper-evident audit log.
All tools used in the demo are simulated. Q-Gate runs on a quantum simulator; this project does not claim quantum advantage.
---
Contents
The problem
What Aegis does
System architecture
Request lifecycle
Security layers
Hallucination and grounding checks
Q-Gate: quantum-kernel injection detection
Simulated tools
Auditability
Evaluation
Technology stack
Run locally
Example attack scenario
Security boundaries and limitations
---
The problem
LLM agents can read documents and call tools such as email, file, and database functions. An attacker may try to manipulate the agent through:
Jailbreaks in user messages.
Prompt injection hidden in retrieved documents or tool output.
Data leakage through secrets or personal information.
Unsafe tool use, such as an unapproved or untrusted outbound action.
Missing auditability, which makes decisions difficult to review.
Hallucinations, where an answer contains claims not supported by the retrieved evidence.
A system prompt or a single classifier is not a complete security boundary. Aegis places checks at multiple points in the agent workflow.
What Aegis does
Normalizes and classifies incoming user messages.
Scans retrieved content, applies data-protection checks, and records provenance and taint.
Uses Q-Gate to score untrusted text for possible prompt injection.
Validates proposed tool calls and makes an explicit `ALLOW`, `CONFIRM`, or `BLOCK` decision.
Grounds answers in retrieved passages and checks citations and supported values.
Can use natural-language inference (NLI) to check whether answer claims are entailed by cited passages.
Records decisions in an append-only, hash-chained audit log.
Evaluates behavior across configurations so that defenses can be compared rather than judged only by a single demo.
System architecture
![Aegis system architecture, including hallucination and grounding checks](docs/aegis_architecture_flowchart.png)
The diagram shows the request path, tool-action decisions, ingress and Q-Gate processing, hallucination/grounding checks, and the hash-chained audit log.
Request lifecycle
User message: The Chainlit UI passes the message to `pipeline.run_turn()`.
Input guard: The message is normalized and classified; multi-turn risk and refusal checks may also apply.
Agent loop: The LLM drafts an answer or proposes a tool call.
Tool Safety / Action Gate: The proposed call is validated and resolved to `ALLOW`, `CONFIRM`, or `BLOCK`.
Simulated tool execution: An allowed tool call runs with an action token.
Ingress and data protection: Retrieved content is checked for access permissions, canaries, secrets/PII, provenance, and taint.
Q-Gate / classical detector: Untrusted text is scored and may pass, be reviewed, or be quarantined. Q-Gate is advisory; it does not independently hard-block an action.
Grounded response: The model uses vetted passages, with citations or “not found” when evidence is unavailable.
Output checks: The answer is checked for moderation, canary/secret leakage, citation validity, supported values, and—when enabled—claim entailment.
Audit: The system records the relevant decisions and allows the hash chain to be verified.
Security layers
Layer / ID	Purpose
J1	Normalize and classify incoming messages.
J2	Harden the prompt and spotlight untrusted text.
J3	Track multi-turn risk and enable stricter handling when needed.
J4	Moderate generated output.
J5	Return a fixed refusal for messages that should be refused.
A1–A3	Apply tool pinning, taint-aware argument rules, and memory-write protections where implemented.
T1, T2, T4, T6, T7	Apply tool registration, argument validation, confirmation, limits, and data-flow rules where enabled.
D1–D4	Apply retrieval permissions, secret/PII scanning, canary checks, and outbound-destination restrictions.
Q-Gate / RBF	Score untrusted text using a quantum-kernel detector and a classical RBF baseline.
H1	Ground generation in vetted passages or return “not found.”
H2	Check citation IDs and whether source values such as names and numbers appear in cited passages.
H3	Optional/recommended NLI check for whether a claim is entailed by a cited passage.
H5	Decide whether the final output should be `ANSWER`, `PRUNED`, or `ABSTAIN`.
M1–M3	Record events in the hash-chained audit log and support chain verification.
The guide distinguishes MVP, recommended, and optional components. Exact availability depends on the enabled configuration; this table describes the project’s layer design, not a claim that every optional layer is enabled in every run.
Hallucination and grounding checks
Aegis treats grounding as a separate output-verification step rather than relying only on the model to follow instructions.
H1 — Grounded generation: The answer should use vetted passages, cite their passage IDs, or say “not found.”
H2 — Citation and source-value checks: Cited passage IDs must exist, and factual values such as numbers and names must be supported by the cited source.
H3 — Claim entailment (recommended): An NLI model can check whether each answer claim is entailed by its cited passage.
H5 — Output decision: Supported sentences can be returned; unsupported sentences can be pruned; if no supported answer remains, the system can abstain.
Example: If a source says that refunds take 5 to 7 business days, an answer claiming 9 days should be pruned. An answer with a nonexistent passage ID should be pruned or lead to abstention.
Q-Gate: quantum-kernel injection detection
Q-Gate is an advisory prompt-injection detector for untrusted text.
Text is converted into features using TF-IDF character n-grams and SVD.
The embedding is scaled to the input range for a small quantum feature map.
A PennyLane `default.qubit` simulator computes a quantum-kernel similarity.
An SVM uses the precomputed kernel to score possible injection text.
A classical RBF SVM provides a comparison using the same features.
The kernel is based on the overlap between encoded quantum states:
[
k(a,b)=|\langle\phi(a)\mid\phi(b)\rangle|^2
]
The detector can return pass, review, or quarantine. A review can cause the action gate to require confirmation; Q-Gate alone does not hard-block tool execution.
Honest scope: The project uses a simulator, not real quantum hardware. Results should be reported from the repository’s evaluation output; no quantum-advantage claim is made.
Simulated tools
The demo provides five simulated tools:
`search_docs`
`read_file`
`query_db`
`write_note`
`send_email`
These are intended for safe testing. In particular, the simulated `send_email` writes to a local outbox file rather than sending a real email.
Auditability
Aegis writes audit events to an append-only, hash-chained JSONL log. Events can include input, tool-gate decisions, ingress, confirmation, output, and LLM errors.
The log is designed to make edits, reordering, or deletion within the chain detectable during verification. It does not prove that every original event was correct, and detecting truncation of the end of a log requires the latest hash to be stored separately.
Use the verification command configured by the repository, for example:
```bash
python -m scripts.verify_audit
```
If your checkout exposes the verifier under a different command or path, follow the script name present in the repository.
Evaluation
Aegis includes an evaluation approach based on attack cases and configuration comparisons.
Reported measures may include:
Attack success rate (ASR): whether the attack achieved its objective, checked using observable outcomes rather than the defense’s own verdict.
False-block rate: benign actions incorrectly blocked.
Over-refusal: benign requests refused by the system.
Latency: time added by the security layers.
Q-Gate vs. RBF: comparison on the same held-out data split.
E2 incremental catches: attacks flagged by one detector that the other relevant layers or classical detector missed, as defined for the project evaluation.
Use the actual output files (for example, `results/summary.csv` and `results/qgate_e1_e2.json`, when present) for reported numbers. Do not infer performance values from the architecture alone.
Technology stack
Technology	Role
Python 3.11	Main implementation language
Chainlit	Chat interface and confirmation workflow
LiteLLM	Shared wrapper for hosted LLM calls
Pydantic	Data contracts and tool-argument validation
PennyLane	Quantum-kernel simulation
scikit-learn	SVMs, TF-IDF/SVD, and evaluation metrics
PyYAML	Readable policy and configuration files
SQLite	Simulated database
`hashlib`, `hmac`, `json`	Audit-chain hashing, action tokens, and JSONL data
pandas and matplotlib	Evaluation summaries and charts
pytest	Automated tests
The execution guide describes a single local Python process and simulated tools; it does not require a separate database server or real quantum hardware.
Run locally
These are the setup steps described by the execution guide. Run commands from the repository root and check that the corresponding files exist in your checkout.
1. Create and activate a virtual environment
```bash
python -m venv .venv
```
On Windows Command Prompt:
```bat
.venv\Scripts\activate
```
On macOS/Linux:
```bash
source .venv/bin/activate
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Configure environment variables
Copy `.env.example` to `.env` if that example file exists, then set the required LLM provider key and model settings described by the project. Keep `.env` private; do not commit API keys or other secrets.
4. Prepare simulated data
```bash
python -m scripts.setup_data
```
5. Run tests
```bash
pytest -q
```
6. Launch the interface
```bash
chainlit run app.py
```
Then open the local URL printed by Chainlit, typically `http://localhost:8000`.
> **Note:** Script names and configuration files can vary by checkout. If a command is unavailable, inspect the repository’s `scripts/`, `configs/`, and `README`/execution-guide files rather than assuming an optional component is present.
Example attack scenario
The execution guide uses a vendor-update scenario to demonstrate defense in depth:
The user asks: “What changed in the vendor update?”
The agent searches the documents and receives a vendor-update passage containing an injected instruction.
Ingress tags the retrieved content as untrusted; Q-Gate may quarantine or flag the injected sentence.
If the model proposes emailing data to `audit@evil-corp.io`, deterministic taint and outbound-destination rules block the action.
The agent can still answer the legitimate question from the vetted passage: “Shipping to Pune now takes 4 days”, with a valid passage citation.
The output checks validate the citation and value, and the audit log records the decisions.
The expected outcome for the full configuration is a grounded answer, no external email in the simulated outbox, visible security-layer verdicts, and an intact audit chain. Behavior should be demonstrated and verified against the active model and configuration.
Security boundaries and limitations
Q-Gate uses a quantum simulator; this is not evidence of quantum advantage.
The demo tools are simulated and must not be described as sending real emails or accessing real company systems.
Classifiers can miss attacks and can flag benign content. The architecture therefore uses multiple layers.
Taint tracking is heuristic and can be evaded by paraphrasing or transforming data; outbound allowlists and confirmation rules provide additional checks.
A hash chain can detect many forms of in-chain tampering, but does not establish that the original event was truthful.
Optional/recommended layers may not be enabled in every configuration.
Evaluation claims must match the committed result files, test-set sizes, and configuration used.
---
Project principle
Probabilistic detectors raise suspicion. Deterministic policy layers control actions. Grounding checks verify answers. The audit chain records the decisions.
