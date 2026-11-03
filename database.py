
import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "")
}

DB_NAME = os.getenv("DB_NAME", "edusphere_db")


def get_db_connection():
    return mysql.connector.connect(
        **DB_CONFIG,
        database=DB_NAME
    )


def initialize_database():
    # Create database if it does not exist
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    connection.close()

    db = get_db_connection()
    cursor = db.cursor()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            email VARCHAR(150) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS departments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            department_name VARCHAR(150) NOT NULL UNIQUE,
            department_code VARCHAR(30) UNIQUE,
            description TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_name VARCHAR(150) NOT NULL,
            course_code VARCHAR(30) NOT NULL UNIQUE,
            department_id INT,
            duration VARCHAR(50),
            course_fee DECIMAL(10,2) DEFAULT 0,
            FOREIGN KEY (department_id)
                REFERENCES departments(id) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admission_no VARCHAR(50) NOT NULL UNIQUE,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100),
            email VARCHAR(150) NOT NULL UNIQUE,
            phone VARCHAR(20),
            gender VARCHAR(20),
            date_of_birth DATE,
            address TEXT,
            course_id INT,
            admission_date DATE,
            status ENUM('Active','Inactive','Graduated') DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id)
                REFERENCES courses(id) ON DELETE SET NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL UNIQUE,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            FOREIGN KEY (student_id)
                REFERENCES students(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            attendance_date DATE NOT NULL,
            attendance_status ENUM('Present','Absent','Late') DEFAULT 'Present',
            remarks VARCHAR(255),
            UNIQUE KEY unique_attendance (student_id, attendance_date),
            FOREIGN KEY (student_id)
                REFERENCES students(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS fees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            total_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
            paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            payment_date DATE,
            payment_method VARCHAR(50),
            transaction_id VARCHAR(100),
            payment_status ENUM('Pending','Partial','Paid') DEFAULT 'Pending',
            FOREIGN KEY (student_id)
                REFERENCES students(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            exam_name VARCHAR(150) NOT NULL,
            subject VARCHAR(150) NOT NULL,
            total_marks DECIMAL(6,2) NOT NULL,
            obtained_marks DECIMAL(6,2) NOT NULL,
            exam_date DATE,
            FOREIGN KEY (student_id)
                REFERENCES students(id) ON DELETE CASCADE
        )
        """
    ]

    try:
        for sql in tables:
            cursor.execute(sql)

        # Default admin account
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "Edu@Admin123")

        cursor.execute(
            "SELECT id FROM admins WHERE username=%s",
            (username,)
        )

        if cursor.fetchone() is None:
            cursor.execute(
                """
                INSERT INTO admins
                (username, password_hash, full_name, email)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    username,
                    generate_password_hash(password),
                    "System Administrator",
                    "admin@edusphere.com"
                )
            )

        # Sample departments
        cursor.execute("""
            INSERT IGNORE INTO departments
            (department_name, department_code)
            VALUES
            ('Computer Science', 'CS'),
            ('Information Technology', 'IT'),
            ('Commerce', 'COM'),
            ('Science', 'SCI')
        """)

        db.commit()
        print("EduSphere database initialized successfully!")

    finally:
        cursor.close()
        db.close()


if __name__ == "__main__":
    initialize_database()
