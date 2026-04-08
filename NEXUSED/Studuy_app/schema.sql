-- Enable UUID extension if we want to use UUIDs (optional, using Serial/Integer for now to match code)

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('student', 'teacher')),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create Pending Verifications Table
CREATE TABLE IF NOT EXISTS pending_verifications (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL, -- Email or Phone
    otp VARCHAR(10) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_pending_verifications_identifier ON pending_verifications(identifier);

-- Optional: Add a test user directly (Password: student123)
-- Hash generated via bcrypt for 'student123'
-- INSERT INTO users (username, email, password_hash, role, is_verified) 
-- VALUES ('student', 'student@test.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWrn96pzvPnEye.R6xO1F.qGP.euG.', 'student', TRUE);
