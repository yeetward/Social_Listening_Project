from typing import Any, Dict


def feature_extraction(article: Dict[str,Any]) -> Dict[str,Any]:

   # Extract title, body, engagement
   '''
   Extract everything from mongoDB and then assign variables to each feature
   '''

   title = article.get("title", "")
   body = article.get("body", "")
   engagement = article.get("engagement", {})

   full_text = f"{title} {body}"

   # Extract Engagement metrics
   # TODO: update with the new extraction
   if isinstance(engagement, dict):
    likes = engagement.get("likes", 0)
    comments = engagement.get("comments", 0)
    shares = engagement.get("shares", 0)
    total_engagement = likes + comments + shares
   else:
    total_engagement = 0

    '''
    Calculate metrics based on the features
    '''

   # Text length features
   word_count = len(full_text.split())
   char_count = len(full_text)

   # check for images/videos/links
   has_images = "image" in body.lower() or "photo" in body.lower() or "img" in body.lower()
   has_video = "video" in body.lower() or "watch" in body.lower()
   has_links = "http" in body or "www." in body

   # check for urgency indicators
   urgency_keywords = ["breaking", "urgent", "alert", "now", "today", "just in", "update"]
   is_urgent = any(keyword in full_text.lower() for keyword in urgency_keywords)

   # long-form indicators
   has_sections = any(marker in body for marker in ["\n\n","##","###"])
   has_detailed_analysis = word_count > 500 
   
   # Social media indicators
   has_hashtags = "#" in full_text
   has_mentions = "@" in full_text
   is_short_form = word_count < 150

   # email indicators
   is_personalized = any(word in full_text.lower() for word in ["you","your","subscribe"])
   has_cta = any(phrase in full_text.lower() for phrase in ["click", "read more", "learn more", "sign up"])

   return {
        "word_count": word_count,
        "char_count": char_count,
        "total_engagement": total_engagement,
        "has_images": has_images,
        "has_video": has_video,
        "has_links": has_links,
        "is_urgent": is_urgent,
        "has_sections": has_sections,
        "has_detailed_analysis": has_detailed_analysis,
        "has_hashtags": has_hashtags,
        "has_mentions": has_mentions,
        "is_short_form": is_short_form,
        "is_personalized": is_personalized,
        "has_cta": has_cta,
    }

