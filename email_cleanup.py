#!/usr/bin/env python3
"""
Email Cleanup System - Automatically removes unwanted emails from Gmail

This script connects to Gmail API, identifies unwanted emails based on configured rules,
and moves them to Trash. Includes dry-run mode for safety.

Usage:
    python email_cleanup.py --help
    python email_cleanup.py                    # Run with default config
    python email_cleanup.py --dry-run          # Simulate without trashing (default)
    python email_cleanup.py --execute          # Actually move emails to trash
"""

import os
import sys
import argparse
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
import base64
import re

from config import UNWANTED_RULES, ALLOWLIST, DRY_RUN, MAX_RESULTS_PER_SEARCH

# Gmail API scope - allows reading and modifying emails
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'


class GmailCleanup:
    """Main class for Gmail email cleanup operations."""
    
    def __init__(self, dry_run=True):
        """
        Initialize Gmail cleanup service.
        
        Args:
            dry_run (bool): If True, only print what would be deleted. If False, actually delete.
        """
        self.service = None
        self.dry_run = dry_run
        self.stats = {
            'total_checked': 0,
            'total_trashed': 0,
            'blocked_by_allowlist': 0
        }
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0."""
        try:
            creds = None
            
            # Load existing token if available
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, prompt for login
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save token for future use
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            self.service = build('gmail', 'v1', credentials=creds)
            print("✓ Successfully authenticated with Gmail API")
            
        except FileNotFoundError:
            print(f"✗ Error: {CREDENTIALS_FILE} not found.")
            print("Please download your Gmail API credentials first.")
            print("See README.md for setup instructions.")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            sys.exit(1)
    
    def _is_allowlisted(self, sender_email):
        """
        Check if sender is in the allowlist.
        
        Args:
            sender_email (str): Email address to check
            
        Returns:
            bool: True if sender is allowlisted, False otherwise
        """
        sender_lower = sender_email.lower()
        
        # Check exact matches or partial matches in senders
        for allowed in ALLOWLIST.get('senders', []):
            if allowed.lower() in sender_lower or sender_lower in allowed.lower():
                return True
        
        # Check domain allowlist
        for domain in ALLOWLIST.get('domains', []):
            if sender_lower.endswith(f"@{domain.lower()}"):
                return True
        
        return False
    
    def _decode_header(self, data):
        """
        Safely decode email header.
        
        Args:
            data (str): Potentially encoded header data
            
        Returns:
            str: Decoded header
        """
        try:
            if not data:
                return ""
            
            # Handle base64 encoding
            if data.startswith('=?'):
                # RFC 2047 encoded header
                import email.header
                decoded_parts = email.header.decode_header(data)
                decoded_str = ''.join(
                    part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
                    for part, encoding in decoded_parts
                )
                return decoded_str
            
            return data
        except Exception:
            return data
    
    def _get_sender_and_subject(self, message):
        """
        Extract sender and subject from email message.
        
        Args:
            message (dict): Gmail message object
            
        Returns:
            tuple: (sender_email, subject)
        """
        headers = message['payload'].get('headers', [])
        sender = ""
        subject = ""
        
        for header in headers:
            if header['name'].lower() == 'from':
                sender = header['value']
            elif header['name'].lower() == 'subject':
                subject = header['value']
        
        # Decode headers if needed
        sender = self._decode_header(sender)
        subject = self._decode_header(subject)
        
        # Extract email address from "Name <email@domain.com>" format
        match = re.search(r'<(.+?)>', sender)
        if match:
            sender = match.group(1)
        
        return sender, subject
    
    def _matches_rules(self, sender, subject, message_id):
        """
        Check if email matches any unwanted rules.
        
        Args:
            sender (str): Sender email address
            subject (str): Email subject
            message_id (str): Gmail message ID (for category check)
            
        Returns:
            tuple: (matches_rules: bool, matched_rule: str)
        """
        # Rule 1: Check for no-reply senders
        if UNWANTED_RULES.get('no_reply_senders', {}).get('enabled', False):
            if 'no-reply@' in sender.lower():
                return True, "no-reply sender"
        
        # Rule 2: Check subject keywords
        if UNWANTED_RULES.get('subject_keywords', {}).get('enabled', False):
            keywords = UNWANTED_RULES['subject_keywords'].get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in subject.lower():
                    return True, f"subject keyword '{keyword}'"
        
        # Rule 3: Check Gmail Promotions category
        if UNWANTED_RULES.get('gmail_category_promotions', {}).get('enabled', False):
            try:
                msg = self.service.users().messages().get(
                    userId='me', id=message_id, format='metadata'
                ).execute()
                labels = msg.get('labelIds', [])
                
                # CATEGORY_PROMOTIONS is the label ID for Gmail's Promotions category
                if 'CATEGORY_PROMOTIONS' in labels:
                    return True, "Gmail Promotions category"
            except Exception as e:
                # Silently skip if we can't check categories
                pass
        
        return False, None
    
    def search_and_cleanup(self):
        """
        Search for unwanted emails and move them to trash.
        
        Returns:
            dict: Statistics on emails found and trashed
        """
        print("\n" + "="*70)
        print("EMAIL CLEANUP PROCESS STARTED")
        print("="*70)
        print(f"Dry Run Mode: {'YES (no emails will be trashed)' if self.dry_run else 'NO (emails will be moved to trash)'}")
        print()
        
        try:
            # Build search query for all active rules
            queries = []
            
            if UNWANTED_RULES.get('no_reply_senders', {}).get('enabled', False):
                queries.append('from:no-reply@')
            
            if UNWANTED_RULES.get('subject_keywords', {}).get('enabled', False):
                keywords = UNWANTED_RULES['subject_keywords'].get('keywords', [])
                subject_query = ' OR '.join([f'subject:{kw}' for kw in keywords])
                queries.append(f'({subject_query})')
            
            if UNWANTED_RULES.get('gmail_category_promotions', {}).get('enabled', False):
                queries.append('category:promotions')
            
            if not queries:
                print("✗ No rules are enabled. Nothing to clean up.")
                return self.stats
            
            full_query = ' OR '.join(queries)
            print(f"Search Query: {full_query}\n")
            
            # Search for matching emails
            results = self.service.users().messages().list(
                userId='me', q=full_query, maxResults=MAX_RESULTS_PER_SEARCH
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("✓ No unwanted emails found.")
                return self.stats
            
            print(f"Found {len(messages)} emails matching unwanted rules.\n")
            print("-" * 70)
            
            emails_to_trash = []
            
            # Process each matching email
            for idx, message in enumerate(messages, 1):
                try:
                    msg = self.service.users().messages().get(
                        userId='me', id=message['id'], format='full'
                    ).execute()
                    
                    sender, subject = self._get_sender_and_subject(msg)
                    self.stats['total_checked'] += 1
                    
                    # Check if sender is allowlisted
                    if self._is_allowlisted(sender):
                        self.stats['blocked_by_allowlist'] += 1
                        print(f"  [{idx}] BLOCKED (allowlisted): {sender}")
                        print(f"        Subject: {subject[:60]}...")
                        print()
                        continue
                    
                    # Check if matches any rule
                    matches, rule_name = self._matches_rules(sender, subject, message['id'])
                    
                    if matches:
                        emails_to_trash.append({
                            'id': message['id'],
                            'sender': sender,
                            'subject': subject,
                            'rule': rule_name
                        })
                        
                        print(f"  [{idx}] TRASH ({rule_name}): {sender}")
                        print(f"        Subject: {subject[:60]}...")
                        print()
                
                except Exception as e:
                    print(f"  [{idx}] Error processing message: {e}")
                    continue
            
            print("-" * 70)
            print()
            
            # Move emails to trash
            if emails_to_trash:
                print(f"Ready to move {len(emails_to_trash)} emails to Trash.")
                
                if self.dry_run:
                    print(f"[DRY RUN] Would trash {len(emails_to_trash)} emails (no action taken)")
                    self.stats['total_trashed'] = len(emails_to_trash)
                else:
                    print(f"Moving {len(emails_to_trash)} emails to Trash...")
                    for email in emails_to_trash:
                        try:
                            self.service.users().messages().trash(
                                userId='me', id=email['id']
                            ).execute()
                            self.stats['total_trashed'] += 1
                        except Exception as e:
                            print(f"Error trashing email from {email['sender']}: {e}")
                    print(f"✓ Successfully trashed {self.stats['total_trashed']} emails")
            else:
                print("No emails needed to be trashed (all were allowlisted).")
            
            print()
            print("="*70)
            print("SUMMARY")
            print("="*70)
            print(f"Total emails checked: {self.stats['total_checked']}")
            print(f"Allowlisted (protected): {self.stats['blocked_by_allowlist']}")
            print(f"Moved to Trash: {self.stats['total_trashed']}")
            print("="*70)
            
        except HttpError as error:
            print(f"✗ Gmail API error: {error}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            sys.exit(1)
        
        return self.stats


def main():
    """Parse arguments and run the cleanup."""
    parser = argparse.ArgumentParser(
        description='Automatically clean up unwanted emails from Gmail',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python email_cleanup.py                    # Dry-run (default)
  python email_cleanup.py --dry-run          # Explicit dry-run
  python email_cleanup.py --execute          # Actually trash emails
        """
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually move emails to trash (default is dry-run)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print what would be deleted (default behavior)'
    )
    
    args = parser.parse_args()
    
    # Determine dry-run mode
    dry_run = not args.execute
    
    if args.execute and args.dry_run:
        print("✗ Error: Cannot use both --execute and --dry-run")
        sys.exit(1)
    
    # Run the cleanup
    cleanup = GmailCleanup(dry_run=dry_run)
    cleanup.search_and_cleanup()


if __name__ == '__main__':
    main()
