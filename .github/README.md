# GitHub Workflows

This directory contains GitHub Actions workflows for CI/CD.

## Workflows

### deploy.yml
- **Trigger**: Push to master branch
- **Action**: Deploys application to Heroku
- **Requirements**:
  - `HEROKU_API_KEY` secret
  - `HEROKU_EMAIL` secret
