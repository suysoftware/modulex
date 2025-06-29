#!/usr/bin/env python3
"""
Gmail Integration - Main Script
"""
import json
import sys
import os
import base64
from email.message import EmailMessage
from email.header import decode_header
from base64 import urlsafe_b64decode
from email import message_from_bytes
from typing import Dict, Any, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def debug_print(message: str):
    """Print debug messages to stderr to avoid interfering with JSON output"""
    print(message, file=sys.stderr)


def decode_mime_header(header: str) -> str:
    """Helper function to decode encoded email headers"""
    decoded_parts = decode_header(header)
    decoded_string = ''
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            # Decode bytes to string using the specified encoding
            decoded_string += part.decode(encoding or 'utf-8')
        else:
            # Already a string
            decoded_string += part
    return decoded_string


class GmailService:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.scopes = ['https://www.googleapis.com/auth/gmail.modify']
        
        if not self.client_id:
            raise ValueError("GOOGLE_CLIENT_ID environment variable not set")
        if not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_SECRET environment variable not set")
        if not self.access_token:
            raise ValueError("ACCESS_TOKEN environment variable not set")
        
        debug_print(f"🔑 DEBUG [Gmail]: Client ID: {self.client_id[:20]}...")
        debug_print(f"🔑 DEBUG [Gmail]: Client Secret: {'*' * len(self.client_secret)}")
        debug_print(f"🔑 DEBUG [Gmail]: Access Token: {self.access_token[:20]}...")
        
        self.credentials = self._create_credentials()
        self.service = self._get_service()
        self.user_email = self._get_user_email()
        
        debug_print(f"✅ DEBUG [Gmail]: Service initialized for user: {self.user_email}")

    def _create_credentials(self) -> Credentials:
        """Create credentials from access token"""
        debug_print('🔑 DEBUG [Gmail]: Creating credentials from access token')
        
        # Create credentials object from access token
        credentials = Credentials(
            token=self.access_token,
            scopes=self.scopes
        )
        
        debug_print('✅ DEBUG [Gmail]: Credentials created successfully')
        return credentials

    def _get_service(self):
        """Initialize Gmail API service"""
        try:
            service = build('gmail', 'v1', credentials=self.credentials)
            return service
        except HttpError as error:
            debug_print(f'❌ DEBUG [Gmail]: Error building Gmail service: {error}')
            raise ValueError(f'Gmail service error: {error}')

    def _get_user_email(self) -> str:
        """Get user email address"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress', '')
        except HttpError as error:
            debug_print(f'❌ DEBUG [Gmail]: Error getting user profile: {error}')
            raise ValueError(f'Profile error: {error}')

    def send_email(self, recipient: str, subject: str, message: str) -> Dict[str, Any]:
        """Send an email"""
        try:
            debug_print(f"📧 DEBUG [Gmail]: Sending email to {recipient}")
            
            message_obj = EmailMessage()
            message_obj.set_content(message)
            message_obj['To'] = recipient
            message_obj['From'] = self.user_email
            message_obj['Subject'] = subject

            encoded_message = base64.urlsafe_b64encode(message_obj.as_bytes()).decode()
            create_message = {'raw': encoded_message}
            
            send_message = self.service.users().messages().send(userId="me", body=create_message).execute()
            
            debug_print(f"✅ DEBUG [Gmail]: Email sent successfully. Message ID: {send_message['id']}")
            
            return {
                "status": "success",
                "message_id": send_message["id"],
                "recipient": recipient,
                "subject": subject
            }
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Send email error: {error}")
            return {"status": "error", "error_message": str(error)}

    def get_unread_emails(self, max_results: int = 10) -> Dict[str, Any]:
        """Get unread emails from inbox"""
        try:
            debug_print(f"📬 DEBUG [Gmail]: Getting {max_results} unread emails")
            
            query = 'in:inbox is:unread category:primary'
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            debug_print(f"📊 DEBUG [Gmail]: Found {len(messages)} unread emails")
            
            emails = []
            for msg in messages:
                email_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in email_detail['payload']['headers']}
                
                emails.append({
                    "id": msg['id'],
                    "thread_id": email_detail['threadId'],
                    "from": headers.get('From', ''),
                    "subject": decode_mime_header(headers.get('Subject', '')),
                    "date": headers.get('Date', ''),
                    "snippet": email_detail.get('snippet', '')
                })
            
            return {
                "emails": emails,
                "total": len(emails)
            }
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Get unread emails error: {error}")
            return {"status": "error", "error_message": str(error)}

    def read_email(self, email_id: str) -> Dict[str, Any]:
        """Read specific email content"""
        try:
            debug_print(f"📖 DEBUG [Gmail]: Reading email {email_id}")
            
            msg = self.service.users().messages().get(userId="me", id=email_id, format='raw').execute()
            
            # Decode the base64URL encoded raw content
            raw_data = msg['raw']
            decoded_data = urlsafe_b64decode(raw_data)
            
            # Parse the RFC 2822 email
            mime_message = message_from_bytes(decoded_data)
            
            # Extract the email body
            body = None
            if mime_message.is_multipart():
                for part in mime_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = mime_message.get_payload(decode=True).decode()
            
            email_data = {
                "id": email_id,
                "subject": decode_mime_header(mime_message.get('subject', '')),
                "from": mime_message.get('from', ''),
                "to": mime_message.get('to', ''),
                "date": mime_message.get('date', ''),
                "content": body
            }
            
            debug_print(f"✅ DEBUG [Gmail]: Email read successfully")
            return email_data
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Read email error: {error}")
            return {"status": "error", "error_message": str(error)}

    def mark_email_as_read(self, email_id: str) -> Dict[str, Any]:
        """Mark email as read"""
        try:
            debug_print(f"✅ DEBUG [Gmail]: Marking email {email_id} as read")
            
            self.service.users().messages().modify(
                userId="me",
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return {"status": "success", "message": "Email marked as read"}
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Mark as read error: {error}")
            return {"status": "error", "error_message": str(error)}

    def trash_email(self, email_id: str) -> Dict[str, Any]:
        """Move email to trash"""
        try:
            debug_print(f"🗑️ DEBUG [Gmail]: Moving email {email_id} to trash")
            
            self.service.users().messages().trash(userId="me", id=email_id).execute()
            
            return {"status": "success", "message": "Email moved to trash"}
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Trash email error: {error}")
            return {"status": "error", "error_message": str(error)}

    def search_emails(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search emails with query"""
        try:
            debug_print(f"🔍 DEBUG [Gmail]: Searching emails with query: {query}")
            
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            debug_print(f"📊 DEBUG [Gmail]: Found {len(messages)} emails")
            
            emails = []
            for msg in messages:
                email_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in email_detail['payload']['headers']}
                
                emails.append({
                    "id": msg['id'],
                    "thread_id": email_detail['threadId'],
                    "from": headers.get('From', ''),
                    "subject": decode_mime_header(headers.get('Subject', '')),
                    "date": headers.get('Date', ''),
                    "snippet": email_detail.get('snippet', '')
                })
            
            return {
                "emails": emails,
                "total": len(emails),
                "query": query
            }
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Search emails error: {error}")
            return {"status": "error", "error_message": str(error)}

    def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            debug_print("👤 DEBUG [Gmail]: Getting user profile")
            
            profile = self.service.users().getProfile(userId='me').execute()
            
            return {
                "email_address": profile.get('emailAddress', ''),
                "messages_total": profile.get('messagesTotal', 0),
                "threads_total": profile.get('threadsTotal', 0),
                "history_id": profile.get('historyId', '')
            }
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [Gmail]: Get profile error: {error}")
            return {"status": "error", "error_message": str(error)}


def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        
        debug_print(f"🚀 DEBUG [Gmail]: Starting execution of action '{action}' with parameters: {parameters}")
        
        # Initialize Gmail service
        gmail_service = GmailService()
        
        # Execute action
        if action == "send_email":
            recipient = parameters.get("recipient")
            subject = parameters.get("subject")
            message = parameters.get("message")
            
            if not recipient or not subject or not message:
                raise ValueError("recipient, subject, and message parameters are required")
            
            result = gmail_service.send_email(recipient, subject, message)
            
        elif action == "get_unread_emails":
            max_results = parameters.get("max_results", 10)
            result = gmail_service.get_unread_emails(max_results)
            
        elif action == "read_email":
            email_id = parameters.get("email_id")
            if not email_id:
                raise ValueError("email_id parameter is required")
            result = gmail_service.read_email(email_id)
            
        elif action == "mark_email_as_read":
            email_id = parameters.get("email_id")
            if not email_id:
                raise ValueError("email_id parameter is required")
            result = gmail_service.mark_email_as_read(email_id)
            
        elif action == "trash_email":
            email_id = parameters.get("email_id")
            if not email_id:
                raise ValueError("email_id parameter is required")
            result = gmail_service.trash_email(email_id)
            
        elif action == "search_emails":
            query = parameters.get("query")
            if not query:
                raise ValueError("query parameter is required")
            max_results = parameters.get("max_results", 10)
            result = gmail_service.search_emails(query, max_results)
            
        elif action == "get_user_profile":
            result = gmail_service.get_user_profile()
            
        else:
            raise ValueError(f"Unknown action: {action}")
        
        debug_print(f"🎉 DEBUG [Gmail]: Action '{action}' completed successfully")
        
        # Return result (to stdout)
        print(json.dumps(result))
        
    except Exception as e:
        debug_print(f"💥 DEBUG [Gmail]: Action failed with error: {str(e)}")
        debug_print(f"🔍 DEBUG [Gmail]: Error type: {type(e).__name__}")
        
        # Return error (to stdout)
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
