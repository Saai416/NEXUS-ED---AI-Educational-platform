from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import secrets
from database import get_db, User, PendingVerification, CommunityPost, CommunityComment, UserProgress, StudyGroup, GroupMembership, GroupArtifact, OrganizationPlan
import backend_logic
from ml_engine.predictor import predict_student_risk
import os
import shutil
import nltk
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# --- Security & Config ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
TEACHER_ACCESS_CODE = os.getenv("TEACHER_ACCESS_CODE", "TEACHER_SECRET")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def generate_mock_otp():
    return str(secrets.randbelow(999999)).zfill(6)

# --- Models ---
class LoginData(BaseModel):
    username: str
    password: str

class SignupData(BaseModel):
    username: str
    email: str
    phone: Optional[str] = None
    password: str
    role: str
    teacher_code: Optional[str] = None

class VerifyData(BaseModel):
    identifier: str # Email or Phone
    otp: str

class ChatRequest(BaseModel):
    question: str
    namespace: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    answer = await backend_logic.process_student_question(request.question, request.namespace)
    return {"answer": answer}



class UploadRequest(BaseModel):
    content_name: str
    text: Optional[str] = None
    url: Optional[str] = None

class PostCreate(BaseModel):
    topic: str
    title: str
    content: str

class CommentCreate(BaseModel):
    post_id: int
    content: str

class XPUpdate(BaseModel):
    xp_amount: int

class GroupJoin(BaseModel):
    topic: str

class GroupArtifactUpdate(BaseModel):
    group_id: int
    content: str
    append: bool = False

# --- Dependencies ---
# Simple cookie-based auth simulation
def get_current_user(request: Request):
    user = request.cookies.get("user")
    role = request.cookies.get("role")
    if not user or not role:
        return None
    return {"username": user, "role": role}

def require_student(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/"}, detail="Not authenticated")
    if user["role"] != "student":
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return user

def require_teacher(user = Depends(get_current_user)):
    if not user:
         raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/"}, detail="Not authenticated")
    if user["role"] != "teacher":
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return user

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/signup")
async def signup(data: SignupData, db: Session = Depends(get_db)):
    # 1. Check if user already exists
    existing_user = db.query(User).filter((User.username == data.username) | (User.email == data.email)).first()
    if existing_user:
        return JSONResponse(content={"error": "Username or Email already registered"}, status_code=400)

    # 2. Teacher Verification
    if data.role == "teacher":
        if data.teacher_code != TEACHER_ACCESS_CODE:
            return JSONResponse(content={"error": "Invalid Teacher Access Code"}, status_code=403)

    # 3. Generate Mock OTP
    otp = generate_mock_otp()
    
    # 4. Store OTP in PendingVerification
    # Remove old OTPs for this identifier
    db.query(PendingVerification).filter(PendingVerification.identifier == data.email).delete()
    
    verification = PendingVerification(
        identifier=data.email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db.add(verification)
    db.commit()

    # 5. Log OTP to console (Mock Service)
    print(f"\n[MOCK SMS/EMAIL] OTP for {data.email}: {otp}\n")

    return {"message": "OTP sent! Check console.", "require_verification": True, "identifier": data.email}

@app.post("/api/verify")
async def verify_otp(data: VerifyData, signup_data: SignupData, db: Session = Depends(get_db)):
    # This endpoint implies we send signup data AGAIN with the OTP, or we store temp user state.
    # A cleaner way is: Signup -> Returns "Ok" -> Frontend shows OTP Input -> Submit OTP + Original Data.
    # To keep payload simple for this step, let's assume Frontend sends everything needed to create user ONLY after OTP is valid.
    # BUT, to be secure, /api/verify normally just toggles a flag.
    # Let's adjust: /api/signup actually creates the user but sets is_verified=False? 
    # Or strict flow: /signup (saves temp) -> /verify (creates real user).
    # Let's go with the user creation flow HERE in verify for atomicity.
    
    # Check OTP
    # Note: validation against time should handle timezone awareness
    pass

# Redefining /api/signup to CREATE user immediately but unverified
@app.post("/api/register")
async def register_initial(data: SignupData, db: Session = Depends(get_db)):
    # Check exists
    if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
         return JSONResponse(content={"error": "User already exists"}, status_code=400)

    # Role Check
    if data.role == "teacher" and data.teacher_code != TEACHER_ACCESS_CODE:
        return JSONResponse(content={"error": "Invalid Teacher Access Code"}, status_code=403)

    # Create User (Unverified)
    new_user = User(
        username=data.username,
        email=data.email,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_verified=False
    )
    db.add(new_user)
    
    # Generate OTP
    otp = generate_mock_otp()
    verification = PendingVerification(
        identifier=data.email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db.add(verification)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(content={"error": str(e)}, status_code=500)

    print(f"\n[MOCK OTP] Code for {data.email}: {otp}\n")
    return {"message": "User registered. Please verify OTP.", "identifier": data.email}

@app.post("/api/confirm_verification")
async def confirm_verification(data: VerifyData, db: Session = Depends(get_db)):
    # Check OTP
    record = db.query(PendingVerification).filter(
        PendingVerification.identifier == data.identifier,
        PendingVerification.otp == data.otp
    ).first()

    if not record:
        return JSONResponse(content={"error": "Invalid OTP"}, status_code=400)
    
    # Time comparison with timezone awareness
    if record.expires_at < datetime.now(timezone.utc):
        return JSONResponse(content={"error": "OTP Expired"}, status_code=400)
    
    # Mark User Verified
    user = db.query(User).filter(User.email == data.identifier).first()
    if user:
        user.is_verified = True
        db.delete(record) # Consume OTP
        db.commit()
        return {"message": "Verification Successful! You can now login."}
    return JSONResponse(content={"error": "User not found"}, status_code=404)

@app.post("/login")
async def login(data: LoginData, db: Session = Depends(get_db)):
    # DB Lookup
    user = db.query(User).filter(User.username == data.username).first()
    
    if not user or not verify_password(data.password, user.password_hash):
        return JSONResponse(content={"error": "Invalid credentials"}, status_code=400)
    
    if not user.is_verified:
        return JSONResponse(content={"error": "Account not verified. Please complete verification."}, status_code=403)

    # Success
    redirect_url = f"/{user.role}"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user", value=user.username)
    response.set_cookie(key="role", value=user.role)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user")
    response.delete_cookie("role")
    return response

# --- Student Routes ---

@app.get("/student", response_class=HTMLResponse)
async def student_dashboard(request: Request, user = Depends(require_student)):
    topics = backend_logic.load_topics()
    return templates.TemplateResponse("student.html", {"request": request, "user": user, "topics": topics})

@app.get("/student/chat", response_class=HTMLResponse)
async def student_chat_page(request: Request, user = Depends(require_student)):
    course = request.query_params.get("course")
    return templates.TemplateResponse("chat_dashboard.html", {"request": request, "user": user, "course": course})

@app.get("/student/plans_page", response_class=HTMLResponse)
async def student_plans_page(request: Request, user = Depends(require_student)):
    return templates.TemplateResponse("student_plans.html", {"request": request, "user": user})

# --- Teacher Routes ---

@app.get("/teacher", response_class=HTMLResponse)
async def teacher_dashboard(request: Request, user = Depends(require_teacher)):
    # Load plans for the dashboard
    # This might be fetched via API, but let's pass it if easy, or use JS to fetch.
    # We will use JS in the template to fetch analytics and plans.
    return templates.TemplateResponse("teacher.html", {"request": request, "user": user})

@app.get("/api/teacher/analytics")
async def get_teacher_analytics(user = Depends(require_teacher), db: Session = Depends(get_db)):
    students = db.query(User).filter(User.role == "student").all()
    
    analytics_data = []
    
    for student in students:
        # 1. Calculate Metrics (Mocking some for now as we don't have full tracking)
        # Avg Quiz Score: Need a table for Quiz Results? 
        # For now, let's derive 'avg_score' from UserProgress.total_xp (very rough proxy) or just random for demo if not strictly tracked yet?
        # A better proxy: UserProgress.level * 10? No.
        # Let's check if we have quiz scores. We don't in `schema.sql`.
        # So we will use specific heuristics or mock the INPUTS to the ML model based on available data + some randomness/heuristics for the demo
        # to show the ML Working.
        
        progress = db.query(UserProgress).filter(UserProgress.user_id == student.id).first()
        posts_count = db.query(CommunityPost).filter(CommunityPost.user_id == student.id).count()
        
        active_days = 0 
        if progress:
             # Heuristic: Level * 2
             active_days = progress.level * 2
        
        avg_score = 0
        if progress:
             # Heuristic based on XP
             avg_score = min(100, (progress.total_xp / 10) + 50) 
        
        features = {
            'avg_quiz_score': avg_score,
            'active_days': active_days,
            'posts_count': posts_count,
            'lessons_completed': progress.level if progress else 0
        }
        
        # 2. ML Prediction
        prediction = predict_student_risk(features)
        
        analytics_data.append({
            "username": student.username,
            "email": student.email,
            "metrics": features,
            "prediction": prediction
        })
        
    return analytics_data

@app.get("/api/teacher/plans")
async def get_teacher_plans(user = Depends(require_teacher), db: Session = Depends(get_db)):
    # Teacher sees plans they uploaded? Or all plans? Let's show all for Org.
    plans = db.query(OrganizationPlan).order_by(OrganizationPlan.created_at.desc()).all()
    return plans

@app.post("/api/teacher/upload_plan")
async def upload_teacher_plan(
    title: str = Form(...),
    file: UploadFile = File(...),
    user = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    try:
        filename = f"PLAN_{secrets.token_hex(4)}_{file.filename}"
        filepath = os.path.join("static/course_materials", filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Extract text for summary
        summary = "No summary available."
        # reuse extraction logic if possible
        summary = "No summary available."
        
        # Unified extraction
        text = backend_logic.extract_text_from_file(filepath)
        if text and not text.startswith("[ERROR") and not text.startswith("[WARNING"):
             summary = backend_logic.generate_summary(text)
        
        # Save to DB
        db_user = db.query(User).filter(User.username == user["username"]).first()
        new_plan = OrganizationPlan(
            title=title,
            content=f"/static/course_materials/{filename}",
            summary=summary,
            created_by=db_user.id
        )
        db.add(new_plan)
        db.commit()
        return {"message": "Plan uploaded successfully", "plan": {"title": title, "summary": summary}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/upload")
async def upload_content(
    content_name: str = Form(...),
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user = Depends(require_teacher)
):
    namespace = content_name
    sentences = []
    full_text = ""
    pdf_path = None
    
    print(f"Upload received: Name={content_name}, Text={bool(text)}, URL={bool(url)}, File={bool(file)}")

    # 1. Process Input
    if file:
        try:
            filename = f"{secrets.token_hex(4)}_{file.filename}"
            filepath = os.path.join("static/course_materials", filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            pdf_path = f"/static/course_materials/{filename}"
            print(f"File saved to {pdf_path}")
            
            pdf_path = f"/static/course_materials/{filename}"
            print(f"File saved to {pdf_path}")
            
            # Unified extraction for PDF, DOCX, TXT
            full_text = backend_logic.extract_text_from_file(filepath)
            
            if full_text and not full_text.startswith("[ERROR"):
                 sentences = nltk.sent_tokenize(full_text)
            else:
                 print(f"Extraction failed or incomplete: {full_text}")
                    
        except Exception as e:
            return JSONResponse(content={"error": f"File upload failed: {str(e)}"}, status_code=500)
            
    elif text:
        full_text = text
        sentences = nltk.sent_tokenize(text)
    elif url:
        sentences, full_text = backend_logic.get_content_from_url(url)
    else:
        return JSONResponse(content={"error": "No text, URL, or file provided"}, status_code=400)

    # 2. Pinecone Upsert
    if sentences:
        success, msg = backend_logic.upsert_to_pinecone(backend_logic.init_pinecone(), sentences, namespace)
        if not success:
            return JSONResponse(content={"error": msg}, status_code=500)
    else:
        print("Warning: No text extracted to upsert.")

    # 3. Neo4j extraction (if text exists)
    graph_data = {}
    if full_text:
        # KG2 now handles chunking, so we can pass the full text
        # (Though we might still want a safety limit of say 100k chars to avoid infinite processing)
        graph_text = full_text[:100000] 
        graph_data = backend_logic.extract_entities_and_relations(graph_text)
        if graph_data:
            backend_logic.load_graph_to_neo4j(graph_data)
    
    # 4. Generate Metadata (Summary)
    summary = ""
    if full_text:
        summary = backend_logic.generate_summary(full_text)
    
    # 5. Save Topic & Metadata
    backend_logic.save_topic(namespace)
    backend_logic.save_topic_metadata(namespace, {
        "summary": summary,
        "pdf_path": pdf_path,
        "created_at": str(datetime.now())
    })

    return {"message": "Content uploaded successfully", "graph_preview": graph_data, "summary": summary}

@app.get("/api/topics")
async def get_topics():
    return backend_logic.load_topics()

@app.get("/api/topic/{topic_name}")
async def get_topic_details(topic_name: str):
    metadata = backend_logic.get_topic_metadata(topic_name)
    return metadata

@app.get("/api/quiz/{topic_name}")
async def get_quiz(topic_name: str):
    # Retrieve text to generate quiz from? or generate generic?
    # Better to have stored the text or re-extract? re-extract is slow.
    # For now, let's try to generate from summary or just generic.
    # ideally we should have stored the 'full_text' in metadata or similar, but generic summary quiz is ok.
    metadata = backend_logic.get_topic_metadata(topic_name)
    summary = metadata.get("summary", "")
    
    # To get better questions, we might want to fetch from Pinecone or similar?
    # Simple approach: Generate based on Summary.
    if summary:
        questions = backend_logic.generate_quiz(summary)
        return questions
    return [{"question": "No content found for quiz.", "options": ["N/A"], "answer": "N/A"}]

# --- Community Routes ---

@app.get("/api/community/{topic}")
async def get_community_posts(topic: str, db: Session = Depends(get_db)):
    posts = db.query(CommunityPost).filter(CommunityPost.topic == topic).order_by(CommunityPost.created_at.desc()).all()
    # Eager load comments? Or fetch separate. Simple list for now.
    return posts

@app.get("/api/community/post/{post_id}")
async def get_post_details(post_id: int, db: Session = Depends(get_db)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    comments = db.query(CommunityComment).filter(CommunityComment.post_id == post_id).order_by(CommunityComment.created_at.asc()).all()
    return {"post": post, "comments": comments}

@app.post("/api/community/post")
async def create_post(data: PostCreate, user = Depends(require_student), db: Session = Depends(get_db)):
    try:
        # Get user id from username (simple way since we only have username in cookie)
        db_user = db.query(User).filter(User.username == user["username"]).first()
        
        new_post = CommunityPost(
            topic=data.topic,
            title=data.title,
            content=data.content,
            user_id=db_user.id,
            username=db_user.username
        )
        db.add(new_post)
        db.commit()
        
        # Award XP for posting?
        return {"message": "Post created", "post_id": new_post.id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Internal Error: {str(e)}"})

@app.post("/api/community/comment")
async def create_comment(data: CommentCreate, user = Depends(require_student), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user["username"]).first()
    
    new_comment = CommunityComment(
        post_id=data.post_id,
        content=data.content,
        user_id=db_user.id,
        username=db_user.username
    )
    db.add(new_comment)
    db.commit()
    return {"message": "Comment added"}

    db.add(new_comment)
    db.commit()
    return {"message": "Comment added"}

@app.get("/api/student/analytics")
async def get_student_analytics(user = Depends(require_student), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user["username"]).first()
    progress = db.query(UserProgress).filter(UserProgress.user_id == db_user.id).first()
    posts_count = db.query(CommunityPost).filter(CommunityPost.user_id == db_user.id).count()
    
    # Heuristics for Features
    active_days = progress.level * 2 if progress else 0
    avg_score = min(100, (progress.total_xp / 10) + 50) if progress else 50
    
    features = {
        'avg_quiz_score': avg_score,
        'active_days': active_days,
        'posts_count': posts_count,
        'lessons_completed': progress.level if progress else 0
    }
    
    prediction = predict_student_risk(features)
    
    return {
        "metrics": features,
        "prediction": prediction
    }

@app.get("/api/student/plans")
async def get_student_plans(user = Depends(require_student), db: Session = Depends(get_db)):
    plans = db.query(OrganizationPlan).order_by(OrganizationPlan.created_at.desc()).all()
    return plans

# --- Progress Routes ---

@app.get("/api/progress")
async def get_progress(user = Depends(require_student), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user["username"]).first()
    progress = db.query(UserProgress).filter(UserProgress.user_id == db_user.id).first()
    
    if not progress:
        # Initialize
        progress = UserProgress(user_id=db_user.id, total_xp=0, level=1)
        db.add(progress)
        db.commit()
        
    return progress

@app.post("/api/progress/update")
async def update_progress(data: XPUpdate, user = Depends(require_student), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user["username"]).first()
    progress = db.query(UserProgress).filter(UserProgress.user_id == db_user.id).first()
    
    if not progress:
        progress = UserProgress(user_id=db_user.id, total_xp=0, level=1)
        db.add(progress)
    
    progress.total_xp += data.xp_amount
    # Simple Level logic: Level = 1 + (XP // 100)
    progress.level = 1 + (progress.total_xp // 100)
    
    db.commit()
    return {"message": "XP updated", "total_xp": progress.total_xp, "level": progress.level}

# --- Jigsaw / Groups Routes ---

@app.post("/api/groups/join")
async def join_group(data: GroupJoin, user = Depends(require_student), db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.username == user["username"]).first()
        
        # 1. Check if already in a group for this topic
        existing_membership = db.query(GroupMembership).join(
            StudyGroup, 
            GroupMembership.group_id == StudyGroup.id
        ).filter(
            GroupMembership.user_id == db_user.id,
            StudyGroup.topic == data.topic
        ).first()
        
        if existing_membership:
            return {"message": "Already in a group", "group_id": existing_membership.group_id}

        # 2. Logic to assign group: Find a group with < 4 members, else create new
        # Simplification: Just create a "Group 1", "Group 2" etc sequentially
        
        groups = db.query(StudyGroup).filter(StudyGroup.topic == data.topic).all()
        target_group = None
        
        for group in groups:
            count = db.query(GroupMembership).filter(GroupMembership.group_id == group.id).count()
            if count < 4:
                target_group = group
                break
                
        if not target_group:
            new_name = f"Group {len(groups) + 1}"
            target_group = StudyGroup(topic=data.topic, name=new_name)
            db.add(target_group)
            db.commit() # Commit to get ID
            
        # 3. Add Member
        membership = GroupMembership(
            group_id=target_group.id,
            user_id=db_user.id,
            username=db_user.username
        )
        db.add(membership)
        db.commit()
        
        # Ensure Artifact exists
        artifact = db.query(GroupArtifact).filter(GroupArtifact.group_id == target_group.id).first()
        if not artifact:
            db.add(GroupArtifact(group_id=target_group.id))
            db.commit()

        return {"message": f"Joined {target_group.name}", "group_id": target_group.id, "group_name": target_group.name}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Internal Error: {str(e)}"})

@app.get("/api/groups/current")
async def get_my_group_details(topic: str, user = Depends(require_student), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user["username"]).first()
    
    membership = db.query(GroupMembership).join(
        StudyGroup,
        GroupMembership.group_id == StudyGroup.id
    ).filter(
        GroupMembership.user_id == db_user.id,
        StudyGroup.topic == topic
    ).first()
    
    if not membership:
        return JSONResponse(content={"error": "Not in any group"}, status_code=404)
        
    group = db.query(StudyGroup).filter(StudyGroup.id == membership.group_id).first()
    members = db.query(GroupMembership).filter(GroupMembership.group_id == group.id).all()
    artifact = db.query(GroupArtifact).filter(GroupArtifact.group_id == group.id).first()
    
    return {
        "group_id": group.id,
        "name": group.name,
        "members": [m.username for m in members],
        "artifact_content": artifact.content if artifact else ""
    }

@app.post("/api/groups/artifact")
async def save_artifact(data: GroupArtifactUpdate, user = Depends(require_student), db: Session = Depends(get_db)):
    # Verify membership
    db_user = db.query(User).filter(User.username == user["username"]).first()
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == data.group_id,
        GroupMembership.user_id == db_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this group")
        
    artifact = db.query(GroupArtifact).filter(GroupArtifact.group_id == data.group_id).first()
    if not artifact:
        artifact = GroupArtifact(group_id=data.group_id)
        db.add(artifact)
        
    if data.append:
        # Append mode for Chat
        import json
        entry = json.dumps({"user": user["username"], "text": data.content})
        if artifact.content:
            artifact.content += "\n" + entry
        else:
            artifact.content = entry
    else:
        # Overwrite mode (legacy or reset)
        artifact.content = data.content
        
    artifact.last_updated = datetime.utcnow()
    db.commit()
    
    return {"message": "Artifact saved"}
