from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# FastAPI app setup
app = FastAPI()

# Add session middleware (REQUIRED for OAuth session handling)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key"))

# Optional: CORS Middleware
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000",  # Frontend dev server
    "https://yourfrontenddomain.com",  # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Template folder setup
templates = Jinja2Templates(directory="templates")

# MongoDB setup
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client["loginapp"]
users = db["users"]

# Google OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Home page route
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Google login route
@app.get("/auth/google")
async def login(request: Request):
    redirect_uri = "http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

# Google callback route
@app.get("/auth/google/callback")
async def auth_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        print("TOKEN:", token)

        if "id_token" not in token:
            return {"error": "id_token not found in token"}

        user_info = await oauth.google.parse_id_token(request, token)
        print("USER INFO:", user_info)

        existing_user = await users.find_one({"email": user_info["email"]})
        if not existing_user:
            await users.insert_one(user_info)

        return {"message": "Login successful", "user": user_info}

    except Exception as e:
        return {"error": str(e)}
