#!/usr/bin/env python3
"""
Reddit Integration - Main Script
"""
import json
import sys
import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests.exceptions


def get_reddit_credentials(user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Get Reddit credentials from user data or environment."""
    if user_credentials and user_credentials.get("auth_type") == "manual":
        return {
            "client_id": user_credentials.get("client_id"),
            "client_secret": user_credentials.get("client_secret"),
            "access_token": user_credentials.get("access_token"),
            "refresh_token": user_credentials.get("refresh_token")
        }
    else:
        return {
            "client_id": os.getenv("REDDIT_CLIENT_ID"),
            "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
            "access_token": user_credentials.get("access_token") if user_credentials else None,
            "refresh_token": user_credentials.get("refresh_token") if user_credentials else None
        }


def get_auth_headers(user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Get Reddit API authentication headers"""
    creds = get_reddit_credentials(user_credentials)
    access_token = creds.get("access_token")
    
    if not access_token:
        raise ValueError("ACCESS_TOKEN not found - user needs to authorize via OAuth2")
    
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "ModuleX Reddit Integration/1.0"
    }


def make_reddit_api_call(endpoint: str, method: str = "GET", data: Dict[str, Any] = None, user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make authenticated Reddit API call"""
    headers = get_auth_headers(user_credentials)
    base_url = "https://oauth.reddit.com"
    url = f"{base_url}{endpoint}"
    
    if method.upper() == "GET":
        response = requests.get(url, headers=headers, params=data)
    elif method.upper() == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method.upper() == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method.upper() == "DELETE":
        response = requests.delete(url, headers=headers)
    
    response.raise_for_status()
    return response.json()


def get_reddit_client(user_credentials: Optional[Dict[str, Any]] = None):
    """Initialize Reddit client with OAuth2 credentials."""
    try:
        import praw
    except ImportError:
        raise ValueError("praw library is required. Install with: pip install praw")
    
    creds = get_reddit_credentials(user_credentials)
    
    if not creds["client_id"] or not creds["client_secret"]:
        raise ValueError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are required")
    
    if not creds["access_token"]:
        raise ValueError("ACCESS_TOKEN required - user needs to authorize via OAuth2")
    
    return praw.Reddit(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        refresh_token=creds["refresh_token"],
        user_agent="ModuleX Reddit Integration/1.0"
    )


def format_utc_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Convert a UTC timestamp to a formatted date string."""
    return datetime.utcfromtimestamp(timestamp).strftime(format_str)


def comment_to_dict(comment) -> Optional[Dict[str, Any]]:
    """Convert PRAW comment object to dictionary."""
    try:
        from praw.models import MoreComments
        if isinstance(comment, MoreComments):
            return None
        
        return {
            "id": comment.id,
            "body": comment.body,
            "author": None if comment.author is None else comment.author.name,
            "created_utc": format_utc_timestamp(comment.created_utc),
            "is_submitter": comment.is_submitter,
            "score": comment.score,
            "replies": [
                result
                for reply in comment.replies
                if (result := comment_to_dict(reply)) is not None
            ]
        }
    except Exception:
        return None


def get_comments_by_submission(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve comments from a specific submission."""
    try:
        submission_id = parameters.get("submission_id")
        if not submission_id:
            raise ValueError("submission_id is required")
        
        replace_more = parameters.get("replace_more", True)
        
        reddit = get_reddit_client(user_credentials)
        submission = reddit.submission(submission_id)
        
        if replace_more:
            submission.comments.replace_more()
        
        comments = [
            result
            for comment in submission.comments.list()
            if (result := comment_to_dict(comment)) is not None
        ]
        
        return {
            "success": True,
            "comments": comments,
            "total": len(comments)
        }
        
    except Exception as e:
        raise ValueError(f"Failed to get comments: {str(e)}")


def get_comment_by_id(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve a specific comment by ID."""
    try:
        comment_id = parameters.get("comment_id")
        if not comment_id:
            raise ValueError("comment_id is required")
        
        reddit = get_reddit_client(user_credentials)
        comment = reddit.comment(comment_id)
        
        comment_data = comment_to_dict(comment)
        if not comment_data:
            raise ValueError("Comment not found or invalid")
        
        return {
            "success": True,
            "comment": comment_data
        }
        
    except Exception as e:
        raise ValueError(f"Failed to get comment: {str(e)}")


def get_submission(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve a specific submission by ID."""
    try:
        submission_id = parameters.get("submission_id")
        if not submission_id:
            raise ValueError("submission_id is required")
        
        reddit = get_reddit_client(user_credentials)
        submission = reddit.submission(submission_id)
        
        return {
            "success": True,
            "submission": {
                "title": submission.title,
                "url": submission.url,
                "author": None if submission.author is None else submission.author.name,
                "subreddit": submission.subreddit.display_name,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "selftext": submission.selftext,
                "created_utc": format_utc_timestamp(submission.created_utc)
            }
        }
        
    except Exception as e:
        raise ValueError(f"Failed to get submission: {str(e)}")


def get_subreddit(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve a subreddit by name."""
    try:
        subreddit_name = parameters.get("subreddit_name")
        if not subreddit_name:
            raise ValueError("subreddit_name is required")
        
        reddit = get_reddit_client(user_credentials)
        subreddit = reddit.subreddit(subreddit_name)
        
        return {
            "success": True,
            "subreddit": {
                "display_name": subreddit.display_name,
                "title": subreddit.title,
                "description": subreddit.description,
                "public_description": subreddit.public_description,
                "subscribers": subreddit.subscribers,
                "created_utc": subreddit.created_utc,
                "over18": subreddit.over18,
                "url": subreddit.url
            }
        }
        
    except Exception as e:
        raise ValueError(f"Failed to get subreddit: {str(e)}")


def search_posts(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Search for posts within a subreddit."""
    try:
        subreddit_name = parameters.get("subreddit_name")
        query = parameters.get("query")
        
        if not subreddit_name:
            raise ValueError("subreddit_name is required")
        if not query:
            raise ValueError("query is required")
        
        sort = parameters.get("sort", "relevance")
        syntax = parameters.get("syntax", "lucene")
        time_filter = parameters.get("time_filter", "all")
        limit = parameters.get("limit", 25)
        
        reddit = get_reddit_client(user_credentials)
        subreddit = reddit.subreddit(subreddit_name)
        
        posts = subreddit.search(
            query=query,
            sort=sort,
            syntax=syntax,
            time_filter=time_filter,
            limit=limit
        )
        
        post_list = [
            {
                "id": post.id,
                "title": post.title,
                "url": post.url,
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": format_utc_timestamp(post.created_utc)
            }
            for post in posts
        ]
        
        return {
            "success": True,
            "posts": post_list,
            "total": len(post_list)
        }
        
    except Exception as e:
        raise ValueError(f"Failed to search posts: {str(e)}")


def search_subreddits(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Search for subreddits using either name-based or description-based search."""
    try:
        search_type = parameters.get("search_type", "name")
        query = parameters.get("query")
        
        if not query:
            raise ValueError("query is required")
        
        reddit = get_reddit_client(user_credentials)
        
        if search_type == "name":
            include_nsfw = parameters.get("include_nsfw", False)
            exact_match = parameters.get("exact_match", False)
            subreddits = reddit.subreddits.search_by_name(
                query, exact=exact_match, include_nsfw=include_nsfw
            )
        else:  # description search
            subreddits = reddit.subreddits.search(query)
        
        include_full_description = parameters.get("include_full_description", False)
        
        subreddit_list = [
            {
                "name": subreddit.display_name,
                "public_description": subreddit.public_description,
                "description": (
                    subreddit.description if include_full_description else None
                ),
                "url": subreddit.url,
                "subscribers": subreddit.subscribers,
                "created_utc": format_utc_timestamp(subreddit.created_utc)
            }
            for subreddit in subreddits
        ]
        
        return {
            "success": True,
            "subreddits": subreddit_list,
            "total": len(subreddit_list)
        }
        
    except Exception as e:
        raise ValueError(f"Failed to search subreddits: {str(e)}")


def get_user_info(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get authenticated user information."""
    try:
        # Debug credentials first
        print(f"🔍 DEBUG get_user_info: user_credentials keys: {list(user_credentials.keys()) if user_credentials else 'None'}")
        
        # Check if we have required credentials
        if not user_credentials:
            raise ValueError("No user credentials provided - NO_CREDENTIALS")
        
        access_token = user_credentials.get("access_token")
        if not access_token:
            raise ValueError(f"No access token found in credentials. Please re-authenticate with Reddit. Available keys: {list(user_credentials.keys())}")
        
        # Debug scope information
        scope = user_credentials.get("scope", "unknown")
        print(f"🔍 DEBUG get_user_info: current scope: {scope}")
        
        # Test if token is still valid by making API call
        try:
            user_data = make_reddit_api_call("/api/v1/me", user_credentials=user_credentials)
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 401:
                raise ValueError("Access token is expired or invalid. Please re-authenticate with Reddit. - INVALID_TOKEN")
            elif http_err.response.status_code == 403:
                raise ValueError("Access denied. Check Reddit app permissions. - ACCESS_DENIED")
            else:
                raise ValueError(f"Reddit API error: {http_err.response.status_code} - {http_err.response.text} - API_ERROR")
        
        # Check required scopes for different operations
        available_scopes = scope.split() if isinstance(scope, str) else []
        scope_check = {
            "read": "read" in available_scopes,
            "identity": "identity" in available_scopes,
            "submit": "submit" in available_scopes,
            "vote": "vote" in available_scopes,
            "save": "save" in available_scopes
        }
        
        return {
            "success": True,
            "user": {
                "name": user_data.get("name"),
                "id": user_data.get("id"),
                "comment_karma": user_data.get("comment_karma"),
                "link_karma": user_data.get("link_karma"),
                "created_utc": user_data.get("created_utc"),
                "has_verified_email": user_data.get("has_verified_email"),
                "is_gold": user_data.get("is_gold"),
                "is_mod": user_data.get("is_mod")
            },
            "oauth_info": {
                "scope": scope,
                "available_scopes": scope_check,
                "missing_scopes": [k for k, v in scope_check.items() if not v],
                "permissions": {
                    "can_read": scope_check["read"] and scope_check["identity"],
                    "can_submit_posts": scope_check["submit"],
                    "can_vote": scope_check["vote"],
                    "can_access_saved": scope_check["save"]
                }
            }
        }
        
    except Exception as e:
        print(f"💥 DEBUG get_user_info exception: {str(e)}")
        raise ValueError(f"Failed to get user info: {str(e)}")


def create_post(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new post in a subreddit."""
    try:
        # Check scope before attempting operation
        scope = user_credentials.get("scope", "") if user_credentials else ""
        if "submit" not in scope:
            raise ValueError("MISSING_SCOPE: 'submit' scope required for creating posts. Please re-authenticate with Reddit to grant posting permissions.")
        
        subreddit = parameters.get("subreddit")
        title = parameters.get("title")
        content = parameters.get("content")
        post_type = parameters.get("type", "text")  # text, link, image
        
        if not subreddit or not title:
            raise ValueError("subreddit and title are required")
        
        reddit = get_reddit_client(user_credentials)
        subreddit_obj = reddit.subreddit(subreddit)
        
        if post_type == "text":
            submission = subreddit_obj.submit(title=title, selftext=content or "")
        elif post_type == "link":
            if not content:
                raise ValueError("URL is required for link posts")
            submission = subreddit_obj.submit(title=title, url=content)
        else:
            raise ValueError("Unsupported post type")
        
        return {
            "success": True,
            "post": {
                "id": submission.id,
                "title": submission.title,
                "url": submission.url,
                "permalink": f"https://reddit.com{submission.permalink}",
                "created_utc": format_utc_timestamp(submission.created_utc)
            }
        }
        
    except Exception as e:
        raise ValueError(f"Failed to create post: {str(e)}")


def vote_post(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Vote on a Reddit post."""
    try:
        # Check scope before attempting operation
        scope = user_credentials.get("scope", "") if user_credentials else ""
        if "vote" not in scope:
            raise ValueError("MISSING_SCOPE: 'vote' scope required for voting on posts. Please re-authenticate with Reddit to grant voting permissions.")
        
        submission_id = parameters.get("submission_id")
        vote_direction = parameters.get("direction")  # "up", "down", "clear"
        
        if not submission_id or not vote_direction:
            raise ValueError("submission_id and direction are required")
        
        reddit = get_reddit_client(user_credentials)
        submission = reddit.submission(submission_id)
        
        if vote_direction == "up":
            submission.upvote()
        elif vote_direction == "down":
            submission.downvote()
        elif vote_direction == "clear":
            submission.clear_vote()
        else:
            raise ValueError("Invalid vote direction. Use 'up', 'down', or 'clear'")
        
        return {
            "success": True,
            "message": f"Vote {vote_direction} applied to submission {submission_id}"
        }
        
    except Exception as e:
        raise ValueError(f"Failed to vote: {str(e)}")


def get_saved_posts(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get user's saved posts."""
    try:
        # Check scope before attempting operation
        scope = user_credentials.get("scope", "") if user_credentials else ""
        if "save" not in scope:
            raise ValueError("MISSING_SCOPE: 'save' scope required for accessing saved posts. Please re-authenticate with Reddit to grant save permissions.")
        
        limit = parameters.get("limit", 25)
        
        reddit = get_reddit_client(user_credentials)
        user = reddit.user.me()
        
        if user is None:
            raise ValueError("AUTHENTICATION_ERROR: Unable to get user information. Please re-authenticate with Reddit.")
        
        saved_items = user.saved(limit=limit)
        
        posts = []
        for item in saved_items:
            if hasattr(item, 'title'):  # It's a submission
                posts.append({
                    "id": item.id,
                    "title": item.title,
                    "url": item.url,
                    "subreddit": item.subreddit.display_name,
                    "score": item.score,
                    "created_utc": format_utc_timestamp(item.created_utc),
                    "type": "submission"
                })
            else:  # It's a comment
                posts.append({
                    "id": item.id,
                    "body": item.body[:200] + "..." if len(item.body) > 200 else item.body,
                    "subreddit": item.subreddit.display_name,
                    "score": item.score,
                    "created_utc": format_utc_timestamp(item.created_utc),
                    "type": "comment"
                })
        
        return {
            "success": True,
            "saved_items": posts,
            "total": len(posts)
        }
        
    except Exception as e:
        raise ValueError(f"Failed to get saved posts: {str(e)}")


def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        user_credentials = input_data.get("user_credentials")
        
        # Execute action based on action name
        if action == "get_comments_by_submission":
            result = get_comments_by_submission(parameters, user_credentials)
        elif action == "get_comment_by_id":
            result = get_comment_by_id(parameters, user_credentials)
        elif action == "get_submission":
            result = get_submission(parameters, user_credentials)
        elif action == "get_subreddit":
            result = get_subreddit(parameters, user_credentials)
        elif action == "search_posts":
            result = search_posts(parameters, user_credentials)
        elif action == "search_subreddits":
            result = search_subreddits(parameters, user_credentials)
        elif action == "get_user_info":
            result = get_user_info(parameters, user_credentials)
        elif action == "create_post":
            result = create_post(parameters, user_credentials)
        elif action == "vote_post":
            result = vote_post(parameters, user_credentials)
        elif action == "get_saved_posts":
            result = get_saved_posts(parameters, user_credentials)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Return result
        print(json.dumps(result))
        
    except Exception as e:
        # Return error in standardized format
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
