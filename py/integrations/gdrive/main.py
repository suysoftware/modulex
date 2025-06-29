#!/usr/bin/env python3
"""
Google Drive Integration - Main Script
"""
import json
import sys
import os
import io
from typing import Dict, Any, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


def debug_print(message: str):
    """Print debug messages to stderr to avoid interfering with JSON output"""
    print(message, file=sys.stderr)


class GoogleDriveService:
    def __init__(self):
        self.client_id = os.getenv("GDRIVE_CLIENT_ID")
        self.client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        
        if not self.client_id:
            raise ValueError("GDRIVE_CLIENT_ID environment variable not set")
        if not self.client_secret:
            raise ValueError("GDRIVE_CLIENT_SECRET environment variable not set")
        if not self.access_token:
            raise ValueError("ACCESS_TOKEN environment variable not set")
        
        debug_print(f"🔑 DEBUG [GDrive]: Client ID: {self.client_id[:20]}...")
        debug_print(f"🔑 DEBUG [GDrive]: Client Secret: {'*' * len(self.client_secret)}")
        debug_print(f"🔑 DEBUG [GDrive]: Access Token: {self.access_token[:20]}...")
        
        self.credentials = self._create_credentials()
        self.service = self._get_service()
        
        debug_print("✅ DEBUG [GDrive]: Service initialized successfully")

    def _create_credentials(self) -> Credentials:
        """Create credentials from access token"""
        debug_print('🔑 DEBUG [GDrive]: Creating credentials from access token')
        
        # Create credentials object from access token
        credentials = Credentials(
            token=self.access_token,
            scopes=self.scopes
        )
        
        debug_print('✅ DEBUG [GDrive]: Credentials created successfully')
        return credentials

    def _get_service(self):
        """Initialize Google Drive API service"""
        try:
            service = build('drive', 'v3', credentials=self.credentials)
            return service
        except HttpError as error:
            debug_print(f'❌ DEBUG [GDrive]: Error building Drive service: {error}')
            raise ValueError(f'Google Drive service error: {error}')

    def search_files(self, query: str, page_size: int = 10) -> Dict[str, Any]:
        """Search for files in Google Drive"""
        try:
            debug_print(f"🔍 DEBUG [GDrive]: Searching files with query: {query}")
            
            results = self.service.files().list(
                q=f"name contains '{query}'",
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, size, modifiedTime, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            debug_print(f"📊 DEBUG [GDrive]: Found {len(files)} files")
            
            formatted_files = []
            for file in files:
                formatted_file = {
                    "id": file['id'],
                    "name": file['name'],
                    "mime_type": file['mimeType'],
                    "web_view_link": file.get('webViewLink', ''),
                    "size": file.get('size', 'N/A'),
                    "modified_time": file.get('modifiedTime', ''),
                    "created_time": file.get('createdTime', '')
                }
                formatted_files.append(formatted_file)

            return {
                "files": formatted_files,
                "total": len(formatted_files),
                "next_page_token": results.get('nextPageToken')
            }
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Search files error: {error}")
            return {"status": "error", "error_message": str(error)}

    def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file content and metadata"""
        try:
            debug_print(f"📄 DEBUG [GDrive]: Getting file {file_id}")
            
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, webViewLink, size, modifiedTime, createdTime, description"
            ).execute()
            
            # Get file content
            try:
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                # Try to decode as UTF-8 text
                try:
                    content = fh.getvalue().decode('utf-8')
                except UnicodeDecodeError:
                    # If it's not text, provide info about binary content
                    content = f"Binary file ({len(fh.getvalue())} bytes)"
                
            except HttpError as e:
                # Some files might not be downloadable (e.g., Google Docs)
                content = f"Content not directly downloadable: {str(e)}"
            
            result = {
                "metadata": {
                    "id": file_metadata['id'],
                    "name": file_metadata['name'],
                    "mime_type": file_metadata['mimeType'],
                    "web_view_link": file_metadata.get('webViewLink', ''),
                    "size": file_metadata.get('size', 'N/A'),
                    "modified_time": file_metadata.get('modifiedTime', ''),
                    "created_time": file_metadata.get('createdTime', ''),
                    "description": file_metadata.get('description', '')
                },
                "content": content
            }
            
            debug_print("✅ DEBUG [GDrive]: File retrieved successfully")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Get file error: {error}")
            return {"status": "error", "error_message": str(error)}

    def list_files(self, folder_id: Optional[str] = None, page_size: int = 10, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """List files in Google Drive with optional filters"""
        try:
            debug_print(f"📋 DEBUG [GDrive]: Listing files (folder_id: {folder_id}, mime_type: {mime_type})")
            
            # Build query
            query_parts = []
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            if mime_type:
                query_parts.append(f"mimeType='{mime_type}'")
            
            query = " and ".join(query_parts) if query_parts else None
            
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, size, modifiedTime, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            debug_print(f"📊 DEBUG [GDrive]: Found {len(files)} files")
            
            formatted_files = []
            for file in files:
                formatted_file = {
                    "id": file['id'],
                    "name": file['name'],
                    "mime_type": file['mimeType'],
                    "web_view_link": file.get('webViewLink', ''),
                    "size": file.get('size', 'N/A'),
                    "modified_time": file.get('modifiedTime', ''),
                    "created_time": file.get('createdTime', '')
                }
                formatted_files.append(formatted_file)

            return {
                "files": formatted_files,
                "total": len(formatted_files),
                "next_page_token": results.get('nextPageToken')
            }
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: List files error: {error}")
            return {"status": "error", "error_message": str(error)}

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get detailed metadata for a specific file"""
        try:
            debug_print(f"📊 DEBUG [GDrive]: Getting metadata for file {file_id}")
            
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="*"
            ).execute()
            
            debug_print("✅ DEBUG [GDrive]: File metadata retrieved successfully")
            return {
                "metadata": file_metadata
            }
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Get file metadata error: {error}")
            return {"status": "error", "error_message": str(error)}

    def download_file(self, file_id: str) -> Dict[str, Any]:
        """Download file content as text or binary data"""
        try:
            debug_print(f"💾 DEBUG [GDrive]: Downloading file {file_id}")
            
            # First get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size"
            ).execute()
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content = fh.getvalue()
            
            # Try to decode as text if it's a text file
            content_type = "binary"
            content = None
            
            if file_metadata['mimeType'].startswith('text/') or file_metadata['mimeType'] in [
                'application/json', 'application/xml', 'application/javascript'
            ]:
                try:
                    content = file_content.decode('utf-8')
                    content_type = "text"
                except UnicodeDecodeError:
                    content = f"Binary content ({len(file_content)} bytes)"
            else:
                content = f"Binary content ({len(file_content)} bytes)"
            
            result = {
                "file_info": {
                    "id": file_metadata['id'],
                    "name": file_metadata['name'],
                    "mime_type": file_metadata['mimeType'],
                    "size": file_metadata.get('size', 'N/A')
                },
                "content_type": content_type,
                "content": content,
                "size_bytes": len(file_content)
            }
            
            debug_print("✅ DEBUG [GDrive]: File downloaded successfully")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Download file error: {error}")
            return {"status": "error", "error_message": str(error)}


def main():
    """Main function to handle incoming requests"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        action = input_data.get("action")
        params = input_data.get("params", {})
        
        debug_print(f"🚀 DEBUG [GDrive]: Executing action: {action}")
        debug_print(f"📋 DEBUG [GDrive]: Parameters: {params}")
        
        # Initialize the service
        gdrive_service = GoogleDriveService()
        
        # Execute the requested action
        if action == "search_files":
            result = gdrive_service.search_files(
                query=params.get("query"),
                page_size=params.get("page_size", 10)
            )
        elif action == "get_file":
            result = gdrive_service.get_file(
                file_id=params.get("file_id")
            )
        elif action == "list_files":
            result = gdrive_service.list_files(
                folder_id=params.get("folder_id"),
                page_size=params.get("page_size", 10),
                mime_type=params.get("mime_type")
            )
        elif action == "get_file_metadata":
            result = gdrive_service.get_file_metadata(
                file_id=params.get("file_id")
            )
        elif action == "download_file":
            result = gdrive_service.download_file(
                file_id=params.get("file_id")
            )
        else:
            result = {"status": "error", "error_message": f"Unknown action: {action}"}
        
        # Output the result as JSON
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        debug_print(f"❌ DEBUG [GDrive]: Critical error: {str(e)}")
        error_result = {"status": "error", "error_message": str(e)}
        print(json.dumps(error_result, indent=2))


if __name__ == "__main__":
    main()
