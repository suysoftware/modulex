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
    try:
        headers = get_auth_headers()
        
        product_id = parameters.get("productId", 0)
        if not product_id:
            return {
                "success": False,
                "error": "Product ID is required",
                "error_code": "MISSING_PRODUCT_ID",
                "user_message": "Ürün ID'si eksik. Lütfen tekrar deneyin."
            }
        
        bid_amount = parameters.get("bid", 0)
        if bid_amount <= 0:
            return {
                "success": False,
                "error": "Invalid bid amount",
                "error_code": "INVALID_BID_AMOUNT",
                "user_message": "Geçerli bir teklif miktarı giriniz."
            }
        
        data = {
            "bid": bid_amount,
            "productId": product_id
        }
        
        response = requests.post(
            "https://www.nellisauction.com/api/bids",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response_data = None
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            pass
        
        # Detailed error handling based on status codes
        if response.status_code == 400:
            error_msg = "Geçersiz teklif verisi"
            if response_data and "message" in response_data:
                error_msg = response_data["message"]
            return {
                "success": False,
                "error": "Bad Request - Invalid bid data",
                "error_code": "INVALID_BID_DATA",
                "user_message": f"Teklif verirken hata oluştu: {error_msg}",
                "status_code": 400,
                "api_response": response_data
            }
        
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Unauthorized - Invalid or expired session",
                "error_code": "AUTH_FAILED",
                "user_message": "Oturum süresi dolmuş veya geçersiz. Lütfen tekrar giriş yapın.",
                "status_code": 401
            }
        
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "Forbidden - Not allowed to bid on this auction",
                "error_code": "BID_FORBIDDEN",
                "user_message": "Bu müzayedeye teklif verme yetkiniz yok.",
                "status_code": 403
            }
        
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Auction not found",
                "error_code": "AUCTION_NOT_FOUND",
                "user_message": "Müzayede bulunamadı. Müzayede sona ermiş olabilir.",
                "status_code": 404
            }
        
        elif response.status_code == 409:
            error_msg = "Teklif çakışması"
            if response_data and "message" in response_data:
                error_msg = response_data["message"]
            return {
                "success": False,
                "error": "Conflict - Bid conflict",
                "error_code": "BID_CONFLICT",
                "user_message": f"Teklif çakışması: {error_msg}",
                "status_code": 409,
                "api_response": response_data
            }
        
        elif response.status_code == 422:
            error_msg = "Teklif miktarı geçersiz"
            if response_data and "message" in response_data:
                error_msg = response_data["message"]
            return {
                "success": False,
                "error": "Unprocessable Entity - Invalid bid amount",
                "error_code": "INVALID_BID_AMOUNT",
                "user_message": f"Geçersiz teklif miktarı: {error_msg}",
                "status_code": 422,
                "api_response": response_data
            }
        
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "Too Many Requests - Rate limit exceeded",
                "error_code": "RATE_LIMIT",
                "user_message": "Çok fazla istek gönderildi. Lütfen bir süre bekleyip tekrar deneyin.",
                "status_code": 429
            }
        
        elif response.status_code >= 500:
            return {
                "success": False,
                "error": "Server Error - Nellis Auction server issue",
                "error_code": "SERVER_ERROR",
                "user_message": "Nellis Auction sunucusunda bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                "status_code": response.status_code,
                "server_response": response.text[:200]  # İlk 200 karakter
            }
        
        elif not response.ok:
            return {
                "success": False,
                "error": f"HTTP {response.status_code} - Unknown error",
                "error_code": "UNKNOWN_HTTP_ERROR",
                "user_message": f"Bilinmeyen bir hata oluştu (HTTP {response.status_code}). Lütfen tekrar deneyin.",
                "status_code": response.status_code,
                "response_content": response.text[:200]
            }
        
        # Success case
        if not response_data:
            return {
                "success": False,
                "error": "Invalid response format",
                "error_code": "INVALID_RESPONSE",
                "user_message": "Sunucudan geçersiz yanıt alındı.",
                "response_content": response.text[:200]
            }
        
        # Check if bid was successful
        if response_data.get("success") is False or "error" in response_data:
            error_msg = response_data.get("message", "Bilinmeyen hata")
            return {
                "success": False,
                "error": "Bid rejected by server",
                "error_code": "BID_REJECTED",
                "user_message": f"Teklif reddedildi: {error_msg}",
                "api_response": response_data
            }
        
        return {
            "success": True,
            "message": response_data.get("message", "Teklif başarıyla verildi"),
            "bid_count": response_data.get("data", {}).get("bidCount"),
            "current_amount": response_data.get("data", {}).get("currentAmount"),
            "minimum_next_bid": response_data.get("data", {}).get("minimumNextBid"),
            "winning_bid_user_id": response_data.get("data", {}).get("winningBidUserId"),
            "bidder_count": response_data.get("data", {}).get("bidderCount"),
            "projected_new_close_time": response_data.get("data", {}).get("projectNewCloseTime", {}).get("value") if response_data.get("data", {}).get("projectNewCloseTime") else None,
            "project_extended": response_data.get("data", {}).get("projectExtended"),
            "user_message": "Teklifiniz başarıyla verildi!"
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout",
            "error_code": "TIMEOUT",
            "user_message": "İstek zaman aşımına uğradı. Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin."
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection failed",
            "error_code": "CONNECTION_ERROR",
            "user_message": "Nellis Auction'a bağlanılamadı. Lütfen internet bağlantınızı kontrol edin."
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "error_code": "REQUEST_FAILED",
            "user_message": "İstek sırasında bir hata oluştu. Lütfen tekrar deneyin."
        }
    except ValueError as e:
        if "ACCESS_TOKEN" in str(e):
            return {
                "success": False,
                "error": "Authentication token missing",
                "error_code": "AUTH_TOKEN_MISSING",
                "user_message": "Kimlik doğrulama tokeni eksik. Lütfen giriş yapın."
            }
        return {
            "success": False,
            "error": str(e),
            "error_code": "VALUE_ERROR",
            "user_message": "Geçersiz veri. Lütfen girdiğiniz bilgileri kontrol edin."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "UNEXPECTED_ERROR",
            "user_message": "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin."
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