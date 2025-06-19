#!/usr/bin/env python3
"""
R2R Integration - Main Script
"""
import json
import sys
import os
from typing import Dict, Any, Optional


def get_r2r_credentials(user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Get R2R credentials from user data or environment."""
    # Priority: user_credentials > environment variables
    if user_credentials and user_credentials.get("auth_type") == "manual":
        # Use user-specific credentials from database
        return {
            "base_url": user_credentials.get("base_url") or os.getenv("R2R_BASE_URL"),
            "api_key": None,  # Not used in manual auth
            "email": user_credentials.get("email"),
            "password": user_credentials.get("password")
        }
    else:
        # Fallback to environment variables (backward compatibility)
        base_url = os.getenv("R2R_BASE_URL") 
        api_key = os.getenv("R2R_API_KEY")
        email = os.getenv("R2R_EMAIL")
        password = os.getenv("R2R_PASSWORD")
        
        return {
            "base_url": base_url,
            "api_key": api_key,
            "email": email,
            "password": password
        }


def get_r2r_client(user_credentials: Optional[Dict[str, Any]] = None):
    """Initialize R2R client with user-specific or environment credentials."""
    try:
        from r2r import R2RClient
    except ImportError:
        raise ValueError("R2R client not installed. Please install r2r package.")
    
    credentials = get_r2r_credentials(user_credentials)
    
    if not credentials["base_url"]:
        raise ValueError("R2R base URL not found in user credentials or environment")
    
    # Initialize client with base URL
    client = R2RClient(base_url=credentials["base_url"])
    
    # Login with credentials if provided
    if credentials["email"] and credentials["password"]:
        try:
            client.users.login(
                email=credentials["email"],
                password=credentials["password"]
            )
            print(f"✅ DEBUG: R2R login successful for email: {credentials['email']}")
        except Exception as e:
            raise ValueError(f"R2R login failed: {str(e)}")
    elif credentials["api_key"]:
        # If API key is provided, we can use it for authentication
        # This might depend on R2R implementation
        print(f"⚠️ DEBUG: Using API key authentication (implementation dependent)")
        pass
    else:
        raise ValueError("R2R credentials (email/password or API key) not found")
    
    return client


def id_to_shorthand(id: str) -> str:
    """Convert ID to shorthand format."""
    return str(id)[:7]


def format_search_results_for_llm(results) -> str:
    """Format search results for LLM consumption."""
    lines = []

    # 1) Chunk search
    if hasattr(results, 'chunk_search_results') and results.chunk_search_results:
        lines.append("Vector Search Results:")
        for c in results.chunk_search_results:
            lines.append(f"Source ID [{id_to_shorthand(c.id)}]:")
            lines.append(c.text or "")

    # 2) Graph search
    if hasattr(results, 'graph_search_results') and results.graph_search_results:
        lines.append("Graph Search Results:")
        for g in results.graph_search_results:
            lines.append(f"Source ID [{id_to_shorthand(g.id)}]:")
            if hasattr(g.content, "summary"):
                lines.append(f"Community Name: {g.content.name}")
                lines.append(f"ID: {g.content.id}")
                lines.append(f"Summary: {g.content.summary}")
            elif hasattr(g.content, "name") and hasattr(g.content, "description"):
                lines.append(f"Entity Name: {g.content.name}")
                lines.append(f"Description: {g.content.description}")
            elif (
                hasattr(g.content, "subject")
                and hasattr(g.content, "predicate")
                and hasattr(g.content, "object")
            ):
                lines.append(
                    f"Relationship: {g.content.subject}-{g.content.predicate}-{g.content.object}"
                )

    # 3) Web search
    if hasattr(results, 'web_search_results') and results.web_search_results:
        lines.append("Web Search Results:")
        for w in results.web_search_results:
            lines.append(f"Source ID [{id_to_shorthand(w.id)}]:")
            lines.append(f"Title: {w.title}")
            lines.append(f"Link: {w.link}")
            lines.append(f"Snippet: {w.snippet}")

    # 4) Local context docs
    if hasattr(results, 'document_search_results') and results.document_search_results:
        lines.append("Local Context Documents:")
        for doc_result in results.document_search_results:
            doc_title = doc_result.title or "Untitled Document"
            doc_id = doc_result.id
            summary = doc_result.summary

            lines.append(f"Full Document ID: {doc_id}")
            lines.append(f"Shortened Document ID: {id_to_shorthand(doc_id)}")
            lines.append(f"Document Title: {doc_title}")
            if summary:
                lines.append(f"Summary: {summary}")

            if hasattr(doc_result, 'chunks') and doc_result.chunks:
                for chunk in doc_result.chunks:
                    lines.append(
                        f"\nChunk ID {id_to_shorthand(chunk['id'])}:\n{chunk['text']}"
                    )

    result = "\n".join(lines)
    return result if result else "No results found."


def search(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Perform a vector search in the R2R knowledge base."""
    client = get_r2r_client(user_credentials)
    
    query = parameters["query"]
    limit = parameters.get("limit", 10)
    
    try:
        # Debug: Check what parameters search accepts
        print(f"🔍 DEBUG: search method signature: {client.retrieval.search.__doc__}")
        print(f"🔍 DEBUG: search method annotations: {getattr(client.retrieval.search, '__annotations__', 'No annotations')}")
        
        # Try search with different parameter combinations
        try:
            # First try: just query
            search_response = client.retrieval.search(query=query)
            print(f"✅ DEBUG: Search with only query parameter succeeded")
        except Exception as e1:
            print(f"💥 DEBUG: Search with query only failed: {str(e1)}")
            try:
                # Second try: different parameter name
                search_response = client.retrieval.search(
                    query=query,
                    top_k=limit
                )
                print(f"✅ DEBUG: Search with top_k parameter succeeded")
            except Exception as e2:
                print(f"💥 DEBUG: Search with top_k failed: {str(e2)}")
                try:
                    # Third try: different parameter name
                    search_response = client.retrieval.search(
                        query=query,
                        k=limit
                    )
                    print(f"✅ DEBUG: Search with k parameter succeeded")
                except Exception as e3:
                    print(f"💥 DEBUG: Search with k failed: {str(e3)}")
                    try:
                        # Fourth try: no limit parameter at all
                        search_response = client.retrieval.search(query)
                        print(f"✅ DEBUG: Search with positional query succeeded")
                    except Exception as e4:
                        print(f"💥 DEBUG: All search attempts failed: {str(e4)}")
                        raise Exception(f"All search parameter combinations failed. Last error: {str(e4)}")
        
        # Debug response structure
        print(f"🔍 DEBUG: search response type: {type(search_response)}")
        print(f"🔍 DEBUG: search response attributes: {dir(search_response)}")
        
        # Handle response
        if hasattr(search_response, 'results'):
            results = search_response.results
        else:
            results = search_response
            
        formatted_results = format_search_results_for_llm(results)
        
        return {
            "results": formatted_results,
            "query": query,
            "requested_limit": limit
        }
        
    except Exception as e:
        print(f"💥 DEBUG: search error: {str(e)}")
        return {
            "error": f"Search error: {str(e)}",
            "query": query,
            "requested_limit": limit
        }


def rag(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Perform a Retrieval-Augmented Generation query."""
    client = get_r2r_client(user_credentials)
    
    query = parameters["query"]
    use_hybrid = parameters.get("use_hybrid", False)
    use_kg = parameters.get("use_kg", False)
    
    try:
        # Debug: Check what parameters rag accepts
        print(f"🔍 DEBUG: rag method signature: {client.retrieval.rag.__doc__}")
        print(f"🔍 DEBUG: rag method annotations: {getattr(client.retrieval.rag, '__annotations__', 'No annotations')}")
        
        rag_response = client.retrieval.rag(
            query=query,
            use_hybrid_search=use_hybrid,
            use_kg_search=use_kg
        )
        
        # Debug response structure
        print(f"🔍 DEBUG: rag response type: {type(rag_response)}")
        print(f"🔍 DEBUG: rag response attributes: {dir(rag_response)}")
        
        # Handle response
        if hasattr(rag_response, 'results'):
            if hasattr(rag_response.results, 'generated_answer'):
                generated_answer = rag_response.results.generated_answer
            else:
                generated_answer = str(rag_response.results)
        else:
            generated_answer = str(rag_response)
        
        return {
            "answer": generated_answer,
            "query": query,
            "use_hybrid": use_hybrid,
            "use_kg": use_kg
        }
        
    except Exception as e:
        print(f"💥 DEBUG: rag error: {str(e)}")
        return {
            "error": f"RAG error: {str(e)}",
            "query": query,
            "use_hybrid": use_hybrid,
            "use_kg": use_kg
        }


def list_documents(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """List documents in the R2R system."""
    client = get_r2r_client(user_credentials)
    
    limit = parameters.get("limit", 10)
    offset = parameters.get("offset", 0)
    
    try:
        response = client.documents.list(
            limit=limit,
            offset=offset
        )
        
        # Debug: Log response structure
        print(f"🔍 DEBUG: R2R response type: {type(response)}")
        print(f"🔍 DEBUG: R2R response attributes: {dir(response)}")
        
        # Handle PaginatedR2RResult format
        if hasattr(response, 'results'):
            docs = response.results
            total_entries = getattr(response, 'total_entries', None)
            print(f"🔍 DEBUG: Using response.results, total_entries: {total_entries}")
        else:
            docs = response.documents if hasattr(response, "documents") else response
            total_entries = None
            
        print(f"🔍 DEBUG: docs type: {type(docs)}")
        
        if not docs:
            return {
                "documents": [],
                "message": "Hiç döküman bulunamadı.",
                "total": 0
            }
        
        # Handle different response formats
        if hasattr(docs, '__len__'):
            docs_length = len(docs)
            print(f"🔍 DEBUG: docs length: {docs_length}")
        else:
            # If it's an iterator or other non-len object, convert to list
            docs = list(docs)
            docs_length = len(docs)
            print(f"🔍 DEBUG: converted to list, length: {docs_length}")
        
        if docs_length > 0:
            print(f"🔍 DEBUG: First doc type: {type(docs[0])}")
            print(f"🔍 DEBUG: First doc content: {docs[0] if isinstance(docs[0], (str, int, float, bool)) else str(type(docs[0]))}")
        
        doc_list = []
        for i, doc in enumerate(docs):
            try:
                print(f"🔍 DEBUG: Processing doc {i}: type={type(doc)}")
                
                # Handle different document formats
                doc_info = {}
                
                # Handle DocumentResponse objects (R2R specific)
                if hasattr(doc, 'id') and hasattr(doc, '__class__') and 'DocumentResponse' in str(type(doc)):
                    # Convert UUID to string for JSON serialization
                    doc_info["id"] = str(doc.id)
                    doc_info["short_id"] = id_to_shorthand(str(doc.id))
                    
                    # Get other attributes with proper type conversion
                    if hasattr(doc, 'title') and doc.title:
                        doc_info["title"] = str(doc.title)
                    elif hasattr(doc, 'metadata') and doc.metadata and isinstance(doc.metadata, dict):
                        # Try to get title from metadata
                        doc_info["title"] = str(doc.metadata.get('title', f"Document {i+1}"))
                    else:
                        doc_info["title"] = f"Document {i+1}"
                    
                    if hasattr(doc, 'created_at') and doc.created_at:
                        doc_info["created_at"] = str(doc.created_at)
                    
                    if hasattr(doc, 'updated_at') and doc.updated_at:
                        doc_info["updated_at"] = str(doc.updated_at)
                    
                    if hasattr(doc, 'metadata') and doc.metadata:
                        # Convert metadata to JSON-serializable format
                        try:
                            import json
                            doc_info["metadata"] = json.loads(json.dumps(doc.metadata, default=str))
                        except:
                            doc_info["metadata"] = str(doc.metadata)
                
                # Handle tuple format specifically
                elif isinstance(doc, tuple):
                    print(f"🔍 DEBUG: Tuple doc has {len(doc)} elements: {doc}")
                    if len(doc) >= 1:
                        doc_info["id"] = str(doc[0])
                        doc_info["short_id"] = id_to_shorthand(str(doc[0]))
                    if len(doc) >= 2:
                        doc_info["title"] = str(doc[1]) if doc[1] else f"Document {i+1}"
                    if len(doc) >= 3:
                        doc_info["created_at"] = str(doc[2]) if doc[2] else None
                    if len(doc) >= 4:
                        doc_info["size"] = doc[3] if isinstance(doc[3], (int, float)) else None
                    # Add all tuple elements for debugging
                    doc_info["tuple_elements"] = [str(x) for x in doc]
                    
                # Handle object with attributes
                elif hasattr(doc, 'id'):
                    doc_info["id"] = str(doc.id)
                    doc_info["short_id"] = id_to_shorthand(str(doc.id))
                    if hasattr(doc, 'title'):
                        doc_info["title"] = str(doc.title)
                    if hasattr(doc, 'created_at'):
                        doc_info["created_at"] = str(doc.created_at)
                        
                # Handle dictionary format
                elif isinstance(doc, dict):
                    if 'id' in doc:
                        doc_info["id"] = str(doc['id'])
                        doc_info["short_id"] = id_to_shorthand(str(doc['id']))
                    if 'title' in doc:
                        doc_info["title"] = str(doc['title'])
                    if 'created_at' in doc:
                        doc_info["created_at"] = str(doc['created_at'])
                    doc_info["raw_keys"] = list(doc.keys())
                    
                else:
                    # Fallback: use index as ID
                    doc_info["id"] = f"doc_{i}"
                    doc_info["short_id"] = f"doc_{i}"
                    doc_info["title"] = f"Document {i+1}"
                
                # Ensure we have minimum required fields
                if "id" not in doc_info:
                    doc_info["id"] = f"doc_{i}"
                    doc_info["short_id"] = f"doc_{i}"
                if "title" not in doc_info:
                    doc_info["title"] = f"Document {i+1}"
                
                doc_list.append(doc_info)
                print(f"✅ DEBUG: Successfully processed doc {i}")
                
            except Exception as doc_error:
                print(f"💥 DEBUG: Error processing doc {i}: {str(doc_error)}")
                # Add error info but continue processing
                doc_list.append({
                    "id": f"error_doc_{i}",
                    "short_id": f"err_{i}",
                    "title": f"Error Document {i+1}",
                    "error": str(doc_error),
                    "doc_type": str(type(doc))
                })
        
        return {
            "documents": doc_list,
            "total": total_entries if total_entries is not None else docs_length,
            "limit": limit,
            "offset": offset,
            "debug_info": {
                "response_type": str(type(response)),
                "docs_type": str(type(docs)),
                "docs_length": docs_length,
                "total_entries": total_entries
            }
        }
        
    except Exception as e:
        print(f"💥 DEBUG: list_documents error: {str(e)}")
        return {
            "error": f"Error listing documents: {str(e)}",
            "documents": [],
            "total": 0
        }


def get_document(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get detailed information about a specific document."""
    client = get_r2r_client(user_credentials)
    
    document_id = parameters["document_id"]
    
    try:
        response = client.documents.retrieve(id=document_id)
        
        # Debug: Log response structure
        print(f"🔍 DEBUG: get_document response type: {type(response)}")
        print(f"🔍 DEBUG: get_document response attributes: {dir(response)}")
        
        # Handle different response formats
        if hasattr(response, 'results'):
            doc = response.results
            print(f"🔍 DEBUG: Using response.results")
        else:
            doc = response.document if hasattr(response, "document") else response
            
        print(f"🔍 DEBUG: doc type: {type(doc)}")
        
        # Handle different document formats
        doc_info = {}
        
        # Handle DocumentResponse objects (R2R specific)
        if hasattr(doc, 'id') and hasattr(doc, '__class__') and 'DocumentResponse' in str(type(doc)):
            # Convert UUID to string for JSON serialization
            doc_info["id"] = str(doc.id)
            doc_info["short_id"] = id_to_shorthand(str(doc.id))
            
            # Get other attributes with proper type conversion
            if hasattr(doc, 'title') and doc.title:
                doc_info["title"] = str(doc.title)
            elif hasattr(doc, 'metadata') and doc.metadata and isinstance(doc.metadata, dict):
                # Try to get title from metadata
                doc_info["title"] = str(doc.metadata.get('title', "Untitled Document"))
            else:
                doc_info["title"] = "Untitled Document"
            
            if hasattr(doc, 'created_at') and doc.created_at:
                doc_info["created_at"] = str(doc.created_at)
            
            if hasattr(doc, 'updated_at') and doc.updated_at:
                doc_info["updated_at"] = str(doc.updated_at)
            
            if hasattr(doc, 'size') and doc.size:
                doc_info["size"] = int(doc.size) if isinstance(doc.size, (int, float)) else str(doc.size)
            
            if hasattr(doc, 'metadata') and doc.metadata:
                # Convert metadata to JSON-serializable format
                try:
                    import json
                    doc_info["metadata"] = json.loads(json.dumps(doc.metadata, default=str))
                except:
                    doc_info["metadata"] = str(doc.metadata)
        
        # Handle tuple format specifically
        elif isinstance(doc, tuple):
            print(f"🔍 DEBUG: Tuple doc has {len(doc)} elements: {doc}")
            if len(doc) >= 1:
                doc_info["id"] = str(doc[0])
                doc_info["short_id"] = id_to_shorthand(str(doc[0]))
            if len(doc) >= 2:
                doc_info["title"] = str(doc[1]) if doc[1] else "Untitled Document"
            if len(doc) >= 3:
                doc_info["created_at"] = str(doc[2]) if doc[2] else None
            if len(doc) >= 4:
                doc_info["size"] = doc[3] if isinstance(doc[3], (int, float)) else None
            # Add all tuple elements for debugging
            doc_info["tuple_elements"] = [str(x) for x in doc]
            
        # Handle object with attributes
        elif hasattr(doc, 'id'):
            doc_info["id"] = str(doc.id)
            doc_info["short_id"] = id_to_shorthand(str(doc.id))
            if hasattr(doc, 'title'):
                doc_info["title"] = str(doc.title)
            if hasattr(doc, 'created_at'):
                doc_info["created_at"] = str(doc.created_at)
            if hasattr(doc, 'size'):
                doc_info["size"] = str(doc.size)
            if hasattr(doc, 'metadata'):
                doc_info["metadata"] = str(doc.metadata)
                
        # Handle dictionary format
        elif isinstance(doc, dict):
            if 'id' in doc:
                doc_info["id"] = str(doc['id'])
                doc_info["short_id"] = id_to_shorthand(str(doc['id']))
            if 'title' in doc:
                doc_info["title"] = str(doc['title'])
            if 'created_at' in doc:
                doc_info["created_at"] = str(doc['created_at'])
            if 'size' in doc:
                doc_info["size"] = str(doc['size'])
            if 'metadata' in doc:
                doc_info["metadata"] = doc['metadata']
            doc_info["raw_keys"] = list(doc.keys())
            
        else:
            # Fallback: use provided ID
            doc_info["id"] = str(document_id)
            doc_info["short_id"] = id_to_shorthand(str(document_id))
            doc_info["title"] = "Unknown Document"
        
        # Ensure we have minimum required fields
        if "id" not in doc_info:
            doc_info["id"] = str(document_id)
            doc_info["short_id"] = id_to_shorthand(str(document_id))
        if "title" not in doc_info:
            doc_info["title"] = "Untitled Document"
        
        return {
            "document": doc_info,
            "debug_info": {
                "response_type": str(type(response)),
                "doc_type": str(type(doc))
            }
        }
        
    except Exception as e:
        print(f"💥 DEBUG: get_document error: {str(e)}")
        return {
            "error": f"Error retrieving document: {str(e)}",
            "document_id": document_id
        }


def list_collections(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """List collections in the R2R system."""
    client = get_r2r_client(user_credentials)
    
    try:
        response = client.collections.list()
        
        # Debug: Log response structure
        print(f"🔍 DEBUG: list_collections response type: {type(response)}")
        print(f"🔍 DEBUG: list_collections response attributes: {dir(response)}")
        
        # Handle PaginatedR2RResult format
        if hasattr(response, 'results'):
            collections = response.results
            total_entries = getattr(response, 'total_entries', None)
            print(f"🔍 DEBUG: Using response.results, total_entries: {total_entries}")
        else:
            collections = response.collections if hasattr(response, "collections") else response
            total_entries = None
            
        print(f"🔍 DEBUG: collections type: {type(collections)}")
        
        if not collections:
            return {
                "collections": [],
                "message": "Collections endpoint not available or no collections found",
                "total": 0
            }
        
        # Handle different response formats
        if hasattr(collections, '__len__'):
            collections_length = len(collections)
            print(f"🔍 DEBUG: collections length: {collections_length}")
        else:
            # If it's an iterator or other non-len object, convert to list
            collections = list(collections)
            collections_length = len(collections)
            print(f"🔍 DEBUG: converted to list, length: {collections_length}")
        
        if collections_length > 0:
            print(f"🔍 DEBUG: First collection type: {type(collections[0])}")
        
        collection_list = []
        for i, col in enumerate(collections):
            try:
                print(f"🔍 DEBUG: Processing collection {i}: type={type(col)}")
                
                # Handle different collection formats
                col_info = {}
                
                # Handle CollectionResponse objects (R2R specific)
                if hasattr(col, 'id') and hasattr(col, '__class__') and ('Response' in str(type(col)) or 'Collection' in str(type(col))):
                    # Convert UUID to string for JSON serialization
                    col_info["id"] = str(col.id)
                    col_info["short_id"] = id_to_shorthand(str(col.id))
                    
                    # Get other attributes with proper type conversion
                    if hasattr(col, 'name') and col.name:
                        col_info["name"] = str(col.name)
                    else:
                        col_info["name"] = f"Collection {i+1}"
                    
                    if hasattr(col, 'description') and col.description:
                        col_info["description"] = str(col.description)
                    
                    if hasattr(col, 'created_at') and col.created_at:
                        col_info["created_at"] = str(col.created_at)
                    
                    if hasattr(col, 'updated_at') and col.updated_at:
                        col_info["updated_at"] = str(col.updated_at)
                
                # Handle tuple format specifically
                elif isinstance(col, tuple):
                    print(f"🔍 DEBUG: Tuple collection has {len(col)} elements: {col}")
                    if len(col) >= 1:
                        col_info["id"] = str(col[0])
                        col_info["short_id"] = id_to_shorthand(str(col[0]))
                    if len(col) >= 2:
                        col_info["name"] = str(col[1]) if col[1] else f"Collection {i+1}"
                    if len(col) >= 3:
                        col_info["description"] = str(col[2]) if col[2] else None
                    # Add all tuple elements for debugging
                    col_info["tuple_elements"] = [str(x) for x in col]
                    
                # Handle object with attributes
                elif hasattr(col, 'id'):
                    col_info["id"] = str(col.id)
                    col_info["short_id"] = id_to_shorthand(str(col.id))
                    if hasattr(col, 'name'):
                        col_info["name"] = str(col.name)
                    if hasattr(col, 'description'):
                        col_info["description"] = str(col.description)
                        
                # Handle dictionary format
                elif isinstance(col, dict):
                    if 'id' in col:
                        col_info["id"] = str(col['id'])
                        col_info["short_id"] = id_to_shorthand(str(col['id']))
                    if 'name' in col:
                        col_info["name"] = str(col['name'])
                    if 'description' in col:
                        col_info["description"] = str(col['description'])
                    col_info["raw_keys"] = list(col.keys())
                    
                else:
                    # Fallback: use index as ID
                    col_info["id"] = f"col_{i}"
                    col_info["short_id"] = f"col_{i}"
                    col_info["name"] = f"Collection {i+1}"
                
                # Ensure we have minimum required fields
                if "id" not in col_info:
                    col_info["id"] = f"col_{i}"
                    col_info["short_id"] = f"col_{i}"
                if "name" not in col_info:
                    col_info["name"] = f"Collection {i+1}"
                
                collection_list.append(col_info)
                print(f"✅ DEBUG: Successfully processed collection {i}")
                
            except Exception as col_error:
                print(f"💥 DEBUG: Error processing collection {i}: {str(col_error)}")
                # Add error info but continue processing  
                collection_list.append({
                    "id": f"error_col_{i}",
                    "short_id": f"err_{i}",
                    "name": f"Error Collection {i+1}",
                    "error": str(col_error),
                    "col_type": str(type(col))
                })
        
        return {
            "collections": collection_list,
            "total": total_entries if total_entries is not None else collections_length,
            "debug_info": {
                "response_type": str(type(response)),
                "collections_type": str(type(collections)),
                "collections_length": collections_length,
                "total_entries": total_entries
            }
        }
        
    except Exception as e:
        print(f"💥 DEBUG: list_collections error: {str(e)}")
        return {
            "collections": [],
            "message": f"Collections endpoint error: {str(e)}",
            "total": 0
        }


def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        user_credentials = input_data.get("user_credentials")  # Get credentials from execution data
        
        # Execute action
        if action == "search":
            result = search(parameters, user_credentials)
        elif action == "rag":
            result = rag(parameters, user_credentials)
        elif action == "list_documents":
            result = list_documents(parameters, user_credentials)
        elif action == "get_document":
            result = get_document(parameters, user_credentials)
        elif action == "list_collections":
            result = list_collections(parameters, user_credentials)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Return result
        print(json.dumps(result))
        
    except Exception as e:
        # Return error
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main() 