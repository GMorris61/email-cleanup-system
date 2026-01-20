# ============================================================================
# EMAIL CLEANUP SYSTEM - CONFIGURATION
# ============================================================================
# Define the rules for identifying unwanted emails and the allowlist

# UNWANTED EMAIL RULES
# These rules identify emails that should be moved to trash
UNWANTED_RULES = {
    # Rule 1: Sender contains no-reply addresses (typically automated/system emails)
    "no_reply_senders": {
        "enabled": True,
        "pattern": "no-reply@",
        "description": "System/automated emails from no-reply addresses"
    },
    
    # Rule 2: Subject contains newsletter/promo keywords
    "subject_keywords": {
        "enabled": True,
        "keywords": ["newsletter", "unsubscribe", "promotional", "promotion", "unsubscribe here"],
        "description": "Marketing and newsletter emails"
    },
    
    # Rule 3: Gmail category = Promotions
    "gmail_category_promotions": {
        "enabled": True,
        "category": "PROMOTIONS",
        "description": "Gmail's built-in Promotions category"
    }
}

# ALLOWLIST - Senders who should NEVER be trashed
# Even if they match unwanted rules, emails from these senders/domains will be preserved
ALLOWLIST = {
    "senders": [
        "windsor metro west",
        "texas oncology",
        "kelvin.guerra",  # Can add full email or partial
        "princess.martin"
    ],
    "domains": [
        # Add entire domains here to whitelist all senders from them
        # Examples:
        # "company.com",
        # "important-vendor.com"
    ]
}

# DRY RUN MODE
# When True, script will only print what it would trash (no actual deletion)
# Set to False to actually move emails to trash
DRY_RUN = True

# EMAIL SEARCH LIMITS
MAX_RESULTS_PER_SEARCH = 100  # Gmail API pagination limit
