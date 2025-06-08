# Setting up GitHub Actions Deployment to Heroku

## Steps to complete setup:

1. **Get your Heroku API Key**:
   ```bash
   heroku auth:token
   ```
   Or go to: https://dashboard.heroku.com/account and scroll to "API Key"

2. **Add secrets to GitHub**:
   - Go to your GitHub repository
   - Click Settings → Secrets and variables → Actions
   - Add these secrets:
     - `HEROKU_API_KEY`: Your Heroku API key from step 1
     - `HEROKU_EMAIL`: Your Heroku account email

3. **Test the deployment**:
   - Make a small change and push to master
   - Check the Actions tab in GitHub to see the deployment progress

## How it works:

- Every push to `master` branch triggers the workflow
- GitHub Actions checks out your code
- Deploys directly to Heroku using their API
- You'll see deployment status in GitHub's Actions tab

## Alternative: Heroku GitHub Integration

If you prefer, you can use Heroku's built-in GitHub integration:
1. Go to your Heroku app dashboard
2. Deploy tab → Deployment method → GitHub
3. Connect your GitHub repo
4. Enable automatic deploys from master branch

This is simpler but gives you less control over the deployment process.
