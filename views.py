from django.contrib.auth.models import User
from .permissions import IsParent , IsBabysitter , check_parent_approved_by_babysitter
from .serializer import MeetingsSerializer, ParentsSerializerForBabysitter, RegistrationSerializer, RequestsIsActiveSerializer, RequestsSerializer, AvailableTimeSerializer, BabysitterSerializerForParents,RequestsStatusSerializer , BabysitterSerializer , ParentsSerializer , KidsSerializer , ReviewsSerializer, MeetingsSerializerForCreating, MeetingsStatusSerializer
from .models import Babysitter, Meetings, Requests , Parents , Kids , Reviews , AvailableTime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status , permissions , viewsets , generics, exceptions
from datetime import datetime
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializer import MyTokenObtainPairSerializer
from google import genai
from decouple import config


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


####  Register ####
# Handle user registration for Babysitter/Parent roles.

@api_view(['POST'])
def register(request):
    # Create the user
    user_serializer = RegistrationSerializer(data=request.data)
    if not user_serializer.is_valid():
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializers_map = {
        'Babysitter': BabysitterSerializer,
        'Parent': ParentsSerializer,    
    }
    user_type = request.data.get('user_type', None)
    profile_type = serializers_map.get(user_type)
    if profile_type is None:
        return Response({"error" : "invalid user type"} , status=status.HTTP_400_BAD_REQUEST)

    profile_type_serializer = profile_type(data = request.data)
    if not profile_type_serializer.is_valid():
        return Response(profile_type_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = user_serializer.save()
    profile_type_serializer.save(user = user)
    return Response({"message" : f"{user_type} User created successfuly"} , status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deactivate_my_user(request):
    """
    Deactivate the currently logged-in user.
    Sets 'is_active' to False.
    """
    user = request.user
    user.is_active = False
    user.save(update_fields=["is_active"])
    return Response({"message": "User deactivated successfully"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_deactivate_user(request):
    user_type = request.data.get("user_type")
    profile_id = request.data.get("profile_id")

    if not user_type or not profile_id:
        return Response(
            {"detail": "user_type and profile_id are required."},
            status=status.HTTP_400_BAD_REQUEST)

    try:
        if user_type == "Babysitter":
            profile = Babysitter.objects.get(id=profile_id)
        elif user_type == "Parent":
            profile = Parents.objects.get(family_id=profile_id)
        else:
            return Response(
                {"detail": "Invalid user_type."},
                status=status.HTTP_400_BAD_REQUEST)
    except (Babysitter.DoesNotExist, Parents.DoesNotExist):
        return Response(
            {"detail": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND)

    if not profile.user:
        return Response(
            {"detail": "This profile has no connected user."},
            status=status.HTTP_400_BAD_REQUEST)

    profile.user.is_active = False
    profile.user.save(update_fields=["is_active"])

    return Response(
        {"message": "User deactivated successfully."},
        status=status.HTTP_200_OK)


##########################################################################################################################################



#### My Profile ####


"""
API view for babysitters to retrieve or update their profile.
"""
class BabysitterMe(generics.RetrieveUpdateAPIView):
    serializer_class = BabysitterSerializer
    permission_classes = [IsBabysitter]

    def get_object(self):
        if self.request.user.is_superuser:
            babysitter_id = self.request.query_params.get("babysitter_id")
            if babysitter_id:
                try:
                    return Babysitter.objects.get(id=babysitter_id)
                except Babysitter.DoesNotExist:
                    raise exceptions.NotFound("Babysitter profile not found.")
            raise exceptions.ValidationError("babysitter_id is required for superuser.")

        try:
            return Babysitter.objects.get(user=self.request.user)
        except Babysitter.DoesNotExist:
            raise exceptions.NotFound("Babysitter profile not found.")
"""
API view for parents to retrieve or update their profile.
"""
class ParentMe(generics.RetrieveUpdateAPIView):
    serializer_class = ParentsSerializer
    permission_classes = [IsParent]

    def get_object(self):
        if self.request.user.is_superuser:
            parent_id = self.request.query_params.get("parent_id")
            if parent_id:
                try:
                    return Parents.objects.get(family_id=parent_id)
                except Parents.DoesNotExist:
                    raise exceptions.NotFound("Parent profile not found.")
            raise exceptions.ValidationError("parent_id is required for superuser.")

        try:
            return Parents.objects.get(user=self.request.user)
        except Parents.DoesNotExist:
            raise exceptions.NotFound("Parent profile not found.")

##########################################################################################################################################



#### BabySitter ####


class BabysitterListView(generics.ListAPIView):
    """
    Retrieve and display a list of all babysitters.
    This view is used by parents.
    """
    queryset = Babysitter.objects.filter(user__is_active=True)
    serializer_class = BabysitterSerializerForParents
    permission_classes = [IsParent]

##########################################################################################################################################



#### Parent ####


class ParentsListView(generics.ListAPIView):
    """
    Retrieve and display a list of all parents.
    This view is used by babysitters.
    """
    queryset = Parents.objects.filter(user__is_active=True)
    serializer_class = ParentsSerializerForBabysitter
    permission_classes = [IsBabysitter]

##########################################################################################################################################



#### Kids ####


class KidsListView(generics.ListAPIView):
    """
    Retrieve and display a list of kids for a given parent id.
    This view is used by babysitters.    
    """
    serializer_class = KidsSerializer
    permission_classes = [IsBabysitter]

    def get_queryset(self):
        parent_id = self.request.query_params.get('parent_id')
        if not parent_id:
            raise exceptions.ValidationError("parent_id is required.")
        try:
            parent=Parents.objects.get(family_id=parent_id)
        except Parents.DoesNotExist:
            raise exceptions.NotFound("Parent not found")
        return Kids.objects.filter(family=parent)

# create+read+update
class KidsCreate(generics.CreateAPIView):
    """
    Allows authenticated parents to add a child to their profile.
    Fields required for creating a kid:
    - **name** (str): The name of the kid.
    - **age** (int): The age of the kid.
    - (The `family` field is automatically associated with the currently logged-in parent.)
    """

    queryset = Kids.objects.all()
    serializer_class = KidsSerializer  # input uses only name/age in this serializer
    permission_classes = [IsParent]

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        # Validate incoming data (name, age)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Resolve current parent's family
        try:
            family = Parents.objects.get(user=request.user)
        except Parents.DoesNotExist:
            return Response({"detail": "Family does not exist."},status=status.HTTP_404_NOT_FOUND)

        if is_many:
            created_kids = [ 
                Kids.objects.create( family=family,name=kid['name'],age=kid['age'])
                for kid in serializer.validated_data ]
            return Response(KidsSerializer(created_kids, many=True).data,status=status.HTTP_201_CREATED)

        # single object path
        data = serializer.validated_data
        kid = Kids.objects.create(family=family,name=data['name'],age=data['age'])
        return Response(KidsSerializer(kid).data, status=status.HTTP_201_CREATED)



class KidsActions(generics.RetrieveUpdateAPIView):
    """
    Get kid info for the given kid id.
    Perform the update only if the logged-in user is the parent associated with the kid.
    """
    queryset = Kids.objects.all()
    serializer_class = KidsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        kid = self.get_object()
        parent = kid.family        
        if parent.user != self.request.user:
            raise exceptions.PermissionDenied("You do not have permission to update this kid.")

        serializer.save()
    
##########################################################################################################################################



#### Available Time ####


class AvailableTimeListView(generics.ListAPIView):
    """
    Retrieve and a list of all available time slots for a given babysitter id.
    This view is used by parents. 
    """
    serializer_class = AvailableTimeSerializer
    permission_classes = [IsParent]

    def get_queryset(self):
        babysitter_id = self.request.query_params.get('babysitter_id')
        if not babysitter_id:
            raise exceptions.ValidationError("babysitter_id is required.")
        try:
            babysitter = Babysitter.objects.get(id=babysitter_id)
        except Babysitter.DoesNotExist:
            raise exceptions.NotFound("Babysitter not found.")

        try:
            parents = Parents.objects.get(user=self.request.user)
        except Parents.DoesNotExist:
            raise exceptions.NotFound("Parent profile not found.")

        if not check_parent_approved_by_babysitter(babysitter, parents):
            # Deny if they’re not approved to see availability
            raise exceptions.PermissionDenied("Parent not approved by babysitter.")
        return AvailableTime.objects.filter(babysitter=babysitter).order_by('date', 'start_time')
        
class AvailableTimeActions(viewsets.ModelViewSet):
    """
    Manage the available time slots for the logged-in babysitter.
    Allows viewing, adding, editing, or removing time slots for the babysitter's availability.
    """
    queryset = AvailableTime.objects.all()
    serializer_class = AvailableTimeSerializer
    permission_classes = [IsBabysitter]

    def get_queryset(self):
        return AvailableTime.objects.filter(babysitter__user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            babysitter = Babysitter.objects.get(user=request.user)
        except Babysitter.DoesNotExist:
            return Response({"detail": "Babysitter does not exist."}, status=status.HTTP_404_NOT_FOUND)
        
        # Create the availability time
        available_time = AvailableTime.objects.create( 
            babysitter = babysitter, 
            date=serializer.validated_data['date'],
            start_time = serializer.validated_data['start_time'], 
            end_time = serializer.validated_data['end_time'] )
        return Response(self.get_serializer(available_time).data,status=status.HTTP_201_CREATED)

    
    def partial_update(self, request, *args, **kwargs):
        upd_time = self.get_object()
        # Handle partial updates
        serializer = self.get_serializer(upd_time, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

##########################################################################################################################################
   


#### Requests ####


class RequestsViewSet(generics.CreateAPIView):
    """
    Allows authenticated parents to add a request.
    Fields required for creating a request:
    - **babysitter_id** (int): The id of the babysitter.
    """
    serializer_class = RequestsSerializer
    permission_classes = [IsParent]

    def create(self, request, *args, **kwargs):  
        try:
            parents = Parents.objects.get(user=request.user)
        except Parents.DoesNotExist:
            return Response({"detail": "Family does not exist"},status=status.HTTP_404_NOT_FOUND)

        babysitter_id = request.data.get('babysitter_id')
        if not babysitter_id:
            return Response({"detail": "babysitter_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            babysitter = Babysitter.objects.get(id=babysitter_id)
        except Babysitter.DoesNotExist:
            return Response({"detail": "Babysitter does not exist."},status=status.HTTP_404_NOT_FOUND)

        if Requests.objects.filter(family=parents, babysitter=babysitter, is_active=True).exists():
            return Response({"detail": "Request already exists."}, status=status.HTTP_409_CONFLICT)

        # Create the Request and associate it with the parent
        new_request = Requests.objects.create(
           family=parents,
            babysitter=babysitter,
            status='pending',
            is_active=True )
        return Response({"detail":"Request created successfully"} ,status=status.HTTP_201_CREATED)

class ShowRequests(generics.ListAPIView):
    """
    Show all requests info created by the logged-in parent / sent to the logged-in babysitter.    
    """
    serializer_class = RequestsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Requests.objects.filter(is_active=True)
        if hasattr(user, 'Parent'):
            return Requests.objects.filter(family__user=user, is_active=True)
        elif hasattr(user, 'Babysitter'):
            return Requests.objects.filter(babysitter__user=user, is_active=True)
        return Requests.objects.none()

class RequestDeactivate(generics.RetrieveUpdateAPIView):
    """
    Allows authenticated babysitters and parents to set is_active=False
    on requests that belong to them.
    """
    serializer_class = RequestsIsActiveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Requests.objects.all()
        if hasattr(user, 'Parent'):
            return Requests.objects.filter(family__user=user)
        if hasattr(user, 'Babysitter'):
            return Requests.objects.filter(babysitter__user=user)
        return Requests.objects.none()

class RequestActionsForBabysitter(generics.RetrieveUpdateAPIView):
    """
    Allows authenticated babysitters to get/edit request status of the requests sent to them.
    """
    serializer_class = RequestsStatusSerializer
    permission_classes = [IsBabysitter]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Requests.objects.all()
        return Requests.objects.filter(babysitter__user=self.request.user)

    def perform_update(self, serializer):
        # Save the update
        updated_request = serializer.save()
        # Automatically deactivate declined requests
        if updated_request.status.lower() == 'declined':
            updated_request.is_active = False
            updated_request.save(update_fields=['is_active'])
    
##########################################################################################################################################



 ## Ai


@api_view(["POST"]) 
@permission_classes([IsParent])
def generate_ai_time_request(request):
    """
    This view uses the OpenAI API to generate a polite babysitting time request message.
    The parent is already inside a specific babysitter's availability page, so the frontend sends the babysitter_id automatically.
    The AI uses the babysitter name, requested date, requested time, and optional parent note to create the message.
    """
    babysitter_id = request.data.get("babysitter_id")
    date = request.data.get("date")
    start_time = request.data.get("start_time")
    end_time = request.data.get("end_time")
    note = request.data.get("note", "")

    if not babysitter_id or not date or not start_time or not end_time:
        return Response(
            {"detail": "babysitter_id, date, start_time, and end_time are required."},
            status=status.HTTP_400_BAD_REQUEST)

    try:
        babysitter = Babysitter.objects.get(id=babysitter_id)
    except Babysitter.DoesNotExist:
        return Response(
            {"detail": "Babysitter not found."},
            status=status.HTTP_404_NOT_FOUND)

    try:
        client = genai.Client(api_key=config("GEMINI_API_KEY"))
        prompt = f"""
        Write a short and polite babysitting request message from a parent to a babysitter.

        Babysitter name: {babysitter.name}
        Requested date: {date}
        Requested time: {start_time} to {end_time}
        Parent note: {note}

        The message should ask if the babysitter can help at this date and time.
        Keep it friendly, clear, and not longer than 4 sentences. dont add *
        """

        ai_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,)

        return Response(
            {"message": ai_response.text},status=status.HTTP_200_OK)

    except Exception as e:
        print("OPENAI ERROR:", e)
        return Response(
            {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def unread_messages_count(request):
    """
    This view returns how many unread AI messages the logged-in user has.
    Babysitters get a count of new pending AI requests from parents.
    Parents get a count of AI requests that were answered by the babysitter.
    """
    user = request.user

    if hasattr(user, "Babysitter"):
        count = Meetings.objects.filter(
            babysitter__user=user,
            is_ai_request=True,
            is_message_read_by_babysitter=False,
            status="pending"
        ).count()
        return Response({"count": count}, status=status.HTTP_200_OK)

    if hasattr(user, "Parent"):
        count = Meetings.objects.filter(
            family__user=user,
            is_ai_request=True,
            is_message_read_by_parent=False
        ).exclude(status="pending").count()
        return Response({"count": count}, status=status.HTTP_200_OK)

    return Response({"count": 0}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_ai_messages_read(request):
    """
    This view marks AI messages as read after the user opens the Messages page.
    For babysitters, it marks pending AI requests as read.
    For parents, it marks answered AI request responses as read.
    """
    user = request.user

    if hasattr(user, "Babysitter"):
        Meetings.objects.filter(
            babysitter__user=user,
            is_ai_request=True,
            is_message_read_by_babysitter=False
        ).update(is_message_read_by_babysitter=True)

    if hasattr(user, "Parent"):
        Meetings.objects.filter(
            family__user=user,
            is_ai_request=True,
            is_message_read_by_parent=False
        ).exclude(status="pending").update(is_message_read_by_parent=True)

    return Response({"message": "Messages marked as read."}, status=status.HTTP_200_OK)

##########################################################################################################################################



#### Meetings ####



class CreateMeetingView(generics.CreateAPIView):
    """
    Parent sends a meeting REQUEST to a babysitter (status='pending'),
    even if the requested time is not in AvailableTime.
    Babysitter later approves/declines.
    """
    serializer_class = MeetingsSerializerForCreating
    permission_classes = [IsParent]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Parent (logged-in)
        try:
            parent = Parents.objects.get(user=request.user)
        except Parents.DoesNotExist:
            return Response({"detail": "Parent profile not found."},status=status.HTTP_404_NOT_FOUND)

        # Babysitter id
        babysitter_id = request.data.get("babysitter_id")
        if not babysitter_id:
            return Response({"detail": "babysitter_id is required."},status=status.HTTP_400_BAD_REQUEST)

        try:
            babysitter = Babysitter.objects.get(id=babysitter_id)
        except Babysitter.DoesNotExist:
            return Response({"detail": "Babysitter does not exist."},status=status.HTTP_404_NOT_FOUND)

        if not check_parent_approved_by_babysitter(babysitter, parent):
            return Response({"detail": "Parent not approved by babysitter!"}, status=status.HTTP_403_FORBIDDEN)

        # Times
        start_time = serializer.validated_data["start_time"]
        end_time = serializer.validated_data["end_time"]

        if start_time >= end_time:
            return Response({"detail": "start_time must be before end_time."},status=status.HTTP_400_BAD_REQUEST)

        # AI message fields
        message = request.data.get("message", "")
        is_ai_request = request.data.get("is_ai_request", False)

        # If the availability already exists, the parent should use the regular "Request this" button instead.
        if is_ai_request:
            existing_availability = AvailableTime.objects.filter(
                babysitter=babysitter,
                date=start_time.date(),
                start_time=start_time.time(),
                end_time=end_time.time()
            ).exists()

            if existing_availability:
                return Response(
                    {"detail": "This time already exists in the babysitter availability."}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent duplicate pending request with same exact times
        if Meetings.objects.filter(
            babysitter=babysitter,
            family=parent,
            start_time=start_time,
            end_time=end_time,
            status="pending").exists():
            return Response({"detail": "A pending request for this exact time already exists."},status=status.HTTP_409_CONFLICT)

        # Prevent overlap with APPROVED meetings (back-to-back is allowed)
        has_conflict = Meetings.objects.filter(
            babysitter=babysitter,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status="approved").exists()
        if has_conflict:
            return Response({"detail": "Babysitter already booked for this time."},status=status.HTTP_400_BAD_REQUEST)
     
        # Create pending meeting request
        meeting = Meetings.objects.create(
            babysitter=babysitter,
            family=parent,
            start_time=start_time,
            end_time=end_time,
            status="pending",
            message=message,
            is_ai_request=is_ai_request,
            is_message_read_by_babysitter=False,
            is_message_read_by_parent=True)
        return Response(self.get_serializer(meeting).data, status=status.HTTP_201_CREATED)

class ShowMeetings(generics.ListAPIView):
    """
    Show meetings for the logged-in user:
      - Parent -> meetings for their family
      - Babysitter -> their meetings
    """
    serializer_class = MeetingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Meetings.objects.all().order_by("-start_time")
        if hasattr(user, "Parent"):
            return Meetings.objects.filter(family__user=user).order_by("-start_time")
        if hasattr(user, "Babysitter"):
            return Meetings.objects.filter(babysitter__user=user).order_by("-start_time")
        return Meetings.objects.none()

class MeetingActionsForBabysitter(generics.RetrieveUpdateAPIView):
    """
    Allows authenticated babysitters to get/edit meeting status of the meetings waits for them.
    """
    serializer_class = MeetingsStatusSerializer
    permission_classes = [IsBabysitter]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Meetings.objects.all()
        return Meetings.objects.filter(babysitter__user=self.request.user)

    def perform_update(self, serializer):
        meeting = serializer.save()
        if meeting.is_ai_request and meeting.status in ["approved", "declined"]:
            meeting.is_message_read_by_parent = False
            meeting.save(update_fields=["is_message_read_by_parent"])

class BabysitRequestCreate(generics.CreateAPIView):
    """
    Allows a parent to create a babysit meeting request based on a babysitter's available time slot.
    The meeting is created in 'pending' status until the babysitter approves it.
    """
    serializer_class = MeetingsSerializerForCreating
    permission_classes = [IsParent]

    def create(self, request, *args, **kwargs):
        # Get parent
        try:
            parent = Parents.objects.get(user=request.user)
        except Parents.DoesNotExist:
            return Response({"detail": "Parent profile not found."}, status=status.HTTP_404_NOT_FOUND)

        babysitter_id = request.data.get('babysitter_id')
        slot_id = request.data.get('slot_id')

        if not babysitter_id or not slot_id:
            return Response({"detail": "babysitter_id and slot_id are required."},status=status.HTTP_400_BAD_REQUEST)

        # Get babysitter + slot
        try:
            babysitter = Babysitter.objects.get(id=babysitter_id)
            slot = AvailableTime.objects.get(id=slot_id, babysitter=babysitter)
        except Babysitter.DoesNotExist:
            return Response({"detail": "Babysitter not found."},status=status.HTTP_404_NOT_FOUND)
        except AvailableTime.DoesNotExist:
            return Response({"detail": "Availability slot not found for this babysitter."},status=status.HTTP_404_NOT_FOUND)

        # Ensure the parent is approved by babysitter
        if not check_parent_approved_by_babysitter(babysitter, parent):
            return Response({"detail": "Parent not approved by babysitter."}, status=status.HTTP_403_FORBIDDEN)

        # Combine slot date + time into datetime 
        start_dt = datetime.combine(slot.date, slot.start_time)
        end_dt = datetime.combine(slot.date, slot.end_time)

        # Prevent duplicate pending request for same parent+babysitter+slot
        if Meetings.objects.filter(
            babysitter=babysitter,
            family=parent,
            start_time=start_dt,
            end_time=end_dt,
            status='pending').exists():
            return Response({"detail": "A pending request for this time already exists."},status=status.HTTP_409_CONFLICT)

        # Prevent overlap with approved meetings
        overlapping_approved_meeting = Meetings.objects.filter(
            babysitter=babysitter,
            start_time__lt=end_dt,
            end_time__gt=start_dt,
            status='approved').exists()
        if overlapping_approved_meeting:
            return Response({"detail": "Babysitter already booked for this time."},status=status.HTTP_400_BAD_REQUEST)

        # Create new meeting request
        meeting = Meetings.objects.create(
            babysitter=babysitter,
            family=parent,
            start_time=start_dt,
            end_time=end_dt,
            status='pending')
        return Response({"detail": "Babysit request sent successfully.","meeting_id": meeting.id},status=status.HTTP_201_CREATED)

class MeetingActions(generics.RetrieveUpdateAPIView):
    """
    Allow the meeting's babysitter **or** parent to view/update its status.
    """
    serializer_class = MeetingsStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Meetings.objects.all()
        # allow only meetings that belong to this user (as parent OR babysitter)
        return (Meetings.objects.filter(family__user=user) | Meetings.objects.filter(babysitter__user=user)).distinct()

    def get_object(self):
        meeting_id = self.request.query_params.get('meeting_id')
        if not meeting_id:
            raise exceptions.ValidationError("meeting_id is required.")

        try:
            meeting_id = int(meeting_id)
        except ValueError:
            raise exceptions.ValidationError("meeting_id must be a number.")

        try:
            obj = self.get_queryset().get(id=meeting_id)
        except Meetings.DoesNotExist:
            raise exceptions.NotFound("Meeting not found.")
        return obj

##########################################################################################################################################



#### Reviews ####


class ReviewsViewSet(viewsets.ModelViewSet):
    """
    Manage the reviews created by the logged-in parent.
    Allows parents to viewing, adding, editing, or removing their own reviews.
    """
    queryset = Reviews.objects.all()     
    serializer_class = ReviewsSerializer
    permission_classes = [IsParent]

    def create(self , request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            parent = Parents.objects.get(user=request.user)
        except Parents.DoesNotExist:
            return Response({"detail": "Parent profile not found."}, status=status.HTTP_404_NOT_FOUND)

        babysitter_id = request.data.get("babysitter_id")
        if not babysitter_id:
            return Response({"detail": "babysitter_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            babysitter = Babysitter.objects.get(id=babysitter_id)
        except Babysitter.DoesNotExist:
            return Response({"detail": "Babysitter does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if not check_parent_approved_by_babysitter(babysitter, parent):
            return Response({"detail": "Parent not approved by babysitter!"}, status=status.HTTP_403_FORBIDDEN)

        review = Reviews.objects.create(
            family=parent,
            babysitter=babysitter,
            review_text=serializer.validated_data["review_text"],
            rating=serializer.validated_data["rating"])
        return Response(self.get_serializer(review).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Reviews.objects.all()
        return Reviews.objects.filter(family__user=self.request.user)
    
class ShowReviews(generics.ListAPIView):
    """
    Retrieve a list of all reviews for a given babysitter id.
    This view is used by both parents and babysitters. 
    """
    serializer_class = ReviewsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Read babysitter_id from query string 
        babysitter_id = self.request.query_params.get('babysitter_id')
        if not babysitter_id:
            raise exceptions.ValidationError("babysitter_id is required")
        return Reviews.objects.filter(babysitter__id=babysitter_id)

##########################################################################################################################################