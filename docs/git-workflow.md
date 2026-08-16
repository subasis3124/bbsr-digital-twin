# BBSR Digital Twin — Git and GitHub Workflow Guidelines

This document outlines the standard version control procedures, branch strategies, commit formats, safety checks, and recovery instructions.

---

## 1. Branching Strategy

The repository follows a simplified trunk-based development workflow:
- **`main`**: The primary, stable branch representing completed and verified milestones. No broken or untested code is committed directly to `main`.
- **Feature Branches (`feat/...`)**: Used for active development of specific phases or features (e.g., `feat/phase-2-postgis`, `feat/phase-6-flood-risk`). Once a phase is complete, passing tests, and approved, it is merged into `main`.

---

## 2. Commit Naming Convention

We adhere to the **Conventional Commits** specification. This makes the git history legible and automatically parseable.

### Format
`type(scope): description`

### Types
- **`feat`**: A new feature or phase milestone (e.g., `feat(phase-2): create spatial database schema`).
- **`fix`**: A bug fix (e.g., `fix(api): handle invalid geometry responses`).
- **`docs`**: Documentation changes (e.g., `docs(git-workflow): add branching rules`).
- **`style`**: Formatting, missing semi-colons, etc.; no code change.
- **`refactor`**: Refactoring production code (e.g., `refactor(ml): separate feature extraction from training`).
- **`test`**: Adding or correcting tests (e.g., `test(pipeline): add geometry validator tests`).
- **`chore`**: Maintenance tasks, dependency updates, build configurations.

---

## 3. Milestone Rules

We commit only at **meaningful checkpoints** or when a phase is fully completed and verified.
- **Do not commit local experiments or temporary files** (ensure they are excluded by [.gitignore](file:///d:/AITwin_City/.gitignore)).
- **Do not make micro-commits** for every tiny line change (e.g., "typo fix", "add line"). Squash or combine micro-changes before pushing.
- A commit represents a **fully functional state** of the workspace.

---

## 4. Safety & Verification Requirements

### Before Comitting:
1. **Verify No Secrets**: Run safety checks to ensure no API keys, database passwords, or private environment variables are staged.
   ```bash
   git diff --cached
   ```
2. **Run Tests**: Ensure all automated test suites pass.
3. **Format/Lints**: Run project code formatters (e.g., `black`, `isort`, `npm run lint`).

---

## 5. How to Manually Push

Once you have verified the staged changes and committed them:
```bash
git push origin <branch-name>
```
*Note: Do not force push (`git push --force`) unless explicitly coordinating with the team.*

---

## 6. How Automatic Milestone Pushing Works

The AI coding agent will automatically stage, inspect, commit, and push changes at the end of each completed phase:
1. The agent stages files (`git add <files>`).
2. The agent runs `git diff --cached` to verify no secrets are present.
3. The agent commits the milestone with a Conventional Commit message.
4. The agent pushes to the active remote branch.

---

## 7. Troubleshooting & Recovery

### Recovering from a Failed Push
If a push is rejected due to remote updates:
1. Pull remote changes and rebase your branch:
   ```bash
   git pull --rebase origin <branch-name>
   ```
2. Resolve any conflicts, continue the rebase:
   ```bash
   git add <resolved-files>
   git rebase --continue
   ```
3. Push again:
   ```bash
   git push origin <branch-name>
   ```

### Reverting a Bad Commit
If a bug was introduced and pushed to the remote:
1. Create a revert commit to cleanly undo the changes:
   ```bash
   git revert <commit-hash>
   ```
2. Commit message will be auto-generated: `revert: "feat(phase-2): ..."`
3. Push the revert commit.

### Inspecting Git History
To view the commit history cleanly:
```bash
git log --oneline --graph --decorate
```
To inspect a specific commit's changes:
```bash
git show <commit-hash>
```
To check staged, uncommitted changes:
```bash
git diff --cached
```
