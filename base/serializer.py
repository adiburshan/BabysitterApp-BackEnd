from rest_framework import serializers
from .models import Babysitter, Meetings, Requests , Parents , Kids , Reviews , AvailableTime 
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import check_password



__all__ = ["RegistrationSerializer", "BabysitterSerializer", "BabysitterSerializerForParents", "KidsSerializer",
           "ParentsSerializer", "ParentsSerializerForBabysitter", "MeetingsSerializer", "MeetingsSerializerForCreating",
            "ReviewsSerializer", "AvailableTimeSerializer", "RequestsSerializer", "RequestsIsActiveSerializer",
            "RequestsStatusSerializer", "MeetingsStatusSerializer"]

##########################################################################################################################################



class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = TokenObtainPairSerializer.get_token(user)
        token["is_superuser"] = user.is_superuser
        if Babysitter.objects.filter(user=user).exists():
            token["user_type"] = "Babysitter"
        elif Parents.objects.filter(user=user).exists():
            token["user_type"] = "Parent"
        else:
            token["user_type"] = None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["is_superuser"] = self.user.is_superuser
        if Babysitter.objects.filter(user=self.user).exists():
            data["user_type"] = "Babysitter"
        elif Parents.objects.filter(user=self.user).exists():
            data["user_type"] = "Parent"
        else:
            data["user_type"] = None
        return data

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username' , 'email' , 'password']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
        
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value
    def validate_password(self, value):
        for user in User.objects.all():
            if check_password(value, user.password):
                raise serializers.ValidationError("This password is already used by another user.")
        return value
            
##########################################################################################################################################

## Babysitter ##
class BabysitterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Babysitter
        fields = ['id', 'name', 'age', 'address', 'hourly_rate', 'description', 'profile_picture', 'user']


class BabysitterSerializerForParents(serializers.ModelSerializer):
    class Meta:
        model = Babysitter
        fields = ['id', 'name', 'age', 'address', 'hourly_rate', 'description', 'profile_picture' ]     

##########################################################################################################################################

## Kids + Parents ##
class KidsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kids
        fields = ['id', 'name', 'age']


class ParentsSerializer(serializers.ModelSerializer):
    kids = KidsSerializer(many=True, read_only=True)
    class Meta:
        model = Parents
        fields = ['dad_name', 'mom_name', 'last_name', 'phone_number', 'address', 'profile_picture', 'user', 'kids']

   
class ParentsSerializerForBabysitter(serializers.ModelSerializer):
    kids = KidsSerializer(many=True, read_only=True)
    class Meta:
        model = Parents
        fields = ['family_id', 'dad_name', 'mom_name', 'last_name', 'phone_number', 'address', 'profile_picture', 'kids']

        def get_phone_number(self, obj):
            request = self.context.get("request")

            if not request or not request.user.is_authenticated:
                return None

            if request.user.is_superuser:
                return obj.phone_number

            approved_request_exists = Requests.objects.filter(
                family=obj,
                babysitter__user=request.user,
                status="approved",
                is_active=True
            ).exists()

            if approved_request_exists:
                return obj.phone_number

            return None
        
##########################################################################################################################################

## Meetings ##
class MeetingsSerializerForCreating(serializers.ModelSerializer):
    class Meta:
        model = Meetings
        fields = ['start_time', 'end_time', 'message', 'is_ai_request']

class MeetingsStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meetings
        fields = ['id', 'status']

# General listing serializer (used by ShowMeetings)
class MeetingsSerializer(serializers.ModelSerializer):
    babysitter_id = serializers.IntegerField(source='babysitter.id', read_only=True)
    babysitter_name = serializers.CharField(source='babysitter.user.username', read_only=True)
    family_id = serializers.IntegerField(source='family.id', read_only=True)
    family_name = serializers.CharField(source='family.user.username', read_only=True)

    class Meta:
        model = Meetings
        fields = ['id','babysitter_id', 'babysitter_name','family_id', 'family_name','start_time', 'end_time', 'status','message', 'is_ai_request', 'is_message_read_by_babysitter', 'is_message_read_by_parent', 'created_time']
        read_only_fields = ['id','babysitter_id', 'babysitter_name','family_id', 'family_name','created_time']

##########################################################################################################################################

## Reviews ##
class ReviewsSerializer(serializers.ModelSerializer):
    reviewer = serializers.SerializerMethodField(read_only=True)
    created_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Reviews
        fields = ['review_text', 'rating', 'created_time', 'reviewer']

    def get_reviewer(self, obj):
        """
        Return the parent's name automatically using the related Parent
        """
        parent = obj.family
        return str(parent) if parent else "Unknown"

##########################################################################################################################################

## Available time ##
class AvailableTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableTime
        fields = ['id', 'date', 'start_time', 'end_time']
        read_only_fields = ['id', 'babysitter']

    def validate(self, data):
            if data.get('start_time') and data.get('end_time'):
                if data['start_time'] >= data['end_time']:
                    raise serializers.ValidationError("start_time must be before end_time.")
            return data

##########################################################################################################################################

## Request ##
class RequestsSerializer(serializers.ModelSerializer):
    family_name = serializers.SerializerMethodField(read_only=True)
    babysitter_name = serializers.SerializerMethodField(read_only=True)
    babysitter_profile_picture = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Requests
        fields = "__all__"

    def get_family_name(self, obj):
        dad_name = obj.family.dad_name
        mom_name = obj.family.mom_name
        last_name = obj.family.last_name
        return f"{dad_name} & {mom_name} {last_name}".strip()

    def get_babysitter_name(self, obj):
        return obj.babysitter.name

    def get_babysitter_profile_picture(self, obj):
        return obj.babysitter.profile_picture.url if obj.babysitter.profile_picture else None    

class RequestsStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requests
        fields = ['id', 'status']

class RequestsIsActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requests
        fields = ['id', 'is_active', 'status']

##########################################################################################################################################