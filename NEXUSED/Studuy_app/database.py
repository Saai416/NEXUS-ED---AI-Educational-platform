import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

# Get Database URL from env, or default to local SQLite for testing if not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# Handle Postgres URL requirement for SQLAlchemy (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String)
    role = Column(String) # 'student' or 'teacher'
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PendingVerification(Base):
    __tablename__ = "pending_verifications"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True) # Email or Phone
    otp = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CommunityPost(Base):
    __tablename__ = "community_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    title = Column(String)
    content = Column(String)
    user_id = Column(Integer) # ForeignKey to User.id
    username = Column(String) # Denormalized for display speed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CommunityComment(Base):
    __tablename__ = "community_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True) # ForeignKey to CommunityPost.id
    content = Column(String)
    user_id = Column(Integer)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    # Could add JSON column for detailed topic progress if needed
    # SQLite doesn't strictly enforce types, but for now simple XP is enough
    
class StudyGroup(Base):
    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    name = Column(String) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class GroupMembership(Base):
    __tablename__ = "group_memberships"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, index=True)
    user_id = Column(Integer)
    username = Column(String)

class GroupArtifact(Base):
    __tablename__ = "group_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, index=True)
    content = Column(String, default="")
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

class OrganizationPlan(Base):
    __tablename__ = "organization_plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String) # Text content or file path
    summary = Column(String)
    created_by = Column(Integer) # User ID (Teacher)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    """Creates tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("Tables created successfully!")
