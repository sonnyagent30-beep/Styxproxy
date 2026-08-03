# Staging & Deployment Workflow

This guide explains how to deploy changes from development to staging and production.

## Environments

| Environment | URL | Branch | Purpose |
|-------------|-----|--------|---------|
| Staging | staging.styxproxy.com | develop | Testing new features before production |
| Production | styxproxy.com | main | Live site for customers |

## Deployment Flow

1. **Develop locally** - Work on your feature in a feature branch
2. **Push to develop** - Merge your branch into `develop`
3. **Staging auto-deploys** - Vercel automatically deploys the `develop` branch
4. **Verify on staging** - Run browser verification to check the site works
5. **Manual production deploy** - Merge `develop` into `main` when ready

## Deploying to Staging

Staging automatically deploys when you push to the `develop` branch.

```bash
# Make sure you're on develop and have the latest
git checkout develop
git pull origin develop

# Merge your feature branch
git merge feature/your-feature-name

# Push to trigger staging deploy
git push origin develop
```

After pushing, wait about 2-3 minutes for Vercel to build and deploy.

## Verifying on Staging

Run the browser verification script to check that the site loads correctly:

```bash
node scripts/browser-verify.js
```

This script will:
- Open a browser and go to staging.styxproxy.com
- Check that the page loads without errors
- Take a screenshot for verification

If verification fails, check the Vercel dashboard for build errors.

## Deploying to Production

Production requires a manual merge from `develop` to `main`.

```bash
# Make sure develop is up to date
git checkout develop
git pull origin develop

# Merge into main
git checkout main
git pull origin main
git merge develop

# Push to trigger production deploy
git push origin main
```

After pushing, verify the production site works:

```bash
STAGING_URL=https://styxproxy.com node scripts/browser-verify.js
```

## Rollback Procedure

If something goes wrong after deployment:

1. **Quick rollback** - Revert the merge and push again:
   ```bash
   git revert -m 1 <merge-commit>
   git push origin main
   ```

2. **Rollback to previous release** - Use Vercel dashboard to redeploy a previous version

## Troubleshooting

### Build fails on Vercel
- Check the Vercel deploy log for errors
- Common issues: missing environment variables, build script errors

### Site not loading
- Check Cloudflare DNS settings
- Verify the domain is pointing to Vercel

### Browser verification fails
- Run manually with browser to see the error
- Check browser console for JavaScript errors
