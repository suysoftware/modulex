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
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


def debug_print(message: str):
    """Print debug messages to both stderr and stdout for visibility"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message, file=sys.stderr, flush=True)
    # Also print to stdout with a prefix so it's visible in docker logs
    print(f"GDRIVE_DEBUG: {formatted_message}", flush=True)


class GoogleDriveService:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.scopes = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/docs',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        if not self.client_id:
            raise ValueError("GOOGLE_CLIENT_ID environment variable not set")
        if not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_SECRET environment variable not set")
        if not self.access_token:
            raise ValueError("ACCESS_TOKEN environment variable not set")
        
        debug_print(f"🔑 DEBUG [GDrive]: Client ID: {self.client_id[:20]}...")
        debug_print(f"🔑 DEBUG [GDrive]: Client Secret: {'*' * len(self.client_secret)}")
        debug_print(f"🔑 DEBUG [GDrive]: Access Token: {self.access_token[:20]}...")
        
        self.credentials = self._create_credentials()
        self.service = self._get_service()
        self.docs_service = self._get_docs_service()
        self.sheets_service = self._get_sheets_service()
        
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

    def _get_docs_service(self):
        """Initialize Google Docs API service"""
        try:
            service = build('docs', 'v1', credentials=self.credentials)
            return service
        except HttpError as error:
            debug_print(f'❌ DEBUG [GDrive]: Error building Docs service: {error}')
            raise ValueError(f'Google Docs service error: {error}')

    def _get_sheets_service(self):
        """Initialize Google Sheets API service"""
        try:
            service = build('sheets', 'v4', credentials=self.credentials)
            return service
        except HttpError as error:
            debug_print(f'❌ DEBUG [GDrive]: Error building Sheets service: {error}')
            raise ValueError(f'Google Sheets service error: {error}')

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

    def create_document(self, title: str, content: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Google Docs document with content"""
        try:
            debug_print(f"📝 DEBUG [GDrive]: Creating document with title: '{title}'")
            debug_print(f"📝 DEBUG [GDrive]: Content length: {len(content) if content else 0}")
            
            # Create the document metadata with explicit name
            file_metadata = {
                'name': title if title else 'Untitled Document',
                'mimeType': 'application/vnd.google-apps.document'
            }
            
            # Add to specific folder if provided
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            debug_print(f"🔍 DEBUG [GDrive]: File metadata: {json.dumps(file_metadata, indent=2)}")
            
            # Create the document
            doc = self.service.files().create(
                body=file_metadata,
                fields='id,name,mimeType,webViewLink'
            ).execute()
            
            document_id = doc.get('id')
            debug_print(f"📄 DEBUG [GDrive]: Document created with ID: {document_id}")
            debug_print(f"📄 DEBUG [GDrive]: Document name from API: {doc.get('name')}")
            
            # Add content to the document using Google Docs API
            content_added = False
            if content and content.strip():
                try:
                    debug_print(f"📝 DEBUG [GDrive]: Attempting to add content to document {document_id}")
                    debug_print(f"📝 DEBUG [GDrive]: Content preview: {content[:100]}...")
                    
                    # Wait a moment for document to be ready
                    import time
                    time.sleep(0.5)
                    
                    # Simple approach - insert at beginning
                    requests = [
                        {
                            'insertText': {
                                'location': {
                                    'index': 1,
                                },
                                'text': content
                            }
                        }
                    ]
                    
                    debug_print(f"🔍 DEBUG [GDrive]: Inserting text at index 1")
                    
                    result = self.docs_service.documents().batchUpdate(
                        documentId=document_id,
                        body={'requests': requests}
                    ).execute()
                    
                    debug_print("✅ DEBUG [GDrive]: Content added successfully")
                    debug_print(f"🔍 DEBUG [GDrive]: Batch update result: {result}")
                    content_added = True
                    
                except Exception as e:
                    debug_print(f"❌ DEBUG [GDrive]: Content addition failed: {e}")
                    debug_print(f"🔍 DEBUG [GDrive]: Error details: {str(e)}")
                    
                    # Alternative approach - try with different index
                    try:
                        debug_print("🔄 DEBUG [GDrive]: Trying alternative approach...")
                        
                        # Get document structure first
                        current_doc = self.docs_service.documents().get(documentId=document_id).execute()
                        debug_print(f"📄 DEBUG [GDrive]: Document title from Docs API: {current_doc.get('title', 'No title')}")
                        
                        # Try inserting at the very beginning
                        alt_requests = [
                            {
                                'insertText': {
                                    'location': {
                                        'index': 1,
                                    },
                                    'text': content + '\n'
                                }
                            }
                        ]
                        
                        alt_result = self.docs_service.documents().batchUpdate(
                            documentId=document_id,
                            body={'requests': alt_requests}
                        ).execute()
                        
                        debug_print("✅ DEBUG [GDrive]: Alternative content insertion successful")
                        content_added = True
                        
                    except Exception as alt_e:
                        debug_print(f"❌ DEBUG [GDrive]: Alternative approach also failed: {alt_e}")
                        content_added = False
            
            # Get the final document details
            final_doc = self.service.files().get(
                fileId=document_id,
                fields="id, name, mimeType, webViewLink, createdTime"
            ).execute()
            
            debug_print(f"📄 DEBUG [GDrive]: Final document name: {final_doc.get('name')}")
            
            result = {
                "status": "success",
                "document": {
                    "id": final_doc['id'],
                    "name": final_doc['name'],
                    "mime_type": final_doc['mimeType'],
                    "web_view_link": final_doc.get('webViewLink', ''),
                    "created_time": final_doc.get('createdTime', ''),
                    "content_added": content_added,
                    "requested_title": title
                }
            }
            
            debug_print("✅ DEBUG [GDrive]: Document creation completed")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Create document error: {error}")
            return {"status": "error", "error_message": str(error)}

    def create_spreadsheet(self, title: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Google Sheets spreadsheet"""
        try:
            debug_print(f"📊 DEBUG [GDrive]: Creating spreadsheet: {title}")
            
            # Create the spreadsheet metadata
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            
            # Add to specific folder if provided
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create the spreadsheet
            spreadsheet = self.service.files().create(body=file_metadata).execute()
            
            # Get the created spreadsheet details
            created_sheet = self.service.files().get(
                fileId=spreadsheet['id'],
                fields="id, name, mimeType, webViewLink, createdTime"
            ).execute()
            
            result = {
                "status": "success",
                "spreadsheet": {
                    "id": created_sheet['id'],
                    "name": created_sheet['name'],
                    "mime_type": created_sheet['mimeType'],
                    "web_view_link": created_sheet.get('webViewLink', ''),
                    "created_time": created_sheet.get('createdTime', '')
                }
            }
            
            debug_print("✅ DEBUG [GDrive]: Spreadsheet created successfully")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Create spreadsheet error: {error}")
            return {"status": "error", "error_message": str(error)}

    def create_presentation(self, title: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Google Slides presentation"""
        try:
            debug_print(f"🎯 DEBUG [GDrive]: Creating presentation: {title}")
            
            # Create the presentation metadata
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.presentation'
            }
            
            # Add to specific folder if provided
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create the presentation
            presentation = self.service.files().create(body=file_metadata).execute()
            
            # Get the created presentation details
            created_presentation = self.service.files().get(
                fileId=presentation['id'],
                fields="id, name, mimeType, webViewLink, createdTime"
            ).execute()
            
            result = {
                "status": "success",
                "presentation": {
                    "id": created_presentation['id'],
                    "name": created_presentation['name'],
                    "mime_type": created_presentation['mimeType'],
                    "web_view_link": created_presentation.get('webViewLink', ''),
                    "created_time": created_presentation.get('createdTime', '')
                }
            }
            
            debug_print("✅ DEBUG [GDrive]: Presentation created successfully")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Create presentation error: {error}")
            return {"status": "error", "error_message": str(error)}

    def create_text_file(self, title: str, content: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new plain text file"""
        try:
            debug_print(f"📄 DEBUG [GDrive]: Creating text file: {title}")
            
            # Create the file metadata
            file_metadata = {
                'name': title,
                'mimeType': 'text/plain'
            }
            
            # Add to specific folder if provided
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create media upload with content
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/plain',
                resumable=True
            )
            
            # Create the file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # Get the created file details
            created_file = self.service.files().get(
                fileId=file['id'],
                fields="id, name, mimeType, webViewLink, createdTime, size"
            ).execute()
            
            result = {
                "status": "success",
                "file": {
                    "id": created_file['id'],
                    "name": created_file['name'],
                    "mime_type": created_file['mimeType'],
                    "web_view_link": created_file.get('webViewLink', ''),
                    "created_time": created_file.get('createdTime', ''),
                    "size": created_file.get('size', 'N/A')
                }
            }
            
            debug_print("✅ DEBUG [GDrive]: Text file created successfully")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Create text file error: {error}")
            return {"status": "error", "error_message": str(error)}


def main():
    """Main function to handle incoming requests"""
    try:
        # Read input from stdin
        raw_input = sys.stdin.read()
        debug_print(f"📥 DEBUG [GDrive]: Raw input received: {raw_input}")
        
        input_data = json.loads(raw_input)
        action = input_data.get("action")
        params = input_data.get("params", {})
        
        # Try both "params" and "parameters" for compatibility
        if not params:
            params = input_data.get("parameters", {})
        
        debug_print(f"🚀 DEBUG [GDrive]: Executing action: {action}")
        debug_print(f"📋 DEBUG [GDrive]: Full input data: {input_data}")
        debug_print(f"📋 DEBUG [GDrive]: Parameters: {params}")
        
        # Log specific parameters for create_document
        if action == "create_document":
            title = params.get("title")
            content = params.get("content")
            debug_print(f"📄 DEBUG [GDrive]: Title parameter: '{title}' (type: {type(title)})")
            debug_print(f"📄 DEBUG [GDrive]: Content parameter length: {len(content) if content else 0}")
        
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
        elif action == "create_document":
            result = gdrive_service.create_document(
                title=params.get("title"),
                content=params.get("content"),
                folder_id=params.get("folder_id")
            )
        elif action == "create_spreadsheet":
            result = gdrive_service.create_spreadsheet(
                title=params.get("title"),
                folder_id=params.get("folder_id")
            )
        elif action == "create_presentation":
            result = gdrive_service.create_presentation(
                title=params.get("title"),
                folder_id=params.get("folder_id")
            )
        elif action == "create_text_file":
            result = gdrive_service.create_text_file(
                title=params.get("title"),
                content=params.get("content"),
                folder_id=params.get("folder_id")
            )
        else:
            result = {"status": "error", "error_message": f"Unknown action: {action}"}
        
        # Output the result as JSON (separate from debug messages)
        debug_print(f"📤 DEBUG [GDrive]: Sending result: {result}")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        debug_print(f"❌ DEBUG [GDrive]: Critical error: {str(e)}")
        error_result = {"status": "error", "error_message": str(e)}
        print(json.dumps(error_result, indent=2))


if __name__ == "__main__":
    main()
