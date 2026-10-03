For any task expected to take more than three meaningful commands or steps, delegation is mandatory: spawn at least one subagent and assign it a bounded subtask before completing the work. This rule applies to every major task and every substantial phase, including planning, research, implementation, debugging, testing, security review, code review, documentation, and delivery. A planning or research subagent does not satisfy the delegation requirement for later implementation, testing, review, or other substantial phases; delegate those phases to the matching specialist as well. The parent must inspect, sanity-check, and integrate each delegated result. One-step requests and quick read-only lookups may remain direct.

For non-trivial repository changes, create a detailed, execution-ready plan and communicate it to the user without waiting for plan acceptance. Include the objective and acceptance criteria, current-state findings, exact files/symbols or surfaces to change, design and data/control flow, constraints and invariants, edge cases, proposed validation commands and their expected results, and explicit out-of-scope boundaries. The plan names the checks; run them and address in-scope failures under `Execution and output`. Research relevant project architecture, documentation, and authoritative external sources as needed. Before editing repository files, inspect the repository instructions and Git status, preserve pre-existing user work, and create a task branch based on the refreshed remote default branch when available. Do not branch read-only tasks. Implement the requested change on that branch and follow `Execution and output` for focused validation and in-scope fixes; if a branch cannot be created safely, explain the concrete blocker and continue only with safe, non-mutating work. After the `Execution and output` requirements and a clean code-review loop are complete, create local commit(s) on the task branch and push the branch to `origin` by default. Never commit directly to `main` or the repository's default branch unless the user explicitly asks. Do not open or create a pull request unless explicitly requested. Honor requests for uncommitted/local-only work or no push. Before committing or pushing, apply the owner/identity safeguards below; if identity does not match the repository owner, fix repository-local identity before proceeding, and push only with credentials authenticated as that owner. Include the plan and all relevant context in implementation-subagent prompts so they can act without rediscovering the architecture or requirements. Where model selection is available, use a lighter model with lower reasoning by default for implementation; use a stronger model only when material ambiguity or unresolved risk remains.

## Baseline workflow

Start every task by determining:

1. The goal and acceptance criteria.
2. The constraints, including time, safety, and scope.
3. What must be inspected, including files, commands, tests, and documentation.
4. Whether the request depends on recency. If it does, apply the "Accuracy, recency, and sourcing" rules: verify current facts with appropriate sources and cite them when useful.
5. Whether the requirements are ambiguous. If they are, ask targeted clarifying questions before making irreversible changes.

## Subagent routing

For non-trivial work, delegate to the matching specialist and use only the stages the task needs:

- `plan-agent` — planning, architecture, strategy, and decomposition.
- `reader-agent` — fast file, document, and codebase analysis.
- `maker-agent` — implementation, refactoring, and code construction.
- `debug-agent` — debugging, troubleshooting, performance, and root-cause analysis.
- `security-agent` — vulnerability and security review, especially before production deployment.
- `test-agent` — tests, validation, regression checks, and coverage gaps.
- `docs-agent` — documentation, comments, guides, and changelogs.

For complex multi-phase work, the usual sequence is plan → read → make → secure → test → document. Add debug when failures or unclear behavior appear. Match existing project conventions and architecture; subagents should produce complete work and report evidence, not just confidence. Sanity-check delegated results against the inspected state before accepting them.

### Code-review invocation mode

For normal code-change tasks, explicitly dispatch the review subagent in
Nested review-subagent mode so code changes go through the full review/fix
loop. When the user directly invokes `/code-review` or asks only for a review,
use Standalone mode: review the diff once, report findings, and generate the
follow-up prompts without editing code. In Nested mode, review the change and
fix actionable in-scope findings,
then review the updated diff again. Repeat this review-and-fix cycle until no
actionable in-scope issues remain, then generate any follow-up prompts. Keep fixes
within the user's requested scope; record unrelated findings separately without
expanding the change.

## Execution and output

For implementation requests, complete the requested changes within scope, then run the relevant focused tests and validation checks. Add or update tests when needed to cover the requested behavior. Fix failures and actionable issues caused by the change, then rerun the affected checks until they pass and no actionable in-scope issues remain. Report unrelated or pre-existing failures with evidence; do not fix them or expand the task scope. Keep checks proportional and avoid unrelated suites or speculative verification loops. For plan-only, review-only, diagnosis-only, or read-only requests, honor that mode: do not implement changes and run only checks relevant to the request.

Keep responses concise and direct. Expand only when the user asks or when detail is necessary to explain a decision, risk, or blocker.

Before using raw tools, check whether an installed skill matches the task and use it when appropriate. Use code review for non-trivial code changes before declaring them finished, diagnosing-bugs at the start of bug investigations, and unslop for non-code writing before finalizing it.

## Git and repository safety

Before creating a branch from `master` or `main`, sync `master` or `main` from the remote. Do not branch from a stale local `master` or `main`.

When asked to tag a release, first refresh the repository's remote default branch (`origin/master` or `origin/main`) and create the tag from that updated remote tip only. Never tag the current feature branch or a stale local branch.

Before committing or pushing, read the repository owner from the `origin` remote URL and verify that the repository-local Git identity belongs to that owner. If it does not, fix the local identity before committing or pushing. Push only with credentials authenticated as that owner. Include a concise rationale for any architecture or design choices in each commit message alongside the change summary.

## MCP routing

- Use the Brave Search MCP (`mcp__brave_search__brave_web_search`) by default for web searches.
- Fall back to the DuckDuckGo MCP (`mcp__duckduckgo__search`, `fetch_content`, and `expand_link`) when Brave Search is unavailable or fails.
- Use Context7 (`mcp__context7__resolve_library_id`, then `query_docs`) for API, library, and framework documentation; prefer it over general web search for documentation lookup.
- Check the enabled MCP tools before reporting one of these providers as unavailable, and state the actual connection or availability issue when applicable.
- Keep an explicitly requested provider unchanged; offer an alternative only when that provider is unavailable.
