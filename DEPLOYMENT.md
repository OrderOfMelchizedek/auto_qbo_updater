# Deployment Guide - FOM to QuickBooks Automation

This guide covers deploying the FOM to QuickBooks automation application to Heroku.

## Prerequisites

1. **Heroku Account**: Sign up at [heroku.com](https://www.heroku.com/)
2. **Heroku CLI**: Install from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
3. **Git**: Ensure your code is committed to Git
4. **Production API Credentials**: 
   - QuickBooks Production App credentials
   - Google Gemini API key

## Step-by-Step Deployment

### 1. Create Heroku App

```bash
# Login to Heroku
heroku login

# Create a new Heroku app (choose a unique name)
heroku create your-app-name

# Or if you want Heroku to generate a name
heroku create
```

### 2. Add Required Add-ons

```bash
# Add Redis for session storage (required for production)
heroku addons:create heroku-redis:mini

# Note: This will automatically set the REDIS_URL environment variable
```

### 3. Configure Environment Variables

Set all required environment variables:

```bash
# Generate and set Flask secret key
heroku config:set FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# Set QuickBooks credentials
heroku config:set QBO_CLIENT_ID=your_production_client_id
heroku config:set QBO_CLIENT_SECRET=your_production_client_secret
heroku config:set QBO_REDIRECT_URI=https://your-app-name.herokuapp.com/qbo/callback
heroku config:set QBO_ENVIRONMENT=production

# Set Gemini API key
heroku config:set GEMINI_API_KEY=your_gemini_api_key

# Optional: Set specific Gemini model
heroku config:set GEMINI_MODEL=gemini-2.5-flash-preview-05-20

# Optional: Configure logging level
heroku config:set LOG_LEVEL=INFO

# Optional: Configure date validation
heroku config:set DATE_WARNING_DAYS=365
heroku config:set FUTURE_DATE_LIMIT_DAYS=7
```

### 4. Update QuickBooks App Settings

1. Go to [Intuit Developer Portal](https://developer.intuit.com/)
2. Select your app
3. Go to "Keys & OAuth" or "Keys & credentials"
4. Add your Heroku URL to redirect URIs:
   - `https://your-app-name.herokuapp.com/qbo/callback`
5. Switch to Production keys (if not already)

### 5. Deploy the Application

```bash
# Deploy to Heroku
git push heroku master

# Or if you're on a different branch
git push heroku your-branch:master

# Scale up the web dyno
heroku ps:scale web=1
```

### 6. Initialize the Database

If using database-backed sessions (optional):

```bash
# Run database migrations if applicable
heroku run python -c "from src.app import db; db.create_all()"
```

### 7. Verify Deployment

```bash
# Check application logs
heroku logs --tail

# Open the application
heroku open

# Check application health
curl https://your-app-name.herokuapp.com/health
```

## Production Configuration

### SSL/HTTPS

Heroku provides free SSL certificates. Your app will be accessible via HTTPS automatically.

### Custom Domain (Optional)

```bash
# Add a custom domain
heroku domains:add www.yourdomain.com

# View DNS configuration instructions
heroku domains
```

### Scaling

```bash
# Scale to multiple dynos for high availability
heroku ps:scale web=2

# Enable automatic scaling (requires paid plan)
heroku autoscale:enable web --min 1 --max 4
```

## Monitoring and Maintenance

### View Logs

```bash
# Real-time logs
heroku logs --tail

# View recent logs
heroku logs -n 1000

# Filter by process type
heroku logs --ps web
```

### Monitor Performance

```bash
# View current dyno status
heroku ps

# View metrics (requires paid plan)
heroku metrics
```

### Health Checks

The application provides several endpoints for monitoring:
- `/health` - Basic health check
- `/ready` - Checks external service connectivity
- `/auth-status` - OAuth status

### Backup Data

```bash
# If using Heroku Postgres (for future enhancement)
heroku pg:backups:capture
heroku pg:backups:download
```

## Troubleshooting

### Common Issues

1. **"Application Error" on load**
   ```bash
   # Check logs for specific error
   heroku logs --tail
   
   # Ensure all environment variables are set
   heroku config
   
   # Restart the application
   heroku restart
   ```

2. **OAuth redirect errors**
   - Verify QBO_REDIRECT_URI matches exactly in both Heroku config and QuickBooks app
   - Ensure it uses HTTPS, not HTTP
   - Check that production keys are being used

3. **Session errors**
   ```bash
   # Verify Redis is provisioned
   heroku addons
   
   # Check Redis connection
   heroku redis:cli
   > PING
   # Should return PONG
   ```

4. **Memory issues**
   ```bash
   # Check memory usage
   heroku ps
   
   # Scale to larger dyno if needed
   heroku ps:resize web=standard-2x
   ```

### Debug Mode (Temporary)

For debugging production issues:

```bash
# Enable debug logging temporarily
heroku config:set LOG_LEVEL=DEBUG

# Remember to disable after debugging
heroku config:set LOG_LEVEL=INFO
```

## Security Best Practices

1. **Regular Updates**
   - Keep dependencies updated: `pip list --outdated`
   - Monitor security advisories

2. **Credential Rotation**
   - Rotate API keys periodically
   - Update Flask secret key if compromised

3. **Access Control**
   - Use Heroku's team features for multi-user access
   - Enable 2FA on Heroku and QuickBooks accounts

4. **Monitoring**
   - Set up alerts for errors
   - Monitor for unusual activity

## Rollback Procedures

If deployment causes issues:

```bash
# View release history
heroku releases

# Rollback to previous version
heroku rollback

# Or rollback to specific version
heroku rollback v42
```

## Continuous Deployment (Optional)

### GitHub Integration

1. Connect GitHub repo in Heroku Dashboard
2. Enable automatic deploys from master branch
3. Enable "Wait for CI to pass" if you have tests

### Manual Pipeline

```bash
# Create a pipeline
heroku pipelines:create fom-qbo-pipeline

# Add staging app
heroku create fom-qbo-staging
heroku pipelines:add fom-qbo-pipeline -a fom-qbo-staging -s staging

# Add production app
heroku pipelines:add fom-qbo-pipeline -a your-app-name -s production

# Promote from staging to production
heroku pipelines:promote -a fom-qbo-staging
```

## Cost Considerations

- **Free Tier**: Limited to 550-1000 dyno hours/month
- **Hobby Tier ($7/month)**: Always-on dyno, SSL
- **Standard Tier**: Horizontal scaling, better performance
- **Redis**: Mini plan is free, larger plans have costs

## Support

- **Heroku Support**: [help.heroku.com](https://help.heroku.com/)
- **Application Issues**: Check GitHub issues
- **QuickBooks API**: [developer.intuit.com/support](https://developer.intuit.com/app/developer/support)