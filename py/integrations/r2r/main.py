#!/usr/bin/env python3
"""
R2R Integration - Main Script
"""
import json
import sys
import os
from typing import Dict, Any


def get_r2r_credentials() -> Dict[str, str]:
    """Get R2R credentials from environment."""
    api_base = os.getenv("R2R_API_BASE")
    base_url = os.getenv("R2R_BASE_URL") 
    api_key = os.getenv("R2R_API_KEY")
    email = os.getenv("R2R_EMAIL")
    password = os.getenv("R2R_PASSWORD")
    
    if not api_base or not base_url:
        raise ValueError("R2R API base URL not found")
    
    return {
        "api_base": api_base,
        "base_url": base_url,
        "api_key": api_key,
        "email": email,
        "password": password
    }


def get_r2r_client():
    """Initialize R2R client with user credentials."""
    try:
        from r2r import R2RClient
    except ImportError:
        raise ValueError("R2R client not installed. Please install r2r package.")
    
    credentials = get_r2r_credentials()
    
    # Initialize client with base URL
    client = R2RClient(base_url=credentials["base_url"])
    
    # Login with user credentials if provided
    if credentials["email"] and credentials["password"]:
        try:
            client.users.login(
                email=credentials["email"],
                password=credentials["password"]
            )
        except Exception as e:
            raise ValueError(f"R2R login failed: {str(e)}")
    elif credentials["api_key"]:
        # If API key is provided, we can use it for authentication
        # This might depend on R2R implementation
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


def search(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Perform a vector search in the R2R knowledge base."""
    client = get_r2r_client()
    
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


def rag(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Perform a Retrieval-Augmented Generation query."""
    client = get_r2r_client()
    
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


def list_documents(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List documents in the R2R system."""
    client = get_r2r_client()
    
    limit = parameters.get("limit", 10)
    offset = parameters.get("offset", 0)
    
    response = client.documents.list(
        limit=limit,
        offset=offset
    )
    
    docs = response.documents if hasattr(response, "documents") else response
    
    if not docs:
        return {
            "documents": [],
            "message": "Hiç döküman bulunamadı.",
            "total": 0
        }
    
    doc_list = []
    for doc in docs:
        doc_info = {
            "id": doc.id,
            "short_id": id_to_shorthand(doc.id)
        }
        if hasattr(doc, 'title'):
            doc_info["title"] = doc.title
        if hasattr(doc, 'created_at'):
            doc_info["created_at"] = doc.created_at
        doc_list.append(doc_info)
    
    return {
        "documents": doc_list,
        "total": len(docs),
        "limit": limit,
        "offset": offset
    }


def get_document(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed information about a specific document."""
    client = get_r2r_client()
    
    document_id = parameters["document_id"]
    
    try:
        response = client.documents.retrieve(id=document_id)
        doc = response.document if hasattr(response, "document") else response
        
        doc_info = {
            "id": doc.id,
            "short_id": id_to_shorthand(doc.id)
        }
        
        if hasattr(doc, 'title'):
            doc_info["title"] = doc.title
        if hasattr(doc, 'created_at'):
            doc_info["created_at"] = doc.created_at
        if hasattr(doc, 'size'):
            doc_info["size"] = doc.size
        if hasattr(doc, 'metadata'):
            doc_info["metadata"] = doc.metadata
        
        return {"document": doc_info}
        
    except Exception as e:
        return {
            "error": f"Error retrieving document: {str(e)}",
            "document_id": document_id
        }


def list_collections(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List collections in the R2R system."""
    client = get_r2r_client()
    
    try:
        response = client.collections.list()
        collections = response.collections if hasattr(response, "collections") else response
        
        collection_list = []
        for col in collections:
            col_info = {
                "id": col.id,
                "short_id": id_to_shorthand(col.id)
            }
            if hasattr(col, 'name'):
                col_info["name"] = col.name
            if hasattr(col, 'description'):
                col_info["description"] = col.description
            collection_list.append(col_info)
        
        return {
            "collections": collection_list,
            "total": len(collections)
        }
        
    except Exception:
        return {
            "collections": [],
            "message": "Collections endpoint not available",
            "total": 0
        }


def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        
        # Execute action
        if action == "search":
            result = search(parameters)
        elif action == "rag":
            result = rag(parameters)
        elif action == "list_documents":
            result = list_documents(parameters)
        elif action == "get_document":
            result = get_document(parameters)
        elif action == "list_collections":
            result = list_collections(parameters)
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