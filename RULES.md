# Repository Rules

## Branch Protection

The `main` branch is protected with the following rules to ensure code quality and prevent accidental changes.

### Active Rules

#### 1. Pull Request Required
- **Rule**: All changes to main must go through a pull request
- **Purpose**: Prevents direct commits to main branch
- **Impact**: Cannot push directly to main; must create PR first
- **Approvals Required**: 0 (self-merge allowed)

#### 2. Deletion Protection
- **Rule**: Branch cannot be deleted
- **Purpose**: Prevents accidental deletion of the main branch

#### 3. Non-Fast-Forward (Force Push Protection)
- **Rule**: Force pushes are blocked
- **Purpose**: Prevents rewriting history and maintains git integrity
- **Impact**: `git push --force` is not allowed on main

#### 4. Required Linear History
- **Rule**: Requires linear commit history
- **Purpose**: Keeps a clean, easy-to-follow commit history
- **Impact**: Prefer rebasing or squash merges to keep history clean

### Enforcement

- **Status**: Active
- **Applies to**: `refs/heads/main`
- **Bypass actors**: None (all contributors must follow rules)

## Development Workflow

Since the main branch is protected, follow this workflow:

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes and Commit

```bash
# Make your changes
git add .
git commit -S -m "feat: your feature description"  # -S for signed commits
```

### 3. Push Feature Branch

```bash
git push origin feature/your-feature-name
```

### 4. Create Pull Request

```bash
gh pr create --title "Your PR Title" --body "Description of changes"
```

### 5. Merge Pull Request

After review and approval, merge via GitHub UI or:

```bash
gh pr merge --squash  # Squash commits for linear history
```

## Notes

- **No commit signing required**: Commits do not need to be GPG or SSH signed
- **Self-merge allowed**: You can approve and merge your own pull requests (no review required)
- **Linear history preferred**: Use squash or rebase merges to maintain clean history

## Ruleset Details

- **Ruleset ID**: 11430460
- **Name**: Protect main branch - require PR
- **Target**: branch
- **Source**: Repository
- **Created**: 2025-12-28
- **View on GitHub**: https://github.com/varunbhat/home-automation/rules/11430460

## Enforcement Level

All rules are actively enforced. Violations will prevent pushes to the main branch.

## Questions?

For issues with branch protection rules, contact the repository administrator or check:
- GitHub Documentation: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets
