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
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/presentations'
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
        self.slides_service = self._get_slides_service()
        
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

    def _get_slides_service(self):
        """Initialize Google Slides API service"""
        try:
            service = build('slides', 'v1', credentials=self.credentials)
            return service
        except HttpError as error:
            debug_print(f'❌ DEBUG [GDrive]: Error building Slides service: {error}')
            raise ValueError(f'Google Slides service error: {error}')

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

    def create_spreadsheet(self, title: str, data: Optional[List[List]] = None, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Google Sheets spreadsheet with optional data"""
        try:
            debug_print(f"📊 DEBUG [GDrive]: Creating spreadsheet: {title}")
            debug_print(f"📊 DEBUG [GDrive]: Data provided: {bool(data)}")
            if data:
                debug_print(f"📊 DEBUG [GDrive]: Data rows: {len(data)}")
            
            # Check if spreadsheet with same name already exists
            debug_print(f"🔍 DEBUG [GDrive]: Checking for existing spreadsheet with name: {title}")
            search_query = f"name='{title}' and mimeType='application/vnd.google-apps.spreadsheet'"
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
            
            existing_files = self.service.files().list(
                q=search_query,
                pageSize=1,
                fields="files(id, name, webViewLink, createdTime)"
            ).execute()
            
            if existing_files.get('files'):
                existing_file = existing_files['files'][0]
                debug_print(f"⚠️ DEBUG [GDrive]: Spreadsheet already exists, returning existing one")
                
                # Add data to existing spreadsheet if provided
                data_added = False
                if data and len(data) > 0:
                    try:
                        debug_print(f"📊 DEBUG [GDrive]: Adding data to existing spreadsheet")
                        
                        # Convert all values to strings for existing spreadsheet too
                        converted_data = []
                        for row in data:
                            converted_row = [str(cell) for cell in row]
                            converted_data.append(converted_row)
                        
                        body = {'values': converted_data}
                        result = self.sheets_service.spreadsheets().values().update(
                            spreadsheetId=existing_file['id'],
                            range='A1',
                            valueInputOption='RAW',
                            body=body
                        ).execute()
                        debug_print(f"✅ DEBUG [GDrive]: Data added to existing spreadsheet: {result.get('updatedCells', 0)} cells updated")
                        data_added = True
                    except Exception as e:
                        debug_print(f"❌ DEBUG [GDrive]: Failed to add data to existing: {e}")
                
                return {
                    "status": "success",
                    "spreadsheet": {
                        "id": existing_file['id'],
                        "name": existing_file['name'],
                        "mime_type": 'application/vnd.google-apps.spreadsheet',
                        "web_view_link": existing_file.get('webViewLink', ''),
                        "created_time": existing_file.get('createdTime', ''),
                        "data_added": data_added,
                        "rows_added": len(data) if data else 0,
                        "note": "Used existing spreadsheet with same name"
                    }
                }
            
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
            spreadsheet_id = spreadsheet['id']
            
            debug_print(f"📊 DEBUG [GDrive]: Spreadsheet created with ID: {spreadsheet_id}")
            
            # Add data to the spreadsheet if provided
            data_added = False
            if data and len(data) > 0:
                try:
                    debug_print(f"📊 DEBUG [GDrive]: Adding data to spreadsheet")
                    
                    # Prepare the data for Sheets API - ensure all values are strings
                    debug_print(f"📊 DEBUG [GDrive]: Data sample before conversion: {data[:2] if len(data) > 1 else data}")
                    
                    # Convert all values to strings
                    converted_data = []
                    for row in data:
                        converted_row = [str(cell) for cell in row]
                        converted_data.append(converted_row)
                    
                    debug_print(f"📊 DEBUG [GDrive]: Data sample after string conversion: {converted_data[:2] if len(converted_data) > 1 else converted_data}")
                    
                    body = {
                        'values': converted_data
                    }
                    debug_print(f"📊 DEBUG [GDrive]: Body prepared for Sheets API with {len(converted_data)} rows")
                    
                    # Update the spreadsheet with data
                    range_name = 'A1'  # Simple range without sheet name
                    debug_print(f"📊 DEBUG [GDrive]: Using range: {range_name}")
                    
                    result = self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    debug_print(f"✅ DEBUG [GDrive]: Data added successfully: {result.get('updatedCells', 0)} cells updated")
                    data_added = True
                    
                except Exception as e:
                    debug_print(f"❌ DEBUG [GDrive]: Failed to add data: {e}")
                    data_added = False
            
            # Get the created spreadsheet details
            created_sheet = self.service.files().get(
                fileId=spreadsheet_id,
                fields="id, name, mimeType, webViewLink, createdTime"
            ).execute()
            
            result = {
                "status": "success",
                "spreadsheet": {
                    "id": created_sheet['id'],
                    "name": created_sheet['name'],
                    "mime_type": created_sheet['mimeType'],
                    "web_view_link": created_sheet.get('webViewLink', ''),
                    "created_time": created_sheet.get('createdTime', ''),
                    "data_added": data_added,
                    "rows_added": len(data) if data else 0
                }
            }
            
            debug_print("✅ DEBUG [GDrive]: Spreadsheet creation completed")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Create spreadsheet error: {error}")
            return {"status": "error", "error_message": str(error)}

    def create_presentation(self, title: str, slides_data: Optional[List[Dict]] = None, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Google Slides presentation with optional slides content"""
        try:
            debug_print(f"🎯 DEBUG [GDrive]: Creating presentation: {title}")
            debug_print(f"🎯 DEBUG [GDrive]: Slides data provided: {bool(slides_data)}")
            if slides_data:
                debug_print(f"🎯 DEBUG [GDrive]: Number of slides: {len(slides_data)}")
            
            # Check if presentation with same name already exists
            debug_print(f"🔍 DEBUG [GDrive]: Checking for existing presentation with name: {title}")
            search_query = f"name='{title}' and mimeType='application/vnd.google-apps.presentation'"
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
            
            existing_files = self.service.files().list(
                q=search_query,
                pageSize=1,
                fields="files(id, name, webViewLink, createdTime)"
            ).execute()
            
            if existing_files.get('files'):
                existing_file = existing_files['files'][0]
                debug_print(f"⚠️ DEBUG [GDrive]: Presentation already exists, returning existing one")
                
                return {
                    "status": "success",
                    "presentation": {
                        "id": existing_file['id'],
                        "name": existing_file['name'],
                        "mime_type": 'application/vnd.google-apps.presentation',
                        "web_view_link": existing_file.get('webViewLink', ''),
                        "created_time": existing_file.get('createdTime', ''),
                        "slides_added": False,
                        "note": "Used existing presentation with same name"
                    }
                }
            
            # Create the presentation using Slides API
            presentation_body = {
                'title': title
            }
            
            # Create presentation via Slides API to get better access
            presentation = self.slides_service.presentations().create(body=presentation_body).execute()
            presentation_id = presentation['presentationId']
            
            debug_print(f"🎯 DEBUG [GDrive]: Presentation created with ID: {presentation_id}")
            
            # Move to specific folder if provided
            if folder_id:
                self.service.files().update(
                    fileId=presentation_id,
                    addParents=folder_id,
                    fields='id, parents'
                ).execute()
            
            # Add slides content if provided
            slides_added = False
            if slides_data and len(slides_data) > 0:
                try:
                    debug_print(f"🎯 DEBUG [GDrive]: Adding slides content")
                    slides_added = self._add_slides_content(presentation_id, slides_data)
                except Exception as e:
                    debug_print(f"❌ DEBUG [GDrive]: Failed to add slides content: {e}")
            
            # Get the created presentation details
            created_presentation = self.service.files().get(
                fileId=presentation_id,
                fields="id, name, mimeType, webViewLink, createdTime"
            ).execute()
            
            result = {
                "status": "success",
                "presentation": {
                    "id": created_presentation['id'],
                    "name": created_presentation['name'],
                    "mime_type": created_presentation['mimeType'],
                    "web_view_link": created_presentation.get('webViewLink', ''),
                    "created_time": created_presentation.get('createdTime', ''),
                    "slides_added": slides_added,
                    "slides_count": len(slides_data) if slides_data else 0
                }
            }
            
            debug_print("✅ DEBUG [GDrive]: Presentation creation completed")
            return result
            
        except HttpError as error:
            debug_print(f"❌ DEBUG [GDrive]: Create presentation error: {error}")
            return {"status": "error", "error_message": str(error)}

    def _add_slides_content(self, presentation_id: str, slides_data: List[Dict]) -> bool:
        """Add content to slides in the presentation"""
        try:
            debug_print(f"🎯 DEBUG [GDrive]: Adding content to {len(slides_data)} slides")
            
            # Get current presentation to find existing slide
            presentation = self.slides_service.presentations().get(presentationId=presentation_id).execute()
            existing_slides = presentation.get('slides', [])
            debug_print(f"🎯 DEBUG [GDrive]: Found {len(existing_slides)} existing slides")
            
            # First, set the layout of the first slide to TITLE_AND_BODY if it's not already
            if existing_slides:
                first_slide_id = existing_slides[0]['objectId']
                debug_print(f"🎯 DEBUG [GDrive]: First slide ID: {first_slide_id}")
                
                # Update first slide layout to ensure it has title and body placeholders
                layout_request = [{
                    'updateSlideProperties': {
                        'objectId': first_slide_id,
                        'slideProperties': {
                            'layoutObjectId': presentation['layouts'][1]['objectId']  # TITLE_AND_BODY layout
                        },
                        'fields': 'layoutObjectId'
                    }
                }]
                
                try:
                    self.slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': layout_request}
                    ).execute()
                    debug_print(f"🎯 DEBUG [GDrive]: Updated first slide layout")
                except Exception as e:
                    debug_print(f"⚠️ DEBUG [GDrive]: Could not update first slide layout: {e}")
            
            # Create additional slides if needed (we have one slide already)
            new_slide_requests = []
            slides_needed = len(slides_data)
            slides_to_create = max(0, slides_needed - len(existing_slides))
            
            debug_print(f"🎯 DEBUG [GDrive]: Need {slides_needed} slides, have {len(existing_slides)}, creating {slides_to_create}")
            
            for i in range(slides_to_create):
                new_slide_requests.append({
                    'createSlide': {
                        'slideLayoutReference': {
                            'predefinedLayout': 'TITLE_AND_BODY'
                        }
                    }
                })
            
            # Execute slide creation requests
            if new_slide_requests:
                debug_print(f"🎯 DEBUG [GDrive]: Creating {len(new_slide_requests)} new slides")
                self.slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': new_slide_requests}
                ).execute()
            
            # Get updated presentation with all slides
            presentation = self.slides_service.presentations().get(presentationId=presentation_id).execute()
            slides = presentation.get('slides', [])
            debug_print(f"🎯 DEBUG [GDrive]: Now have {len(slides)} total slides")
            
            # Add content to each slide
            text_requests = []
            for i, slide_data in enumerate(slides_data):
                if i >= len(slides):
                    debug_print(f"⚠️ DEBUG [GDrive]: Skipping slide {i+1}, not enough slides available")
                    break
                    
                slide_id = slides[i]['objectId']
                slide_title = slide_data.get('title', f'Slide {i+1}')
                slide_content = slide_data.get('content', '')
                
                debug_print(f"🎯 DEBUG [GDrive]: Processing slide {i+1}: '{slide_title}' (ID: {slide_id})")
                
                # Find title and body placeholders in current slide
                slide_elements = slides[i].get('pageElements', [])
                title_placeholder = None
                body_placeholder = None
                
                debug_print(f"🎯 DEBUG [GDrive]: Slide {i+1} has {len(slide_elements)} elements")
                
                for element in slide_elements:
                    if element.get('shape') and element['shape'].get('placeholder'):
                        placeholder_type = element['shape']['placeholder'].get('type')
                        element_id = element['objectId']
                        debug_print(f"🎯 DEBUG [GDrive]: Found placeholder type '{placeholder_type}' with ID: {element_id}")
                        
                        if placeholder_type == 'TITLE':
                            title_placeholder = element_id
                        elif placeholder_type == 'BODY':
                            body_placeholder = element_id
                
                debug_print(f"🎯 DEBUG [GDrive]: Slide {i+1} - Title placeholder: {title_placeholder}, Body placeholder: {body_placeholder}")
                
                # Clear and add title text
                if title_placeholder and slide_title:
                    # First delete any existing text (placeholder text)
                    text_requests.append({
                        'deleteText': {
                            'objectId': title_placeholder,
                            'textRange': {
                                'type': 'ALL'
                            }
                        }
                    })
                    # Then insert new text
                    text_requests.append({
                        'insertText': {
                            'objectId': title_placeholder,
                            'text': slide_title
                        }
                    })
                    debug_print(f"🎯 DEBUG [GDrive]: Added title clear+insert requests for slide {i+1}")
                
                # Clear and add body text  
                if body_placeholder and slide_content:
                    # First delete any existing text (placeholder text)
                    text_requests.append({
                        'deleteText': {
                            'objectId': body_placeholder,
                            'textRange': {
                                'type': 'ALL'
                            }
                        }
                    })
                    # Then insert new text
                    text_requests.append({
                        'insertText': {
                            'objectId': body_placeholder,
                            'text': slide_content
                        }
                    })
                    debug_print(f"🎯 DEBUG [GDrive]: Added body clear+insert requests for slide {i+1}")
                
                # If no placeholders found, create text boxes manually
                if not title_placeholder and not body_placeholder:
                    debug_print(f"⚠️ DEBUG [GDrive]: No placeholders found for slide {i+1}, creating manual text boxes")
                    
                    # Create title text box
                    if slide_title:
                        title_box_id = f"title_box_{i}"
                        text_requests.extend([
                            {
                                'createShape': {
                                    'objectId': title_box_id,
                                    'shapeType': 'TEXT_BOX',
                                    'elementProperties': {
                                        'pageObjectId': slide_id,
                                        'size': {
                                            'width': {'magnitude': 720, 'unit': 'PT'},
                                            'height': {'magnitude': 100, 'unit': 'PT'}
                                        },
                                        'transform': {
                                            'scaleX': 1,
                                            'scaleY': 1,
                                            'translateX': 50,
                                            'translateY': 50,
                                            'unit': 'PT'
                                        }
                                    }
                                }
                            },
                            {
                                'insertText': {
                                    'objectId': title_box_id,
                                    'text': slide_title
                                }
                            }
                        ])
                    
                    # Create body text box
                    if slide_content:
                        body_box_id = f"body_box_{i}"
                        text_requests.extend([
                            {
                                'createShape': {
                                    'objectId': body_box_id,
                                    'shapeType': 'TEXT_BOX',
                                    'elementProperties': {
                                        'pageObjectId': slide_id,
                                        'size': {
                                            'width': {'magnitude': 720, 'unit': 'PT'},
                                            'height': {'magnitude': 400, 'unit': 'PT'}
                                        },
                                        'transform': {
                                            'scaleX': 1,
                                            'scaleY': 1,
                                            'translateX': 50,
                                            'translateY': 180,
                                            'unit': 'PT'
                                        }
                                    }
                                }
                            },
                            {
                                'insertText': {
                                    'objectId': body_box_id,
                                    'text': slide_content
                                }
                            }
                        ])
            
            # Execute all text insertion requests
            if text_requests:
                debug_print(f"🎯 DEBUG [GDrive]: Executing {len(text_requests)} text requests")
                self.slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': text_requests}
                ).execute()
                debug_print(f"✅ DEBUG [GDrive]: Successfully added all text content")
            else:
                debug_print(f"⚠️ DEBUG [GDrive]: No text requests to execute")
            
            debug_print(f"✅ DEBUG [GDrive]: Successfully processed {len(slides_data)} slides")
            return True
            
        except Exception as e:
            debug_print(f"❌ DEBUG [GDrive]: Error adding slides content: {e}")
            import traceback
            debug_print(f"❌ DEBUG [GDrive]: Full traceback: {traceback.format_exc()}")
            return False

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
            # Parse data from JSON string if provided
            data = params.get("data")
            debug_print(f"📊 DEBUG [GDrive]: Raw data parameter: {data} (type: {type(data)})")
            
            if data and isinstance(data, str):
                try:
                    data = json.loads(data)
                    debug_print(f"✅ DEBUG [GDrive]: Data parsed successfully: {len(data) if data else 0} rows")
                except json.JSONDecodeError as e:
                    debug_print(f"❌ DEBUG [GDrive]: JSON decode error: {e}")
                    data = None
            elif data and isinstance(data, list):
                debug_print(f"✅ DEBUG [GDrive]: Data already a list: {len(data)} rows")
            else:
                debug_print(f"📊 DEBUG [GDrive]: No data provided or invalid format")
            
            result = gdrive_service.create_spreadsheet(
                title=params.get("title"),
                data=data,
                folder_id=params.get("folder_id")
            )
        elif action == "create_presentation":
            # Parse slides data from JSON string if provided
            slides_data = params.get("slides_data")
            debug_print(f"🎯 DEBUG [GDrive]: Raw slides_data parameter: {slides_data} (type: {type(slides_data)})")
            
            if slides_data and isinstance(slides_data, str):
                try:
                    slides_data = json.loads(slides_data)
                    debug_print(f"✅ DEBUG [GDrive]: Slides data parsed successfully: {len(slides_data) if slides_data else 0} slides")
                except json.JSONDecodeError as e:
                    debug_print(f"❌ DEBUG [GDrive]: JSON decode error for slides: {e}")
                    slides_data = None
            elif slides_data and isinstance(slides_data, list):
                debug_print(f"✅ DEBUG [GDrive]: Slides data already a list: {len(slides_data)} slides")
            else:
                debug_print(f"🎯 DEBUG [GDrive]: No slides data provided or invalid format")
            
            result = gdrive_service.create_presentation(
                title=params.get("title"),
                slides_data=slides_data,
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
