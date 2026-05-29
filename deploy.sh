#!/bin/bash
# Deploy Irina's Compass to GitHub + Streamlit Cloud
# Usage: ./deploy.sh

set -e

echo "=================================================="
echo "   🧭 Irina's Compass - Deploy Script"
echo "=================================================="
echo ""
echo "This will:"
echo "  1. Create a GitHub repo (public)"
echo "  2. Push the code"
echo "  3. Give you the Streamlit Cloud deploy link"
echo ""

# Get credentials
read -p "GitHub username: " GH_USER
read -sp "GitHub Personal Access Token (classic, with 'repo' scope): " GH_TOKEN
echo ""

REPO_NAME="irinas-compass"

echo ""
echo "Step 1/3: Creating GitHub repo..."
curl -s -o /tmp/gh_create.json -w "%{http_code}" \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\",\"private\":false,\"auto_init\":false}" > /tmp/gh_status.txt

STATUS=$(cat /tmp/gh_status.txt)
if [ "$STATUS" = "201" ]; then
    echo "✓ Repo created: https://github.com/$GH_USER/$REPO_NAME"
elif [ "$STATUS" = "422" ]; then
    echo "⚠ Repo may already exist. Continuing..."
else
    echo "✗ GitHub API error (HTTP $STATUS). Check your token."
    cat /tmp/gh_create.json
    exit 1
fi

echo ""
echo "Step 2/3: Pushing code..."
cd "$(dirname "$0")"

# Set git identity if not set
git config user.email "deploy@irinascompass.local" 2>/dev/null || true
git config user.name "Deploy Script" 2>/dev/null || true

# Remove any old remote
git remote remove origin 2>/dev/null || true

# Add remote with token embedded
git remote add origin "https://$GH_USER:$GH_TOKEN@github.com/$GH_USER/$REPO_NAME.git"

# Push
git branch -M main
git push -u origin main -f

echo "✓ Code pushed successfully"

echo ""
echo "Step 3/3: Done!"
echo ""
echo "=================================================="
echo "   🎉 NEXT STEP: Deploy to Streamlit Cloud"
echo "=================================================="
echo ""
echo "1. Go to: https://share.streamlit.io"
echo "2. Sign in with GitHub"
echo "3. Click 'New app'"
echo "4. Select:"
echo "     Repository: $GH_USER/$REPO_NAME"
echo "     Branch: main"
echo "     Main file: app.py"
echo "5. Click 'Deploy'"
echo ""
echo "Your app will be live at:"
echo "  https://$REPO_NAME-*.streamlit.app"
echo ""
echo "Share that link with Irina!"
echo ""
