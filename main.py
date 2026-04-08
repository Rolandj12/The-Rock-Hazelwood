from fastapi import FastAPI, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import shutil
import os

from database import Base, engine, SessionLocal
from models import User
from auth import hash_password, verify_password, create_token
from github import handle_github_webhook
from utils import process_csv

app = FastAPI()
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password):
        return {"error": "Invalid credentials"}

    token = create_token({"sub": user.username})
    return {"token": token}

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    user = User(
        username=username,
        password=hash_password(password),
        role="admin"
    )
    db.add(user)
    db.commit()
    return {"message": "User created"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_path = f"{UPLOAD_DIR}/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if file.filename.endswith(".csv"):
        data = process_csv(file_path)
        return {"preview": data}

    return {"message": "File uploaded"}

@app.post("/webhook/github")
async def github_webhook(request: Request):
    await handle_github_webhook(request)
    return {"status": "ok"}