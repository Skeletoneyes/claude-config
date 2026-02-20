# Beads Integration

**ENFORCED**: Issue tracking integration for skills that execute in projects with beads initialized.

## Purpose

Beads (bd) provides **persistent cross-session issue tracking** for:
- Multi-session features (planning → `/clear` → execution)
- Complex features with dependencies between milestones
- Technical debt tracking from refactor/analysis skills
- Work prioritization across multiple features

## When Skills Use Beads

**Planner skill:** Beads integration is **ENFORCED**. Planner checks for beads availability and:
- If available: **MUST** create milestone issues and track progress
- If unavailable: **MUST** prompt user to run `bd init` before proceeding with plan approval

**Other skills:** Beads integration is **OPTIONAL**. Skills check for beads availability using `is_beads_available()` and gracefully fall back to TodoWrite when unavailable:

```python
from skills.lib.beads import is_beads_available

if is_beads_available():
    # Optional beads tracking for non-planner skills
    create_issue(title="Feature X", issue_type="feature")
else:
    # Fallback to TodoWrite for in-session tracking
```

## Skill-Specific Integration

### Planner Skill

**Planning phase (step 5):**
- After writing plan, **MUST** create milestone issues for each milestone
- **MUST** link milestone dependencies via `bd dep`
- **MAY** create parent feature issue (optional)

**Execution phase (step 1):**
- **MUST** check for existing milestone issues
- **MUST** note milestone IDs for status tracking

**Execution phase (step 3):**
- **MUST** update milestone status to `in_progress` when starting
- **MUST** close milestone issues when complete

**Execution phase (step 9 - retrospective):**
- **MUST** verify all milestone issues are closed
- **MUST** show `bd ready` for remaining work
- **MAY** close parent feature issue if all milestones done (optional)

### Refactor Skill

**Not yet implemented.** Future integration:
- Create issues for MUST/SHOULD severity findings
- Label with `refactor`, `technical-debt`
- Priority based on severity + impact

### Codebase Analysis Skill

**Not yet implemented.** Future integration:
- Create issues for CRITICAL/HIGH findings
- Label with `security`, `architecture` as appropriate
- Link to specific file:line locations

## Beads vs TodoWrite

| Aspect | Beads (bd) | TodoWrite |
|--------|-----------|-----------|
| **Lifetime** | Persistent across sessions | Single conversation |
| **Survives /clear** | ✅ Yes | ❌ No |
| **Git-backed** | ✅ Yes | ❌ No |
| **Dependencies** | ✅ Yes (`bd dep`) | ❌ No |
| **Status tracking** | ✅ open, in_progress, blocked, closed | ❌ Limited |
| **Use case** | Cross-session work tracking | In-session task tracking |

**Hybrid strategy recommended:**

```
Beads (bd)              → Long-term, cross-session tracking
  ├─ Feature planning   → bd issue created
  ├─ Milestone tracking → bd issues per milestone
  ├─ Technical debt     → bd issues from refactor
  └─ Architecture gaps  → bd issues from analysis

TodoWrite               → Short-term, in-session tracking
  ├─ Debug statements   → Must clean up before session ends
  ├─ QR fix iterations  → Track fixes within review loop
  ├─ Current wave       → Which milestones are running now
  └─ Sub-task breakdown → Temporary task decomposition
```

## Initialization

Beads is initialized **per-project**, not in the config template:

```bash
cd ~/projects/my-app
bd init --prefix APP  # Creates .beads/ with APP-001, APP-002, etc.
```

Skills detect beads in the **current working directory** (the project being worked on), not the config directory.

## Common Commands

```bash
# Create issues
bd create --type feature --title "Add async logging" --priority 1
bd create --type task --title "M0: Configure NLog" --deps APP-001

# Update status
bd update APP-002 --status in_progress
bd close APP-002 "Milestone complete"

# Check work
bd ready                  # Show tasks with no blockers
bd list --status open     # Show all open issues
bd blocked                # Show blocked issues

# Dependencies
bd dep APP-003 APP-002    # APP-003 depends on APP-002
```

## Enforcement Policy

Beads integration is **ENFORCED** for planner skill in projects with `.beads/` directory:

1. **Detection**: `is_beads_available()` returns `False` if `bd list` fails
2. **Requirement**: Planner skill **MUST** create and track milestone issues when beads is available
3. **Fallback**: If beads is not initialized, planner skill **MUST** prompt user to initialize with `bd init`
4. **Error handling**: Planner should not proceed with plan approval until milestone issues are created

For non-planner skills and projects without beads:
- Skills gracefully fall back to TodoWrite for in-session tracking
- No errors if beads unavailable
- Beads remains optional for quick one-off tasks and external issue trackers

## Design Rationale

**Why enforced for planner?** Planning creates cross-session work:
- Plans are meant to persist after `/clear`
- Milestones have dependencies requiring tracking
- Multi-session execution benefits from issue persistence
- Without tracking, planned work gets lost across sessions

**Why optional for other skills?** Not all work needs persistent tracking:
- Simple scripts or prototypes
- Projects with existing issue trackers (JIRA, GitHub Issues)
- One-session features and quick fixes
- Analysis/refactor findings (future enhancement)

**Why per-project init?** Each project has unique needs:
- Different prefix conventions (APP-, FEAT-, BUG-)
- Different tracking granularity
- Some projects share trackers
- User controls when to enable beads per project

## Library API

See `skills/lib/beads.py` for full API:

```python
# Availability check
is_beads_available() -> bool

# Issue operations
create_issue(title, issue_type="task", description="", ...) -> Optional[str]
update_status(issue_id, status) -> bool
close_issue(issue_id, reason="Completed") -> bool
add_dependency(issue_id, depends_on, dep_type="blocks") -> bool

# Queries
get_ready_issues(assignee=None, priority=None) -> list[dict]
```

All functions gracefully handle beads unavailability by returning `None` or `False`.
