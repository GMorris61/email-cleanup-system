# Email Cleanup System

A Python-based automation tool that intelligently filters and removes unwanted emails from Gmail. Built with security in mind, featuring dry-run mode, allowlist protection, and easy AWS Lambda deployment.

## 📋 Problem Statement

Email inboxes are flooded with unwanted messages:
- Automated system notifications (no-reply emails)
- Marketing newsletters and promotions
- Recurring vendor notices
- Low-priority alerts

This clutter increases the risk of missing important time-sensitive communications. The Email Cleanup System automatically identifies and removes these unwanted emails while protecting important senders through an allowlist.

## ✨ Features

- **3 Smart Filtering Rules**
  - Sender-based filtering (no-reply addresses)
  - Subject keyword matching (newsletter, promotional, unsubscribe)
  - Gmail category filtering (Promotions)
  
- **Safety First**
  - Dry-run mode (default) — see what would be deleted without actually deleting
  - Allowlist protection — important senders are never trashed
  - Move to Trash only (never permanent deletion)
  
- **Easy to Use**
  - Works locally on your laptop
  - Deployable to AWS Lambda with EventBridge scheduling
  - Clear configuration file
  - Detailed logging and statistics

## 🔧 Setup

### Prerequisites
- Python 3.8+
- Gmail account
- Google Cloud Project with Gmail API enabled

### Step 1: Clone the Repository

```bash
git clone https://github.com/GMorris61/email-cleanup-system.git
cd email-cleanup-system
```

### Step 2: Create a Google Cloud Project & Get Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (name: "Email Cleanup System")
3. Enable the **Gmail API**
4. Go to **APIs & Services** → **Credentials**
5. Click **"Configure Consent Screen"** → Choose **External**
6. Fill in app name and your email
7. Add the Gmail API scope (`gmail.modify`)
8. Add your test user (your Gmail address)
9. Go back to **Credentials** → **Create OAuth 2.0 Client ID**
10. Choose **Desktop application**
11. Download the JSON file and save it as `credentials.json` in this directory

**Important:** Never commit `credentials.json` to GitHub (it's in `.gitignore`)

### Step 3: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Your Rules

Edit `config.py` to customize:

```python
# Enable/disable specific rules
UNWANTED_RULES = {
    "no_reply_senders": {"enabled": True, ...},
    "subject_keywords": {"enabled": True, "keywords": [...], ...},
    "gmail_category_promotions": {"enabled": True, ...}
}

# Protect important senders
ALLOWLIST = {
    "senders": ["windsor metro west", "texas oncology", "kelvin.guerra", "princess.martin"],
    "domains": ["company.com"]  # Add entire domains if needed
}
```

## 🚀 Usage

### Local Testing (Dry-Run)

Test what emails would be trashed **without actually trashing them**:

```bash
source venv/bin/activate
python3 email_cleanup.py --dry-run
```

Output will show:
- Number of emails found
- Rules that matched each email
- Total statistics
- Allowlisted emails (protected)

### Actually Delete Emails

Move matched emails to Gmail Trash:

```bash
python3 email_cleanup.py --execute
```

**Warning:** This will permanently move emails to Trash. Always run with `--dry-run` first!

### Get Help

```bash
python3 email_cleanup.py --help
```

## 📊 Output Example

```
======================================================================
EMAIL CLEANUP PROCESS STARTED
======================================================================
Dry Run Mode: YES (no emails will be trashed)

Search Query: (from:no-reply@ OR (subject:newsletter OR subject:unsubscribe OR subject:promotional OR subject:promotion) OR category:promotions)

Found 100 emails matching unwanted rules.

----------------------------------------------------------------------
  [1] TRASH (no-reply sender): noreply@notifications.example.com
        Subject: System Alert: Database Backup Complete
  
  [2] BLOCKED (allowlisted): support@texas-oncology.com
        Subject: Your Appointment Confirmation
  
  [3] TRASH (subject keyword 'newsletter'): newsletter@marketing.com
        Subject: Weekly Newsletter - January 20
----------------------------------------------------------------------

======================================================================
SUMMARY
======================================================================
Total emails checked: 100
Allowlisted (protected): 1
Moved to Trash: 99
======================================================================
```

## ☁️ AWS Lambda Deployment

### Step 1: Prepare Lambda Code

The `lambda_handler.py` file is ready for deployment. It:
- Reads Gmail credentials from AWS Secrets Manager
- Runs the same cleanup logic as the local script
- Returns summary statistics

### Step 2: Store Credentials in AWS Secrets Manager

```bash
# Create a secret with your Gmail credentials
aws secretsmanager create-secret \
  --name gmail-credentials \
  --secret-string '{
    "type": "authorized_user",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

**Note:** Get refresh token by running the local script and extracting from `token.pickle`

### Step 3: Create Lambda Function

1. Go to [AWS Lambda Console](https://console.aws.amazon.com/lambda)
2. Click **"Create function"**
3. Choose **Python 3.11**
4. Add execution role with permissions for:
   - Secrets Manager (read)
   - CloudWatch Logs (write)
5. Upload code (zip all files + dependencies)
6. Set handler to `lambda_handler.lambda_handler`
7. Increase timeout to 60 seconds

### Step 4: Schedule with EventBridge

1. Go to [EventBridge Console](https://console.aws.amazon.com/events)
2. Click **"Create rule"**
3. Set schedule: `cron(0 9 * * ? *)` (9 AM daily)
4. Add Lambda function as target
5. Done! ✅

## 📁 Project Structure

```
email-cleanup-system/
├── email_cleanup.py       # Main local script
├── lambda_handler.py      # AWS Lambda version
├── config.py              # Configuration & rules
├── requirements.txt       # Python dependencies
├── .gitignore             # Protect credentials
├── README.md              # This file
└── screenshots/           # Before/after proof
    ├── before.png
    ├── script_output.png
    └── trash_folder.png
```

## 🔒 Security Best Practices

✅ **What This Project Does Right:**
- Credentials stored locally, never in code
- `credentials.json` in `.gitignore` (never committed)
- Dry-run mode by default (safety first)
- Allowlist protection for important senders
- Move to Trash only (recoverable)

⚠️ **Important Reminders:**
- Never share your `credentials.json` file
- Never commit `token.pickle` to GitHub
- Review allowlist before running
- Always test with `--dry-run` first
- For Lambda: Store credentials in AWS Secrets Manager, not in code

## 🧪 Testing

### Local Test with Dry-Run
```bash
python3 email_cleanup.py --dry-run
```

### Local Test with Execution
```bash
python3 email_cleanup.py --execute
```

### Lambda Test (AWS Console)
Create a test event and trigger the function to verify it works.

## 📈 Monitoring & Logs

### Local
Output is printed to console with detailed statistics.

### Lambda
View logs in **CloudWatch** → **Log Groups** → `/aws/lambda/email-cleanup-system`

## 🛠️ Customization

### Add More Rules

Edit `config.py` and add to `UNWANTED_RULES`:

```python
"my_custom_rule": {
    "enabled": True,
    "pattern": "my_pattern",
    "description": "My custom filter"
}
```

Then add matching logic to `_matches_rules()` in `email_cleanup.py`.

### Add More Allowlist Entries

Edit `ALLOWLIST` in `config.py`:

```python
ALLOWLIST = {
    "senders": [
        "important.person@company.com",
        "support@critical-vendor.com"
    ],
    "domains": [
        "company.com",
        "important-partner.com"
    ]
}
```

## 📚 Files Reference

- **`email_cleanup.py`** - Main script with Gmail API integration
- **`lambda_handler.py`** - AWS Lambda wrapper
- **`config.py`** - Configuration (rules, allowlist, dry-run)
- **`requirements.txt`** - Python dependencies
- **`.gitignore`** - Protects credentials from being committed

## 🐛 Troubleshooting

### "Authentication failed"
- Verify `credentials.json` is in the project directory
- Delete `token.pickle` and try again (will prompt for re-authorization)

### "Access blocked: Email Cleanup System has not completed Google verification"
- Add your Gmail address as a **Test User** in Google Cloud Console
- Go to Audience → Test users → Add users

### "No unwanted emails found"
- Check that your rules are enabled in `config.py`
- Verify your Gmail account has emails matching those rules
- Try adjusting search keywords

### Lambda timeout
- Increase timeout to 60 seconds in Lambda configuration
- Reduce `MAX_RESULTS_PER_SEARCH` if needed

## 📝 License

This project is open source and available under the MIT License.

## 👤 Author

Created by **GMorris61** for portfolio demonstration.

---

## 📸 Screenshots (Proof of Concept)

See the `screenshots/` folder for proof of execution:
- Before: Original inbox with 100+ unwanted emails
- Output: Script showing 91 emails to be trashed
- After: Gmail Trash folder showing moved emails

---

**Questions?** Feel free to open an issue on GitHub!
