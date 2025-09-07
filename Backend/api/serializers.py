from rest_framework import serializers
from .models import project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = project
        fields = '__all__'

# --- Contract v1.0 for /api/search ---
class QuerySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    subject = serializers.CharField(max_length=200)
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    industry = serializers.CharField(max_length=120, required=False, allow_blank=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=30)

class EngagementSerializer(serializers.Serializer):
    score = serializers.IntegerField(required=False)
    num_comments = serializers.IntegerField(required=False)
    upvote_ratio = serializers.FloatField(required=False)

class EngagementDerivedSerializer(serializers.Serializer):
    hours_since_post = serializers.FloatField(required=False)
    upvotes_per_hour = serializers.FloatField(required=False)
    comments_per_hour = serializers.FloatField(required=False)

class PostSerializer(serializers.Serializer):
    post_id = serializers.CharField()
    source = serializers.CharField()
    url = serializers.URLField()
    title = serializers.CharField(allow_blank=True)
    text = serializers.CharField(allow_blank=True)
    published_ts = serializers.IntegerField(required=False)
    author = serializers.CharField(required=False, allow_blank=True)

    engagement = EngagementSerializer(required=False)
    engagement_derived = EngagementDerivedSerializer(required=False)
