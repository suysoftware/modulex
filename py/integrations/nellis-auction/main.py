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
    headers = get_auth_headers()
    
    product_id = parameters.get("productId")
    if not product_id:
        raise ValueError("Product ID is required")
    
    data = {
        "bid": parameters.get("bid", 0),
        "productId": product_id
    }
    
    response = requests.post(
        "https://www.nellisauction.com/api/bids",
        headers=headers,
        json=data
    )
    response.raise_for_status()
    
    repo = response.json()
    return {
        "message": repo.get("message", ""),
        "bid_count": repo.get("data", {}).get("bidCount"),
        "current_amount": repo.get("data", {}).get("currentAmount"),
        "minimum_next_bid": repo.get("data", {}).get("minimumNextBid"),
        "winning_bid_user_id": repo.get("data", {}).get("winningBidUserId"),
        "bidder_count": repo.get("data", {}).get("bidderCount"),
        "projected_new_close_time": repo.get("data", {}).get("projectNewCloseTime", {}).get("value") if repo.get("data", {}).get("projectNewCloseTime") else None,
        "project_extended": repo.get("data", {}).get("projectExtended")
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