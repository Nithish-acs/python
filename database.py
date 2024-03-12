# Connect to MySQL database
import mysql

dbUrl =  mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="",
    database="social_media"  # Specify the database name here
)

