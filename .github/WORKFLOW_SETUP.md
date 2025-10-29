# GitHub Actions Workflow Setup

## Integration Tests Workflow

The integration tests workflow file needs to be added manually due to GitHub workflow permissions.

### Workflow Template Location

The complete workflow template is available at:
`tests/integration/templates/integration-tests.workflow.yml`

### Target Location

The workflow file should be placed at: `.github/workflows/integration-tests.yml`

### Manual Setup Instructions

1. **Copy the workflow template**:
   ```bash
   # Copy from template to workflows directory
   mkdir -p .github/workflows
   cp tests/integration/templates/integration-tests.workflow.yml .github/workflows/integration-tests.yml
   ```

2. **Or create it manually** using the content from `tests/integration/templates/integration-tests.workflow.yml`

3. **Commit and push with proper permissions**:
   ```bash
   git add .github/workflows/integration-tests.yml
   git commit -m "Add integration tests workflow"
   git push
   ```

### What This Workflow Does

- **Triggers**: Runs on push to main/develop/claude/* branches and pull requests
- **Services**: Sets up PostgreSQL and Redis test services
- **Tests**: Runs all integration tests with coverage reporting
- **Reports**: Uploads coverage to Codecov and test results as artifacts
- **Logs**: Captures service logs on failure for debugging

### Required Secrets

No additional secrets are required. The workflow uses:
- GitHub's built-in PostgreSQL and Redis service containers
- Public Docker images for services
- Standard pytest and coverage tools

### Permissions Required

To add this workflow, you need:
- Write access to the repository
- Permission to modify GitHub Actions workflows

### Alternative: Manual Testing

If you prefer not to use GitHub Actions, you can run integration tests locally:

```bash
cd tests/integration
./run_tests.sh
```

See `tests/integration/README.md` for detailed testing instructions.
