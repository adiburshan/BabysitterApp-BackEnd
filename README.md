# Babysitter App Backend

This is the backend for a Babysitter Management Application built with **Django** and **Django REST Framework**.  
The system allows parents and babysitters to register, manage profiles, create friend requests, manage availability, schedule babysitting meetings, write reviews, and gives a superuser/admin the ability to view and manage existing data.


## Backend Structure

The backend is organized into Django app files:
- models.py defines the database tables, such as Babysitter, Parents, Kids, AvailableTime, Meetings, Reviews, and Requests.
- serializer.py validates incoming data and converts model objects into JSON responses.
- views.py contains the API logic for registration, profiles, requests, availability, meetings, reviews, and admin actions.
- permissions.py contains custom permission classes for parents, babysitters, and superusers.
- urls.py connects the API endpoints to their views.
- admin.py registers the models so they can be managed through Django Admin.


## Project Structure:

backend/
├── base/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializer.py
│   ├── urls.py
│   └── views.py
├── myproj/
│   ├── settings.py
│   └── urls.py
├── manage.py
├── requirements.txt
├── Dockerfile
└── .dockerignore


## Project Overview

The backend supports three main user types:

1. **Parent**
   - Can register and create a family profile.
   - Can add and update kids.
   - Can view babysitters.
   - Can send friend requests to babysitters.
   - Can view babysitter availability.
   - Can create babysitting meeting requests.
   - Can write reviews after being approved by a babysitter.

2. **Babysitter**
   - Can register and create a babysitter profile.
   - Can manage availability time slots.
   - Can view parents.
   - Can approve or decline friend requests.
   - Can approve or decline babysitting meeting requests.
   - Can view reviews written by parents.

3. **Superuser / Admin**
   - Can log in.
   - Receives `is_superuser` in the login response and token.
   - Can view and manage existing data.
   - Can deactivate parent or babysitter accounts.
   - Can access Django Admin to manage database records.

The backend uses Django’s built-in `User` model and connects each app profile to a user through a one-to-one relationship. Babysitters and parents both have their own profile models connected to `User`. 


## Technologies Used

- Python
- Django
- Django REST Framework
- Simple JWT Authentication
- SQLite
- Django Admin
- CORS Headers
- Media file uploads for profile pictures
- Gemini API
- python-decouple for environment variables

The project is configured to use Django REST Framework with JWT authentication through rest_framework_simplejwt.authentication.JWTAuthentication. 


## Main Features

- JWT authentication for parents, babysitters, and admin users
- Parent and babysitter profile management
- Kids management for parent profiles
- Friend request system between parents and babysitters
- Babysitter availability management
- Babysitting meeting request system
- Real AI message helper using the Gemini API
- AI alternative time request messages between parents and babysitters
- Messages notification system for unread AI requests and responses
- Reviews and ratings for babysitters
- Admin support for viewing and managing existing data

## User Roles and Permissions

This allows the admin to view and manage existing data while still keeping the parent/babysitter permissions for normal users.
The backend contains custom permission classes:

IsParent
Allows access if the logged-in user is a parent or a superuser

IsBabysitter
Allows access if the logged-in user is a babysitter or a superuser


## Database Models

Babysitter
Represents a babysitter profile (Main fields: name, age, address, hourly_rate, description, profile_picture)
Each babysitter is connected to one Django User

Parents
Represents a family profile (Main fields: dad_name, mom_name, last_name, address, profile_picture)
Each parent profile is connected to one Django User

Kids
Represents children connected to a family profile (Main fields: family, name, age, created_time)
Each kid belongs to one parent profile

AvailableTime
Represents babysitter availability time slots (Main fields: babysitter, date, start_time, end_time)
Each availability slot belongs to one babysitter

Meetings
Represents babysitting meeting requests from parents (Main fields: start_time, end_time, family, babysitter, status, message, is_ai_request, is_message_read_by_babysitter, is_message_read_by_parent)
Statuses: pending, approved, declined, cancelled
A meeting connects one family with one babysitter
AI-generated custom requests are also saved as meeting requests, so the babysitter can approve or decline them.

Reviews
Represents reviews written by parents for babysitters (Main fields: family, babysitter, review_text, rating)
Each review belongs to a parent and a babysitter

Requests
Represents friend requests between parents and babysitters (Main fields: family, babysitter, status, is_active)
Statuses: pending, approved, declined, cancelled
The is_active field is used to deactivate friend requests 


## API Endpoints

| Method | Endpoint | Description |
|---|---|---|

### Authentication and Users
| POST | /login/ | Logs in a user and returns access/refresh tokens |
| POST | /register/ | Registers a new parent or babysitter |
| POST | /user-delete/ | Deactivates the currently logged-in user |
| POST | /admin-user-delete/ | Allows admin to deactivate a selected parent or babysitter account |

### Profiles- For parents/babysitters, these endpoints return the profile connected to the logged-in user. For superusers, the endpoint can use query parameters such as babysitter_id or parent_id to access a specific profile.
| GET/PATCH	| /babysitter-profile/me/ |	Get or update babysitter profile |
| GET/PATCH	| /parents-profile/me/ | Get or update parent profile |

### Lists- Only active parents/babysitters are returned by the list view.
| GET | /babysitters-list/ | List active babysitters |
| GET | /parents-list/ | List active parents |

### Kids- The kids model is connected to the parent profile, and parents can add children to their own family profile.
| GET | /kids-list/?parent_id=<id> | Get kids for a parent |
| POST | /kids-add/ | Add kid/kids to logged-in parent |
| PATCH | /kids-update/<id>/ | Update a kid |

### Availability- Parents can only view a babysitter’s availability if the parent has an approved active request with that babysitter.
| GET | /availability-list/?babysitter_id=<id> | Parent views the approved babysitter availability |
| GET | /babysitter/availability/ | Babysitter views their own availability |
| POST | /babysitter/availability/ | Babysitter adds availability |
| PATCH | /babysitter/availability/<id>/ | Babysitter updates availability |
| DELETE | /babysitter/availability/<id>/ | Babysitter deletes availability |

### Friend Requests- Parents can send a request to a babysitter. If an active request already exists between the same parent and babysitter, the backend returns a conflict response. Babysitters can approve or decline requests. Declined requests are automatically deactivated. Parents can also cancel their own pending friend requests.
| POST | /request-add/ | Parent sends friend request to babysitter |
| GET | /requests-list/ | View requests for logged-in user |
| PATCH | /request-update/<id>/ | Babysitter approves/declines request |
| PATCH | /request-delete/<id>/ | Parent cancels/deactivates their request | 

### AI Messages- The project includes a real AI message helper using the Gemini API.  If a parent cannot find a suitable availability slot, they can enter a preferred date and time. The AI generates a polite message asking the babysitter if they can help at that time. The AI request is saved as a meeting request. After opening the Messages page, the babysitter can approve or decline the request. Parents can also see the babysitter’s response in the Messages page. If the babysitter approves the request, it becomes an approved babysitting meeting.
| POST | /ai-time-request/ | Generates an AI message for an alternative babysitting date and time |
| GET | /messages-count/ | Returns the number of unread AI messages for the logged-in user |
| POST | /messages-read/ | Marks AI messages as read after opening the Messages page |

### Meetings- Parents can create babysitting requests by selecting an existing babysitter availability slot, Babysitters can approve or decline pending meeting requests.
| POST | /meetings-add/ | Creates a custom babysitting request manually. This is also used for AI alternative time requests, where the parent sends a custom date, time, and AI-generated message |
| GET | /meetings-list/ | Shows all meetings connected to the logged-in user: parents and babysitters see their own meetings, admin sees all meetings |
| PATCH | /meeting-update/<id>/ | Babysitter approves or declines a pending babysitting request |
| POST | /babysit-request-add/ | Parent sends a babysitting request based on one of the babysitter’s available time slots |
| PATCH | /meeting-actions/?meeting_id=<id> | Parent or babysitter updates an existing meeting status |

### Reviews- Parents can only create a review for a babysitter if they have an approved relationship with that babysitter.
| GET |	/reviews-list/?babysitter_id=<id> | View reviews for a babysitter |
| POST | /reviews/ | Parent creates review |
| GET/PATCH/DELETE | /reviews/<id>/ | Review CRUD through router


## Admin Support

The backend registers the main models in Django Admin: Parents, Babysitter, Kids, Requests, AvailableTime, Meetings, Reviews 
This allows a superuser to manage the database records through the Django admin panel.


## Serializers

Serializers are used to validate incoming data and return model data as JSON.
Main serializers:
- RegistrationSerializer
- BabysitterSerializer
- ParentsSerializer
- KidsSerializer
- RequestsSerializer
- AvailableTimeSerializer
- MeetingsSerializer
- ReviewsSerializer


## Media Files

The backend supports uploaded profile pictures for both parents and babysitters.
Media settings:
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


## CORS

This allows the React frontend to communicate with the Django backend during development:
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


## Environment Variables

The backend uses environment variables for sensitive settings.
Create a .env file in the same folder as manage.py:
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
GEMINI_API_KEY=your-gemini-api-key
The AI API key is used by the AI message helper.  
The key must stay in the backend and should not be placed in the React frontend.


## Installation and Setup:

### 1. Clone the project
        git clone <repository-url>
        cd <backend-folder>
### 2. Create a virtual environment
        python -m venv myenv
### 3. Activate the virtual environment
        source myenv/bin/activate (Mac) 
        OR
        myenv\Scripts\activate (Windows)
### 4. Install dependencies
        pip install -r requirements.txt
### 5. Run migrations
        python manage.py makemigrations
        python manage.py migrate
### 6. Create superuser
        python manage.py createsuperuser
### 7. Run the server
        python manage.py runserver 
        (The backend will run by default at: http://127.0.0.1:8000/)

## Project Links
Frontend github repository: https://github.com/adiburshan/BabysitterApp--FrontEnd.git
Backend github repository: https://github.com/adiburshan/BabysitterApp-BackEnd.git
		

## Docker
This project can be run using Docker and Docker Compose.

### Dockerfile
The backend includes a Dockerfile that builds and runs the Django REST API.

### Run with Docker Compose
To run the backend with Docker Compose from the main project folder:
docker compose up --build

To stop the container:
docker compose down

		
		
		
