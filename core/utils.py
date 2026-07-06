import os
import json
import datetime
from django.utils import timezone

def get_daily_ai_news(user):
    """
    Fetches daily news based on user's interested topics using DuckDuckGo Search,
    and summarizes them using Groq API (if available). Results are cached per day.
    """
    if not user.interested_topics:
        return None
        
    today = timezone.now().date()
    if user.news_last_fetched == today and user.daily_news_cache:
        return user.daily_news_cache
        
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"title": "Missing Package", "description": "Please pip install duckduckgo-search", "link": "#"}]
        
    topics = user.interested_topics
    
    try:
        # Search the web for the user's topics
        raw_results = list(DDGS().text(f"{topics} tech news", max_results=5))
    except Exception as e:
        return [{"title": "Web Search Error", "description": str(e), "link": "#"}]
        
    groq_api_key = os.environ.get('GROQ_API_KEY')
    
    formatted_news = []
    
    if groq_api_key:
        try:
            import groq
            client = groq.Groq(api_key=groq_api_key)
            
            prompt = (
                f"You are an AI news summarizer. Here are raw web search results for '{topics}':\n"
                f"{json.dumps(raw_results)}\n\n"
                "Extract the 3 most relevant items. For each item, provide a highly engaging 2-sentence description. "
                "Return ONLY a valid JSON array of objects with keys: 'title', 'description', 'link'."
            )
            
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            response_text = chat_completion.choices[0].message.content
            # Groq returns a JSON object when response_format is json_object. It usually wraps the array.
            data = json.loads(response_text)
            
            # Extract the array from the JSON response
            for key in data:
                if isinstance(data[key], list):
                    formatted_news = data[key]
                    break
            if not formatted_news and isinstance(data, list):
                formatted_news = data
                
        except Exception as e:
            # Fallback if Groq API fails
            print(f"Groq API Error: {e}")
            pass
            
    # Fallback to pure DuckDuckGo results if Groq wasn't used or failed
    if not formatted_news:
        for res in raw_results[:4]:
            formatted_news.append({
                'title': res.get('title', 'Unknown Title'),
                'description': res.get('body', 'No description available.'),
                'link': res.get('href', '#')
            })
            
    # Cache the results for today
    user.daily_news_cache = formatted_news
    user.news_last_fetched = today
    user.save(update_fields=['daily_news_cache', 'news_last_fetched'])
    
    return formatted_news
