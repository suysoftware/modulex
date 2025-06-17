#!/usr/bin/env python3
"""
GitHub Integration - Main Script
"""
import json
import sys
import os
import requests
from typing import Dict, Any


def get_auth_headers() -> Dict[str, str]:
    """Get Nellis Auction API authentication headers"""
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise ValueError("ACCESS_TOKEN not found in environment")
    
    return {
        "Cookie": "__session=" + access_token,
        "Accept": "application/json"
    }


def list_active_auctions(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List active auctions"""
    headers = get_auth_headers()
    
    response = requests.get(
        f"https://www.nellisauction.com/dashboard/auctions/active?_data=routes%2Fdashboard.auctions.active",
        headers=headers
    )
    response.raise_for_status()
    
    data = response.json()
    auctions = data.get("myAuctions", {}).get("records", [])
    
    return {
        "active_auctions": [
            {
                "product_id": auction["id"],
                "title": auction["title"],
                "inventory_number": auction["inventoryNumber"],
                "current_price": auction["currentPrice"],
                "retail_price": auction["retailPrice"],
                "bid_count": auction["bidCount"],
                "market_status": auction["marketStatus"],
                "close_time": auction["closeTime"]["value"] if auction.get("closeTime") else None,
                "location": f"{auction['location']['city']}, {auction['location']['state']}" if auction.get("location") else None,
                "rating": auction["grade"]["rating"] if auction.get("grade") else None,
                "condition": auction["grade"]["conditionType"]["description"] if auction.get("grade", {}).get("conditionType") else None,
                "photo_url": auction["photos"][0]["url"] if auction.get("photos") and len(auction["photos"]) > 0 else None,
                "is_winning": auction["userState"]["isWinning"] if auction.get("userState") else False
            }
            for auction in auctions
        ],
        "total": len(auctions)
    }

def bid_on_active_auction(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Bid on the active auction"""
    print(f"[DEBUG] bid_on_active_auction called with parameters: {parameters}", file=sys.stderr)
    
    try:
        headers = get_auth_headers()
        print(f"[DEBUG] Headers obtained successfully", file=sys.stderr)
        
        product_id = parameters.get("productId")
        if not product_id:
            print(f"[ERROR] Product ID is missing from parameters", file=sys.stderr)
            raise ValueError("Product ID is required")
        
        print(f"[DEBUG] Product ID: {product_id}", file=sys.stderr)
        
        data = {
            "bid": parameters.get("bid", 0),
            "productId": product_id
        }
        
        print(f"[DEBUG] Request data: {json.dumps(data)}", file=sys.stderr)
        print(f"[DEBUG] Request headers: {json.dumps({k: v for k, v in headers.items() if k != 'Cookie'})}", file=sys.stderr)
        
        url = "https://www.nellisauction.com/api/bids"
        print(f"[DEBUG] Making POST request to: {url}", file=sys.stderr)
        
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        
        print(f"[DEBUG] Response status code: {response.status_code}", file=sys.stderr)
        print(f"[DEBUG] Response headers: {dict(response.headers)}", file=sys.stderr)
        
        # Response content'i log et
        response_text = response.text
        print(f"[DEBUG] Response content: {response_text}", file=sys.stderr)
        
        # Status code kontrolü
        if not response.ok:
            print(f"[ERROR] HTTP Error {response.status_code}: {response_text}", file=sys.stderr)
            return {
                "error": f"HTTP {response.status_code}: {response_text}",
                "status_code": response.status_code,
                "response_content": response_text
            }
        
        try:
            repo = response.json()
            print(f"[DEBUG] Successfully parsed JSON response: {json.dumps(repo)}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON response: {e}", file=sys.stderr)
            return {
                "error": f"Invalid JSON response: {response_text}",
                "json_error": str(e)
            }
        
        result = {
            "message": repo.get("message", ""),
            "bid_count": repo.get("data", {}).get("bidCount"),
            "current_amount": repo.get("data", {}).get("currentAmount"),
            "minimum_next_bid": repo.get("data", {}).get("minimumNextBid"),
            "winning_bid_user_id": repo.get("data", {}).get("winningBidUserId"),
            "bidder_count": repo.get("data", {}).get("bidderCount"),
            "projected_new_close_time": repo.get("data", {}).get("projectNewCloseTime", {}).get("value") if repo.get("data", {}).get("projectNewCloseTime") else None,
            "project_extended": repo.get("data", {}).get("projectExtended")
        }
        
        print(f"[DEBUG] Final result: {json.dumps(result)}", file=sys.stderr)
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request exception: {e}", file=sys.stderr)
        return {
            "error": f"Request failed: {str(e)}",
            "exception_type": "RequestException"
        }
    except Exception as e:
        print(f"[ERROR] Unexpected exception: {e}", file=sys.stderr)
        print(f"[ERROR] Exception type: {type(e).__name__}", file=sys.stderr)
        return {
            "error": str(e),
            "exception_type": type(e).__name__
        }

def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        
        # Execute action
        if action == "list_active_auctions":
            result = list_active_auctions(parameters)
        elif action == "bid_on_active_auction":
            result = bid_on_active_auction(parameters)
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