## MODIFIED Requirements

### Requirement: BackendProvider must expose a unified execution entry
The system MUST provide a stable unified execution entry on `BackendProvider` to coordinate capability handler invocation and provider-level cross-cutting behavior. `CommandFacade` SHALL NOT bypass that entry when executing a concrete backend or an auto-routed backend candidate.

#### Scenario: Single backend executes through provider entry
- **WHEN** `CommandFacade` handles a non-`auto` concrete backend command
- **THEN** it MUST invoke the selected backend through that backend provider's unified execution entry

#### Scenario: Auto backend executes each candidate through provider entry
- **WHEN** `CommandFacade` tries backend candidates in `auto` mode
- **THEN** each candidate execution MUST go through the unified execution entry of that backend provider

### Requirement: Provider unified execution entry must carry provider retry policy
The unified `BackendProvider` execution entry MUST apply provider-level retry policy before invoking a handler, while still allowing side-effect commands to bypass automatic retry.

#### Scenario: Non-side-effect path is wrapped by provider retry policy
- **WHEN** a provider executes a non-side-effect capability whose failure class is retryable
- **THEN** the unified execution entry MUST invoke that handler through the provider retry mechanism

#### Scenario: Side-effect command bypasses provider retry
- **WHEN** a provider executes a command marked with `has_side_effect=True`
- **THEN** the unified execution entry MUST bypass automatic retry and invoke the handler directly

### Requirement: Auto mode shall finish provider-internal recovery before failover
The system MUST treat provider-internal retry as part of a candidate backend's own recovery path. `CommandFacade` SHALL NOT fail over to the next backend until the current candidate has completed its local retry policy and still failed.

#### Scenario: Candidate succeeds after provider-internal retry and stops failover
- **WHEN** the current `auto` candidate succeeds after provider-internal retry handling
- **THEN** the system MUST return that result immediately
- **THEN** it SHALL NOT continue to later candidates

#### Scenario: Candidate enters failover only after provider-internal failure is final
- **WHEN** the current `auto` candidate still raises after provider-internal retry handling completes
- **THEN** `CommandFacade` MUST decide failover eligibility based on that final classified failure
- **THEN** it SHALL NOT treat an unfinished local retry path as a failover trigger

### Requirement: Final backend and attempted candidates shall remain aligned with truthful planning
The system MUST continue to record `candidate_chain`, attempted candidates, `final_backend`, and fallback usage after introducing truthful candidate filtering and explicit identifier adaptation.

#### Scenario: Truthfully filtered candidate chain is reflected in metadata
- **WHEN** an auto-routed shared command is executed after candidate truthfulness filtering
- **THEN** raw metadata SHALL record the filtered candidate chain rather than a broader theoretical backend list
- **THEN** attempted candidates SHALL appear in the same order they were truly executed

#### Scenario: Final backend reflects the backend that succeeded after truthful filtering
- **WHEN** an auto-routed shared command succeeds on a filtered backend candidate
- **THEN** runtime context and raw metadata MUST record that concrete backend as `final_backend`
- **THEN** fallback flags MUST reflect whether the successful backend was not the first filtered candidate