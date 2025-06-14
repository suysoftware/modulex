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
            "api_base": user_credentials.get("base_url") or os.getenv("R2R_API_BASE"),
            "base_url": user_credentials.get("base_url") or os.getenv("R2R_BASE_URL"),
            "api_key": None,  # Not used in manual auth
            "email": user_credentials.get("email"),
            "password": user_credentials.get("password")
        }
    else:
        # Fallback to environment variables (backward compatibility)
        api_base = os.getenv("R2R_API_BASE")
        base_url = os.getenv("R2R_BASE_URL") 
        api_key = os.getenv("R2R_API_KEY")
        email = os.getenv("R2R_EMAIL")
        password = os.getenv("R2R_PASSWORD")
        
        return {
            "api_base": api_base,
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
    
    search_response = client.retrieval.search(
        query=query,
        limit=limit
    )
    
    formatted_results = format_search_results_for_llm(search_response.results)
    
    return {
        "results": formatted_results,
        "query": query,
        "limit": limit
    }


def rag(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Perform a Retrieval-Augmented Generation query."""
    client = get_r2r_client(user_credentials)
    
    query = parameters["query"]
    use_hybrid = parameters.get("use_hybrid", False)
    use_kg = parameters.get("use_kg", False)
    
    rag_response = client.retrieval.rag(
        query=query,
        use_hybrid_search=use_hybrid,
        use_kg_search=use_kg
    )
    
    generated_answer = rag_response.results.generated_answer if hasattr(rag_response.results, 'generated_answer') else str(rag_response.results)
    
    return {
        "answer": generated_answer,
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
        
        docs = response.documents if hasattr(response, "documents") else response
        print(f"🔍 DEBUG: docs type: {type(docs)}")
        
        if not docs:
            return {
                "documents": [],
                "message": "Hiç döküman bulunamadı.",
                "total": 0
            }
        
        # Handle different response formats
        if isinstance(docs, (list, tuple)):
            print(f"🔍 DEBUG: docs is list/tuple with {len(docs)} items")
            if len(docs) > 0:
                print(f"🔍 DEBUG: First doc type: {type(docs[0])}")
                print(f"🔍 DEBUG: First doc attributes: {dir(docs[0]) if hasattr(docs[0], '__dict__') else 'No attributes'}")
        
        doc_list = []
        for i, doc in enumerate(docs):
            try:
                print(f"🔍 DEBUG: Processing doc {i}: type={type(doc)}")
                
                # Handle different document formats
                doc_info = {}
                
                # Try different ways to get document ID
                if hasattr(doc, 'id'):
                    doc_info["id"] = doc.id
                    doc_info["short_id"] = id_to_shorthand(doc.id)
                elif isinstance(doc, dict) and 'id' in doc:
                    doc_info["id"] = doc['id']
                    doc_info["short_id"] = id_to_shorthand(doc['id'])
                elif isinstance(doc, (list, tuple)) and len(doc) > 0:
                    # If it's a tuple/list, try to use first element as ID
                    doc_info["id"] = str(doc[0])
                    doc_info["short_id"] = id_to_shorthand(str(doc[0]))
                else:
                    # Fallback: use index as ID
                    doc_info["id"] = f"doc_{i}"
                    doc_info["short_id"] = f"doc_{i}"
                
                # Try to get other attributes
                if hasattr(doc, 'title'):
                    doc_info["title"] = doc.title
                elif isinstance(doc, dict) and 'title' in doc:
                    doc_info["title"] = doc['title']
                
                if hasattr(doc, 'created_at'):
                    doc_info["created_at"] = doc.created_at
                elif isinstance(doc, dict) and 'created_at' in doc:
                    doc_info["created_at"] = doc['created_at']
                
                # Add raw doc info for debugging
                if isinstance(doc, dict):
                    doc_info["raw_keys"] = list(doc.keys())
                elif hasattr(doc, '__dict__'):
                    doc_info["raw_attrs"] = [attr for attr in dir(doc) if not attr.startswith('_')]
                
                doc_list.append(doc_info)
                print(f"✅ DEBUG: Successfully processed doc {i}")
                
            except Exception as doc_error:
                print(f"💥 DEBUG: Error processing doc {i}: {str(doc_error)}")
                # Add error info but continue processing
                doc_list.append({
                    "id": f"error_doc_{i}",
                    "short_id": f"err_{i}",
                    "error": str(doc_error),
                    "doc_type": str(type(doc))
                })
        
        return {
            "documents": doc_list,
            "total": len(docs),
            "limit": limit,
            "offset": offset,
            "debug_info": {
                "response_type": str(type(response)),
                "docs_type": str(type(docs)),
                "docs_length": len(docs) if docs else 0
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
        
        doc = response.document if hasattr(response, "document") else response
        print(f"🔍 DEBUG: doc type: {type(doc)}")
        
        # Handle different document formats
        doc_info = {}
        
        # Try different ways to get document ID
        if hasattr(doc, 'id'):
            doc_info["id"] = doc.id
            doc_info["short_id"] = id_to_shorthand(doc.id)
        elif isinstance(doc, dict) and 'id' in doc:
            doc_info["id"] = doc['id']
            doc_info["short_id"] = id_to_shorthand(doc['id'])
        else:
            # Fallback: use provided ID
            doc_info["id"] = document_id
            doc_info["short_id"] = id_to_shorthand(document_id)
        
        # Try to get other attributes
        if hasattr(doc, 'title'):
            doc_info["title"] = doc.title
        elif isinstance(doc, dict) and 'title' in doc:
            doc_info["title"] = doc['title']
            
        if hasattr(doc, 'created_at'):
            doc_info["created_at"] = doc.created_at
        elif isinstance(doc, dict) and 'created_at' in doc:
            doc_info["created_at"] = doc['created_at']
            
        if hasattr(doc, 'size'):
            doc_info["size"] = doc.size
        elif isinstance(doc, dict) and 'size' in doc:
            doc_info["size"] = doc['size']
            
        if hasattr(doc, 'metadata'):
            doc_info["metadata"] = doc.metadata
        elif isinstance(doc, dict) and 'metadata' in doc:
            doc_info["metadata"] = doc['metadata']
        
        # Add raw doc info for debugging
        if isinstance(doc, dict):
            doc_info["raw_keys"] = list(doc.keys())
        elif hasattr(doc, '__dict__'):
            doc_info["raw_attrs"] = [attr for attr in dir(doc) if not attr.startswith('_')]
        
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
        
        collections = response.collections if hasattr(response, "collections") else response
        print(f"🔍 DEBUG: collections type: {type(collections)}")
        
        if not collections:
            return {
                "collections": [],
                "message": "Collections endpoint not available or no collections found",
                "total": 0
            }
        
        collection_list = []
        for i, col in enumerate(collections):
            try:
                print(f"🔍 DEBUG: Processing collection {i}: type={type(col)}")
                
                # Handle different collection formats
                col_info = {}
                
                # Try different ways to get collection ID
                if hasattr(col, 'id'):
                    col_info["id"] = col.id
                    col_info["short_id"] = id_to_shorthand(col.id)
                elif isinstance(col, dict) and 'id' in col:
                    col_info["id"] = col['id']
                    col_info["short_id"] = id_to_shorthand(col['id'])
                elif isinstance(col, (list, tuple)) and len(col) > 0:
                    # If it's a tuple/list, try to use first element as ID
                    col_info["id"] = str(col[0])
                    col_info["short_id"] = id_to_shorthand(str(col[0]))
                else:
                    # Fallback: use index as ID
                    col_info["id"] = f"col_{i}"
                    col_info["short_id"] = f"col_{i}"
                
                # Try to get other attributes
                if hasattr(col, 'name'):
                    col_info["name"] = col.name
                elif isinstance(col, dict) and 'name' in col:
                    col_info["name"] = col['name']
                    
                if hasattr(col, 'description'):
                    col_info["description"] = col.description
                elif isinstance(col, dict) and 'description' in col:
                    col_info["description"] = col['description']
                
                # Add raw collection info for debugging
                if isinstance(col, dict):
                    col_info["raw_keys"] = list(col.keys())
                elif hasattr(col, '__dict__'):
                    col_info["raw_attrs"] = [attr for attr in dir(col) if not attr.startswith('_')]
                
                collection_list.append(col_info)
                print(f"✅ DEBUG: Successfully processed collection {i}")
                
            except Exception as col_error:
                print(f"💥 DEBUG: Error processing collection {i}: {str(col_error)}")
                # Add error info but continue processing  
                collection_list.append({
                    "id": f"error_col_{i}",
                    "short_id": f"err_{i}",
                    "error": str(col_error),
                    "col_type": str(type(col))
                })
        
        return {
            "collections": collection_list,
            "total": len(collections),
            "debug_info": {
                "response_type": str(type(response)),
                "collections_type": str(type(collections)),
                "collections_length": len(collections) if collections else 0
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