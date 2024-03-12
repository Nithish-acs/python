from fastapi import FastAPI, Query, UploadFile, File, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import mysql.connector
import jwt
from datetime import datetime, timedelta
import os
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.api import user_register
from app.users import user_login
from database import dbUrl

app = FastAPI()

# Configure CORS settings
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_register,
                   prefix="", tags=["social_media"])

app.include_router(user_login,
                   prefix="", tags=["social_media"])

# Connect to MySQL database
# dbUrl = mysql.connector.connect(
#     host=" 127.0.0.1",
#     user="root",
#     password="",
#     database="social_media"  # Specify the database name here
# )



# Define a function to get a new cursor
def get_cursor():
    return dbUrl.cursor()


class UserUpdate(BaseModel):
    first_name: str = None
    last_name: str = None
    password: str = None
    gender_id: int = None
    email: str = None

class UpdateProfilePic(BaseModel):
    profile_pic: UploadFile = None
    
class UserLogin(BaseModel):
    email: str
    password: str

class ForgotPassword(BaseModel):
    email: str


# Token expiration time
ACCESS_TOKEN_EXPIRE_MINUTES = 15
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"



# Define functions to work with JWT tokens
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Database operations
def get_user_by_email(email: str):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    return user


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return False
    if user[4] != password:  # Compare plaintext passwords
        return False
    return user

# Directory for storing profile pictures
PROFILE_PICS_DIR = "users"

# Function to generate a unique filename for profile pictures
def generate_unique_filename(file_name):
    _, ext = os.path.splitext(file_name)
    return f"{uuid.uuid4().hex}{ext}"

@app.put("/api/upload-profile-pic/{user_id}")
async def upload_profile_pic(user_id: int, profile_pic: UploadFile = File(...)):
    try:
        print("user_id", user_id)
        print("profile_pic", profile_pic)

        if not PROFILE_PICS_DIR or not isinstance(PROFILE_PICS_DIR, str):
            return {"message": "Invalid profile picture directory configuration"}

        if not os.path.exists(PROFILE_PICS_DIR):
            os.makedirs(PROFILE_PICS_DIR)

        file_name = generate_unique_filename(profile_pic.filename)
        file_path = os.path.join(PROFILE_PICS_DIR, file_name)

        print("file_path:", file_path)

        with open(file_path, "wb") as f:
            f.write(await profile_pic.read())

        cursor = get_cursor()
        cursor.execute("UPDATE users SET profile_picture = %s WHERE id = %s", (file_name, user_id))
        dbUrl.commit()

        return {"message": "Profile picture uploaded successfully", "file_name": file_name}
    except Exception as e:
        print("Error:", e)
        return {"message": "Failed to upload profile picture"}



@app.post("/api/login")
def login_user(user: UserLogin):
    print(user.email)
    auth_user = authenticate_user(user.email, user.password)
    if not auth_user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": auth_user[0]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    # Get the profile picture URL
    profile_picture = None
    if auth_user[5]:
        profile_picture = f"/api/profile-picture/{auth_user[5]}"

    return {
        "access_token": access_token,
        "message": "Login successful",
        "user_details": {
            "user_id": auth_user[0],
            "user_name": auth_user[1],
            "first_name": auth_user[2],
            "last_name": auth_user[3],
            "profile_picture": profile_picture,  # Include profile picture URL
            "gender_id": auth_user[6],
            "email": auth_user[7],
        }
    }

@app.get("/api/profile-picture/{file_name}")
async def get_profile_picture(file_name: str):
    file_path = os.path.join(PROFILE_PICS_DIR, file_name)
    return FileResponse(file_path, media_type="image/png") 


def reset_password(email: str):
    new_password = str(uuid.uuid4())[:8]  # Generate a random 8-character password
    cursor = get_cursor()
    cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, email))
    dbUrl.commit()
    cursor.close()
    return new_password

# Function to send email with new password
@app.post("/api/forgot-password")
def forgot_password(request: ForgotPassword):
    user_email = request.email
    user = get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_password = reset_password(user_email)
    
    # Update the response to include the new password
    return {"message": "Password reset successfully", "new_password": new_password}

# Database operations
def get_user_by_id(user_id: int):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()

def update_user(user_id: int, user_update: UserUpdate):
    print(user_update)
    columns = []
    values = []
    for key, value in user_update.dict().items():
        if value is not None:
            columns.append(key)
            values.append(value)
    
    if not columns:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"UPDATE users SET {', '.join([f'{col} = %s' for col in columns])} WHERE id = %s"
    values.append(user_id)
    cursor = get_cursor()
    cursor.execute(query, tuple(values))
    dbUrl.commit()

# API endpoint for updating user information
@app.put("/api/upload-profile-pic")
async def upload_profile_pic(user_id: int = Query(...), profile_pic: UploadFile = File(...)):
    try:
       
        if not PROFILE_PICS_DIR or not isinstance(PROFILE_PICS_DIR, str):
            return {"message": "Invalid profile picture directory configuration"}

        if not os.path.exists(PROFILE_PICS_DIR):
            os.makedirs(PROFILE_PICS_DIR)

        file_name = generate_unique_filename(profile_pic.filename)
        file_path = os.path.join(PROFILE_PICS_DIR, file_name)

        with open(file_path, "wb") as f:
            f.write(await profile_pic.read())

        # Update profile picture file name in the database
        cursor = get_cursor()
        print('user_id',user_id)
        cursor.execute("UPDATE users SET profile_picture = %s WHERE id = %s", (file_name, user_id))
        dbUrl.commit()

        return {"message": "Profile picture uploaded successfully", "file_name": file_name}
    except Exception as e:
        print("Error:", e)
        return {"message": "Failed to upload profile picture"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
