from fastapi import FastAPI, Query, UploadFile, File, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import mysql.connector
import jwt
from datetime import datetime, timedelta
import os
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter
from database import dbUrl


user_login = APIRouter()

# Define a function to get a new cursor
def get_cursor():
    return dbUrl.cursor()


# Define a Pydantic model for user registration
class UserRegistration(BaseModel):
    username: str
    first_name: str
    last_name: str
    password: str
    profile_picture: str = None  # Optional field
    gender_id: int
    email: str
    
    
def create_user(user: UserRegistration):
    cursor = get_cursor()
    cursor.execute("INSERT INTO users (username, first_name, last_name, password, profile_picture, gender_id, email) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                   (user.username, user.first_name, user.last_name, user.password, user.profile_picture, user.gender_id, user.email))
    dbUrl.commit()
    cursor.close()

# Database operations
def get_user_by_email(email: str):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    return user

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


@user_login.post("/api/register")
def register_user(user: UserRegistration):
    if get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    create_user(user)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"message": "User registered successfully", "access_token": access_token}



    

# Define the GET endpoint to get a list of genders
@user_login.get("/api/genders")
def list_genders():
    cursor = get_cursor()
    cursor.execute("SELECT id, name FROM genders")
    genders = cursor.fetchall()
    cursor.close()
    return [{"id": gender[0], "name": gender[1]} for gender in genders]


