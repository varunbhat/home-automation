# Repository Rules

## Branch Protection

The `main` branch is protected with the following rules to ensure code quality and prevent accidental changes.

### Active Rules

#### 1. Deletion Protection
- **Rule**: Branch cannot be deleted
- **Purpose**: Prevents accidental deletion of the main branch

#### 2. Non-Fast-Forward (Force Push Protection)
- **Rule**: Force pushes are blocked
- **Purpose**: Prevents rewriting history and maintains git integrity
- **Impact**: `git push --force` is not allowed on main

#### 3. Required Linear History
- **Rule**: Requires linear commit history
- **Purpose**: Keeps a clean, easy-to-follow commit history
- **Impact**: Merge commits may be restricted; prefer rebasing or squash merges

#### 4. Required Signatures
- **Rule**: Commits must be signed
- **Purpose**: Ensures commit authenticity
- **Impact**: You must configure GPG/SSH signing for commits

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

## Commit Signing Setup

To comply with the required signatures rule, set up commit signing:

### GPG Signing

```bash
# Generate GPG key
gpg --full-generate-key

# List keys
gpg --list-secret-keys --keyid-format=long

# Configure git
git config --global user.signingkey YOUR_KEY_ID
git config --global commit.gpgsign true

# Add GPG key to GitHub
gpg --armor --export YOUR_KEY_ID
# Then add at https://github.com/settings/keys
```

### SSH Signing (Recommended for macOS)

```bash
# Configure git to use SSH signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# Add SSH key to GitHub as signing key
# https://github.com/settings/keys (select "Signing Key" type)
```

## Ruleset Details

- **Ruleset ID**: 11430414
- **Name**: Protect main branch
- **Target**: branch
- **Source**: Repository
- **Created**: 2025-12-28
- **View on GitHub**: https://github.com/varunbhat/home-automation/rules/11430414

## Enforcement Level

All rules are actively enforced. Violations will prevent pushes to the main branch.

## Questions?

For issues with branch protection rules, contact the repository administrator or check:
- GitHub Documentation: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets
