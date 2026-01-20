"""
AWS Lambda version of Email Cleanup System

This version is designed to run on AWS Lambda triggered by EventBridge.
Credentials are loaded from AWS Secrets Manager instead of local files.

To deploy:
1. Store Gmail credentials in AWS Secrets Manager
2. Package this code with dependencies
3. Create Lambda function with this code
4. Set EventBridge rule to trigger on schedule (e.g., daily at 9 AM)
"""

import json
import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import boto3
import re


class LambdaGmailCleanup:
    """Gmail cleanup for AWS Lambda."""
    
    def __init__(self, dry_run=False):
        self.service = None
        self.dry_run = dry_run
        self.stats = {
            'total_checked': 0,
            'total_trashed': 0,
            'blocked_by_allowlist': 0
        }
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate using credentials from AWS Secrets Manager."""
        try:
            # Retrieve Gmail credentials from Secrets Manager
            client = boto3.client('secretsmanager')
            secret_response = client.get_secret_value(SecretId='gmail-credentials')
            credentials_json = json.loads(secret_response['SecretString'])
            
            # Build credentials object
            creds = Credentials.from_authorized_user_info(
                credentials_json,
                scopes=['https://www.googleapis.com/auth/gmail.modify']
            )
            
            self.service = build('gmail', 'v1', credentials=creds)
            print("✓ Authenticated with Gmail API (Lambda)")
            
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            raise
    
    def _is_allowlisted(self, sender_email):
        """Check if sender is in allowlist."""
        allowlist_senders = ["windsor metro west", "texas oncology", "kelvin.guerra", "princess.martin"]
        sender_lower = sender_email.lower()
        
        for allowed in allowlist_senders:
            if allowed.lower() in sender_lower or sender_lower in allowed.lower():
                return True
        
        return False
    
    def _get_sender_and_subject(self, message):
        """Extract sender and subject from message."""
        headers = message['payload'].get('headers', [])
        sender = ""
        subject = ""
        
        for header in headers:
            if header['name'].lower() == 'from':
                sender = header['value']
            elif header['name'].lower() == 'subject':
                subject = header['value']
        
        # Extract email address
        match = re.search(r'<(.+?)>', sender)
        if match:
            sender = match.group(1)
        
        return sender, subject
    
    def _matches_rules(self, sender, subject):
        """Check if email matches unwanted rules."""
        # Rule 1: no-reply senders
        if 'no-reply@' in sender.lower():
            return True, "no-reply sender"
        
        # Rule 2: Subject keywords
        keywords = ["newsletter", "unsubscribe", "promotional", "promotion"]
        for keyword in keywords:
            if keyword.lower() in subject.lower():
                return True, f"subject keyword '{keyword}'"
        
        return False, None
    
    def search_and_cleanup(self):
        """Search for and clean up unwanted emails."""
        try:
            query = '(from:no-reply@ OR subject:newsletter OR subject:unsubscribe OR subject:promotional OR category:promotions)'
            
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("No unwanted emails found.")
                return self.stats
            
            print(f"Found {len(messages)} matching emails.")
            
            emails_to_trash = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full'
                ).execute()
                
                sender, subject = self._get_sender_and_subject(msg)
                self.stats['total_checked'] += 1
                
                if self._is_allowlisted(sender):
                    self.stats['blocked_by_allowlist'] += 1
                    continue
                
                matches, rule = self._matches_rules(sender, subject)
                if matches:
                    emails_to_trash.append({
                        'id': message['id'],
                        'sender': sender,
                        'subject': subject
                    })
            
            if not self.dry_run:
                for email in emails_to_trash:
                    self.service.users().messages().trash(
                        userId='me', id=email['id']
                    ).execute()
                    self.stats['total_trashed'] += 1
            else:
                self.stats['total_trashed'] = len(emails_to_trash)
            
            return self.stats
        
        except Exception as e:
            print(f"Error during cleanup: {e}")
            raise


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    try:
        cleanup = LambdaGmailCleanup(dry_run=False)
        stats = cleanup.search_and_cleanup()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Email cleanup completed',
                'stats': stats
            })
        }
    
    except Exception as e:
        print(f"Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error during email cleanup',
                'error': str(e)
            })
        }
