<section class="ctx-home-hero">
  <div class="ctx-home-hero__eyebrow">CORTEX Persist</div>
  <h1>AI memory with proof, not vibes.</h1>
  <p class="ctx-home-hero__lede">
    CORTEX gives autonomous systems a trust substrate: deterministic guards,
    cryptographic audit trails, tenant-aware memory, and verification boundaries
    between generated output and persisted state.
  </p>
  <div class="ctx-home-actions">
    <a href="quickstart.md" class="md-button md-button--primary">Start in 5 minutes</a>
    <a href="architecture.md" class="md-button">Read the architecture</a>
    <a href="https://github.com/borjamoskv/Cortex-Persist" class="md-button">GitHub</a>
  </div>
  <div class="ctx-home-metrics">
    <div class="ctx-home-metric">
      <span class="ctx-home-metric__value">Hash-chained</span>
      <span class="ctx-home-metric__label">Every write is auditable</span>
    </div>
    <div class="ctx-home-metric">
      <span class="ctx-home-metric__value">Local-first</span>
      <span class="ctx-home-metric__label">SQLite by default, cloud optional</span>
    </div>
    <div class="ctx-home-metric">
      <span class="ctx-home-metric__value">Multi-tenant</span>
      <span class="ctx-home-metric__label">API, storage, and read paths stay scoped</span>
    </div>
  </div>
</section>

<div class="ctx-home-terminal">
  <div class="ctx-home-terminal__bar">
    <span></span><span></span><span></span>
    <strong>sovereign-memory.demo</strong>
  </div>

```bash
pip install cortex-persist
cortex init
cortex store my-agent "Use OAuth2 PKCE for auth" --type decision
cortex verify 1
# VERIFIED — hash continuity intact, ledger auditable
```
</div>

## Why teams use CORTEX

<div class="ctx-home-grid">
  <article class="ctx-home-card">
    <h3>Deterministic admission</h3>
    <p>Generated output stays a proposal until guards, schemas, and typed interfaces allow it through.</p>
  </article>
  <article class="ctx-home-card">
    <h3>Cryptographic continuity</h3>
    <p>Facts and transactions are linked through tamper-evident ledger semantics instead of best-effort logs.</p>
  </article>
  <article class="ctx-home-card">
    <h3>Tenant-aware memory</h3>
    <p>Public read and write paths are scoped by default so agent memory does not leak across customers.</p>
  </article>
  <article class="ctx-home-card">
    <h3>Consensus and verification</h3>
    <p>Multi-agent voting, audit trails, and replayable state make decisions inspectable after the fact.</p>
  </article>
  <article class="ctx-home-card">
    <h3>Compliance posture</h3>
    <p>Built for systems that need traceability, retention boundaries, and evidence for high-risk AI operations.</p>
  </article>
  <article class="ctx-home-card">
    <h3>Failure locality</h3>
    <p>Invalid state should be rejectable and abortable before it contaminates durable system memory.</p>
  </article>
</div>

## The write path contract

<div class="ctx-home-flow">
  <div class="ctx-home-flow__step">
    <span>1</span>
    <strong>Proposal</strong>
    <p>Agent produces a candidate fact, action, or state mutation.</p>
  </div>
  <div class="ctx-home-flow__arrow">→</div>
  <div class="ctx-home-flow__step">
    <span>2</span>
    <strong>Guards</strong>
    <p>Admission, contradiction, injection, and dependency checks run before persistence.</p>
  </div>
  <div class="ctx-home-flow__arrow">→</div>
  <div class="ctx-home-flow__step">
    <span>3</span>
    <strong>Ledger + audit</strong>
    <p>The accepted mutation is logged with continuity and traceability.</p>
  </div>
  <div class="ctx-home-flow__arrow">→</div>
  <div class="ctx-home-flow__step">
    <span>4</span>
    <strong>Recall</strong>
    <p>Search, memory, and downstream agents consume verifiable state instead of raw conjecture.</p>
  </div>
</div>

## Designed for real operator pressure

<div class="ctx-home-split">
  <div class="ctx-home-panel">
    <h3>What breaks without this layer</h3>
    <ul>
      <li>Agents persist incorrect state because the model sounded confident.</li>
      <li>Compliance and security teams cannot reconstruct who wrote what and why.</li>
      <li>Cross-tenant memory or undeclared side effects turn into invisible operational risk.</li>
      <li>Incident review becomes guesswork because logs and state diverge.</li>
    </ul>
  </div>
  <div class="ctx-home-panel ctx-home-panel--accent">
    <h3>What CORTEX changes</h3>
    <ul>
      <li>Persisted facts pass deterministic validation boundaries before durable write.</li>
      <li>Ledger continuity can be verified instead of assumed.</li>
      <li>Memory remains useful for agents without becoming a silent source of untrusted truth.</li>
      <li>Teams get a local-first foundation that can scale to cloud when needed.</li>
    </ul>
  </div>
</div>

## Start where you are

<div class="ctx-home-links">
  <a class="ctx-home-link" href="quickstart.md">
    <strong>Quickstart</strong>
    <span>Install, init, store, verify.</span>
  </a>
  <a class="ctx-home-link" href="installation.md">
    <strong>Installation</strong>
    <span>Extras, Python versions, environment setup.</span>
  </a>
  <a class="ctx-home-link" href="architecture.md">
    <strong>Architecture</strong>
    <span>Core topology, trust surfaces, module map.</span>
  </a>
  <a class="ctx-home-link" href="api.md">
    <strong>REST API</strong>
    <span>Read and write paths for memory-backed systems.</span>
  </a>
  <a class="ctx-home-link" href="compliance.md">
    <strong>Compliance</strong>
    <span>Traceability and control posture for regulated AI use cases.</span>
  </a>
  <a class="ctx-home-link" href="developer-guide.md">
    <strong>Developer Guide</strong>
    <span>Repo conventions, extension points, and contribution flow.</span>
  </a>
</div>

---

*by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
