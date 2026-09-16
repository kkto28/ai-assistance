# Modular Mac Assistance Project Plan

## 1. Project outcome

Build a macOS-only, modular personal-assistance platform for document management and workflow automation. The system must be extensible rather than a single application with hard-coded features: agents, schedulers, tools, interfaces, configuration, storage, and LLM providers should be replaceable modules connected through typed contracts.

The first release will support local files, iCloud Drive, and Google Drive; document processing; scheduled and event-driven workflows; and configurable LLM providers including Claude. Development will be incremental and test-driven so every slice is useful, testable, and reversible.

The repository is currently an empty Git repository with no source files, dependencies, commits, or application configuration. The plan therefore starts with project scaffolding and contracts before adding integrations.

## 2. Product principles

- **Modular:** each capability is a module with a narrow interface and explicit dependencies.
- **Provider-neutral:** LLMs, storage providers, schedulers, and UI surfaces can be changed without rewriting workflow logic.
- **Incremental:** deliver vertical slices that work end-to-end before expanding breadth.
- **Test-driven:** write failing tests for behavior and contracts before implementation; preserve fixtures and regression tests.
- **Safe by default:** preview changes, preserve originals, require approval for destructive actions, and make retries idempotent.
- **Configurable:** use versioned configuration for providers, schedules, permissions, tools, agents, and policies; avoid secrets in repository files.
- **Observable:** every workflow and agent run has structured status, logs, diagnostics, costs/usage where available, and recoverable failure state.
- **Offline-capable:** local indexing, search, deterministic tools, and previously configured workflows work without cloud access where possible.

## 3. First-release goals

### Must have

1. Index and search user-approved local folders and iCloud Drive locations incrementally.
2. Connect to Google Drive with OAuth, scoped access, incremental change detection, and explicit sync/caching rules.
3. Process Markdown/plain text, Office documents, and PDFs with explicit unsupported/degraded states.
4. Run document operations such as summarize, transform, extract, classify, suggest names/tags, and export.
5. Use configurable LLM providers, including Claude, through a common provider interface.
6. Run reusable workflows manually, from Finder/Shortcuts, from the CLI, and on a schedule.
7. Coordinate specialized agents that use approved tools to complete bounded workflow tasks.
8. Provide a menu-bar/desktop interface and a CLI over the same application services.
9. Store configuration, workflow definitions, credentials references, run history, and audit events safely and locally.
10. Use TDD, contract tests, integration fixtures, and CI from the first implementation slice.

### Explicitly not in the first release

- Email and calendar automation.
- Broad SaaS integrations beyond Google Drive.
- Unbounded autonomous agents or agents that can invent and install tools.
- Cross-platform support.
- Multi-user accounts or a hosted orchestration backend.
- Destructive file operations without preview and approval.
- Full-fidelity Office/PDF round-trip editing unless required by a validated use case.

## 4. Modular architecture

### 4.1 Core modules

```text
Sources/
├── AssistantDomain/       # Typed IDs, documents, artifacts, policies, errors
├── AssistantConfig/       # Versioned config, profiles, validation, migrations
├── AssistantStorage/      # Local database, secrets references, run history
├── AssistantDocuments/    # File catalog, extraction, indexing, search
├── AssistantTools/        # Tool protocol, registry, permissions, adapters
├── AssistantAgents/       # Agent definitions, planning, execution, guardrails
├── AssistantWorkflows/    # Workflow schema, validation, execution, approvals
├── AssistantScheduler/    # Manual, time-based, event-based triggers
├── AssistantLLM/          # Provider protocol and Claude/other adapters
├── AssistantConnectors/   # Local FS, iCloud Drive, Google Drive connectors
├── AssistantCLI/          # Command-line interface
└── AssistantApp/          # Menu-bar and desktop SwiftUI interface
```

The modules should communicate through domain types and protocols, not by importing UI implementations or provider-specific types into the core. A module may be extracted into a separate Swift package later without changing workflow semantics.

### 4.2 Agents

Agents are bounded workers, not unrestricted autonomous processes. Each agent has:

- A versioned identifier and declared capabilities.
- A typed input and output contract.
- An allow-list of tools and data sources.
- A resource/time/token budget.
- A policy for approval, retries, and failure escalation.
- Structured event output and an auditable run record.

Initial agents:

- **Indexer agent:** discovers and updates file/document metadata.
- **Document agent:** extracts, summarizes, transforms, or classifies selected content.
- **Organizer agent:** proposes names, tags, folders, and safe file actions.
- **Workflow agent:** coordinates steps and delegates to tools or other approved agents.
- **Sync agent:** reconciles Google Drive and local/iCloud metadata without overwriting unexpectedly.

Agents should use deterministic tools for file operations and parsing. LLM reasoning may select or sequence tools, but it must not bypass tool permissions or approval checkpoints.

### 4.3 Tools

Define a versioned tool protocol with:

- Tool name/version, JSON-like input schema, output schema, and error schema.
- Declared side effects and required permissions.
- Dry-run/preview support where applicable.
- Timeout, cancellation, retry, and idempotency behavior.
- Redacted structured logging.

Initial tool groups:

- File read/write/move/copy and metadata tools.
- Document extraction, conversion, and search tools.
- Local/iCloud Drive connector tools.
- Google Drive list/read/upload/update tools with scoped OAuth.
- LLM completion/structured-output tools.
- Notification, approval, and run-history tools.

Tool registration must be explicit in configuration or code. Unknown tools are unavailable by default.

### 4.4 LLM providers

Create a provider-neutral interface for text completion, structured extraction, embeddings if later required, streaming, cancellation, token/usage reporting, and provider errors.

Initial provider strategy:

- Implement a mock provider first for deterministic tests.
- Add a Claude adapter behind the provider interface.
- Keep room for additional providers without coupling prompts or workflow definitions to one vendor.
- Store model/provider settings in profiles; store API keys only in macOS Keychain or an equivalent secret store.
- Attach a data-transfer policy to every request: allowed sources, redaction rules, maximum content, retention notice, and user approval requirement.

Prompt templates, output schemas, and model selection belong to versioned configuration or workflow steps rather than scattered implementation constants.

### 4.5 Schedulers and triggers

The scheduler is a replaceable service that emits typed workflow triggers:

- Manual invocation.
- Calendar/time schedules using macOS scheduling facilities.
- Folder/file change events.
- Google Drive change notifications or polling where event delivery is unavailable.
- Finder/Shortcuts/CLI invocation.

Schedules must include timezone, enabled state, concurrency policy, missed-run behavior, retry policy, and last-run status. The scheduler submits a workflow run; it does not contain business logic.

### 4.6 Interfaces

All interfaces call application services, never private implementation details:

- Menu-bar status and quick actions.
- Desktop search, document actions, workflow editor/runner, approvals, and history.
- CLI commands for config validation, indexing, search, workflow execution, scheduling, runs, and diagnostics.
- Finder Services and AppleScript/Shortcuts actions.
- Future interfaces can be added without changing agents or tools.

## 5. Configuration and data model

Use versioned, validated configuration with separate profiles for development and production:

```text
config/
├── default/
│   ├── providers.yaml
│   ├── tools.yaml
│   ├── agents.yaml
│   ├── workflows/
│   └── schedules.yaml
└── examples/
```

Configuration should define enabled providers, model profiles, connector scopes, tool permissions, agent budgets, workflow policies, schedules, logging, and data-retention settings. Secrets are references to Keychain entries, never literal values.

Persist locally:

- File/document catalog and extraction status.
- Connector cursors and sync metadata.
- Workflow definitions and versions.
- Agent/tool/workflow run history and audit events.
- User preferences and migration version.

Do not persist raw cloud prompts or document content in logs unless the user explicitly enables diagnostic capture.

## 6. Incremental TDD delivery plan

Every phase follows this loop: write a failing test or contract fixture, implement the smallest behavior, run focused tests, integrate one vertical slice, then document and refactor. Each phase must leave the project buildable.

### Phase 0 — Bootstrap and contracts

**Tests first**

- Project health command and empty configuration validation.
- Domain serialization/error contract tests.
- Tool and provider protocol contract tests using fakes.

**Implementation**

- Swift package/app/CLI scaffolding.
- Module boundaries and dependency rules.
- CI running formatting, build, unit tests, and contract tests.
- Versioned config loader, migration mechanism, Keychain reference abstraction, and structured logging.

**Exit criteria**

- Clean checkout builds and tests.
- A fake LLM, fake connector, fake tool, and fake scheduler can be injected.
- No production test needs a live cloud service.

### Phase 1 — Local documents vertical slice

**Tests first**

- Folder permission and bookmark behavior.
- Incremental indexing with unchanged/changed/deleted/unavailable files.
- Extraction fixtures for Markdown, Office, PDF, malformed, encrypted, and scanned inputs.
- Search ranking and status behavior.

**Implementation**

- Local connector, document catalog, extractors, index, and search tools.
- Indexer agent using only approved deterministic tools.
- CLI commands for index, search, inspect, and diagnostics.

**Exit criteria**

- A selected folder can be indexed and searched end-to-end offline.
- Re-indexing avoids unchanged work and never modifies originals.

### Phase 2 — LLM and document-operation vertical slice

**Tests first**

- Provider contract tests with mock responses, timeouts, cancellation, malformed structured output, and usage data.
- Claude adapter tests using recorded/sanitized fixtures or a test endpoint, never required for ordinary CI.
- Data-transfer policy tests proving disallowed content is blocked.
- Document operation tests for safe output and failure recovery.

**Implementation**

- Provider-neutral LLM service and Claude adapter.
- Document agent and operation tools.
- Prompt/output schema configuration, consent flow, redaction, and usage display.

**Exit criteria**

- A user can summarize a selected document with a mock provider and configured Claude provider.
- Inputs remain unchanged after success or failure.

### Phase 3 — Workflow and agent orchestration

**Tests first**

- Workflow schema validation and version migration.
- Tool permission enforcement and agent capability boundaries.
- Artifact passing, retries, cancellation, idempotency, approvals, and recovery.
- Deterministic workflow fixtures and event/audit assertions.

**Implementation**

- Workflow engine, agent runner, tool registry, approval service, and run history.
- Starter workflows: document brief, inbox triage preview, and batch extraction.
- CLI workflow execution and dry-run output.

**Exit criteria**

- The same workflow runs through CLI and application services.
- An agent cannot call an unlisted tool or perform an unapproved destructive action.

### Phase 4 — Google Drive and scheduling

**Tests first**

- OAuth scope/configuration validation with mocked authorization.
- Connector cursor, pagination, rate-limit, conflict, and retry tests.
- Scheduler timezone, concurrency, missed-run, and trigger-routing tests.
- Google Drive sync fixtures for new, changed, deleted, and remote-only files.

**Implementation**

- Google Drive connector and tools with minimal scopes.
- Sync agent with explicit cache and conflict policy.
- Scheduler service with time and file-change triggers.
- CLI commands for connector status, schedules, runs, and retry.

**Exit criteria**

- A configured Google Drive folder can be incrementally indexed.
- A scheduled workflow produces an auditable run and respects concurrency/approval policy.

### Phase 5 — Interfaces and integrations

**Tests first**

- View-model/service tests for onboarding, permissions, approvals, errors, and run history.
- CLI acceptance tests against fakes.
- Finder/Shortcuts command contract tests.

**Implementation**

- SwiftUI menu-bar and desktop interfaces.
- Finder Services, AppleScript/Shortcuts, and notification integration.
- Shared interface-to-service adapters with no duplicated workflow logic.

**Exit criteria**

- The primary document workflow can be completed without the terminal.
- CLI, UI, Finder, and Shortcuts all use the same workflow engine.

### Phase 6 — Hardening and release

**Tests first**

- End-to-end regression suite with local, iCloud-like, and mocked Google Drive fixtures.
- Security/privacy tests for secret handling, permissions, redaction, and log contents.
- Performance tests for incremental indexing and bounded concurrent runs.

**Implementation**

- Signed development builds, notarization path, migration/recovery tools, backups, and release docs.
- User docs for configuration, providers, Google Drive permissions, schedules, workflows, privacy, and troubleshooting.

**Exit criteria**

- Focused and full test suites pass from a clean checkout.
- A release build contains no credentials or user document content.
- Every supported failure mode has a visible diagnostic and recovery path.

## 7. Initial project structure

```text
ai-assistance/
├── PLAN.md
├── README.md
├── Package.swift
├── Sources/
│   ├── AssistantDomain/
│   ├── AssistantConfig/
│   ├── AssistantStorage/
│   ├── AssistantDocuments/
│   ├── AssistantTools/
│   ├── AssistantAgents/
│   ├── AssistantWorkflows/
│   ├── AssistantScheduler/
│   ├── AssistantLLM/
│   ├── AssistantConnectors/
│   ├── AssistantCLI/
│   └── AssistantApp/
├── Tests/
│   ├── ContractTests/
│   ├── AssistantDomainTests/
│   ├── AssistantDocumentsTests/
│   ├── AssistantAgentsTests/
│   ├── AssistantWorkflowsTests/
│   ├── AssistantSchedulerTests/
│   ├── AssistantLLMTests/
│   ├── AssistantConnectorTests/
│   └── AssistantCLITests/
├── Fixtures/
│   ├── Documents/
│   ├── Workflows/
│   ├── Providers/
│   └── Connectors/
├── config/
│   ├── default/
│   └── examples/
├── Documentation/
├── .github/
│   ├── skills/
│   │   └── commit-message-writer/
│   │       └── SKILL.md
│   └── workflows/
```

## 8. Example workflows

1. **Document brief:** select a PDF or Office file, extract content, ask the configured Claude provider for a structured summary, and save a Markdown result beside the original.
2. **Inbox triage:** on a schedule or folder event, classify new files, propose names/tags/destinations, show a dry-run, then move only approved files.
3. **Google Drive intake:** detect new Drive files, cache/index them incrementally, create briefs, and write outputs to a configured local or Drive destination.
4. **Batch extraction:** search matching documents, extract fields into CSV/JSON, write results separately, and record per-file failures.
5. **Shortcut action:** receive Finder-selected files, run a saved workflow, and return output paths, approvals, and warnings.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Modular boundaries become abstract without value | Require each module to support a vertical slice and contract tests; avoid premature remote services. |
| Agent performs unsafe or unexpected actions | Capability/tool allow-lists, budgets, dry runs, approval checkpoints, and audit events. |
| Claude or another provider changes behavior | Provider protocol, structured output validation, mock tests, versioned prompts, and fallback/error states. |
| Google Drive OAuth or API limits block workflows | Minimal scopes, token storage in Keychain, cursors, pagination, backoff, rate-limit handling, and connector diagnostics. |
| Schedules duplicate or lose work | Idempotency keys, concurrency policy, durable run states, missed-run policy, and retry tests. |
| Cloud AI exposes sensitive content | Per-request transfer policy, redaction, explicit consent, provider settings, and content-free logs. |
| File-provider delays look like missing files | Distinguish unavailable, deleted, and unsupported states; retry with bounded backoff. |
| Incremental development creates integration drift | Keep the main branch buildable, merge vertical slices, run contract tests in CI, and maintain migration fixtures. |

## 10. Definition of done for the first release

A user can configure a provider such as Claude and a Google Drive connection, select local/iCloud/Drive sources, search supported documents, run or schedule a reusable workflow, let bounded agents use approved tools, review proposed changes, approve safe outputs, and recover from permission, extraction, provider, synchronization, or scheduling failures without losing originals. The behavior is covered by focused TDD tests, integration fixtures, and end-to-end regression tests.

## 11. Decisions to record before implementation

- Minimum supported macOS version and Apple Silicon/Intel support.
- Swift package versus Xcode project details required for app entitlements and integrations.
- Initial Claude API model, authentication, retention settings, and provider fallback policy.
- Google Drive OAuth scopes, selected folders, cache policy, and conflict behavior.
- Configuration format (YAML/JSON/plist) and migration/versioning policy.
- Local persistence technology and backup/recovery strategy.
- Time scheduler implementation and whether a background launch agent is required.
- GUI workflow editor in v1 versus templates plus CLI-defined workflows.
- Personal local distribution versus signed/notarized public distribution.
