import uuid, shutil
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import PROJECTS_DIR, MAX_UPLOAD_MB, MAX_PROJECTS_PER_USER, MAX_FILES_PER_PROJECT, MAX_FILE_BYTES
from .db import init_db, connection
from .auth import hash_password, verify_password, make_token, current_user
from .safe_runner import run_python_demo

app = FastAPI(title="PyHost Demo", version="2.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def home():
    return FileResponse("app/static/index.html")

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=72)

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=48)

class FileData(BaseModel):
    path: str
    content: str = ""

def project_row(pid, user):
    with connection() as db:
        row = db.execute("SELECT * FROM projects WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    if not row: raise HTTPException(404, "Không tìm thấy project")
    return dict(row)

def root_dir(pid):
    return (PROJECTS_DIR / pid).resolve()

def safe_path(root: Path, rel: str):
    rel = rel.replace("\\", "/").lstrip("/")
    if not rel or any(x in ("", ".", "..") for x in rel.split("/")):
        raise HTTPException(400, "Đường dẫn không hợp lệ")
    target = (root / rel).resolve()
    if root.resolve() not in target.parents: raise HTTPException(400, "Đường dẫn không hợp lệ")
    return target

@app.post("/api/register")
def register(data: Credentials):
    with connection() as db:
        try:
            cur = db.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                             (data.username, hash_password(data.password)))
        except Exception:
            raise HTTPException(409, "Tên tài khoản đã tồn tại")
        uid = cur.lastrowid
    return {"access_token": make_token(uid), "token_type": "bearer"}

@app.post("/api/login")
def login(data: Credentials):
    with connection() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (data.username,)).fetchone()
    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    return {"access_token": make_token(row["id"]), "token_type": "bearer"}

@app.get("/api/me")
def me(user=Depends(current_user)): return user

@app.get("/api/projects")
def projects(user=Depends(current_user)):
    with connection() as db:
        rows = db.execute("SELECT * FROM projects WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return [{"id":r["id"],"name":r["name"]} for r in rows]

@app.post("/api/projects")
def create_project(data: ProjectCreate, user=Depends(current_user)):
    with connection() as db:
        n = db.execute("SELECT COUNT(*) FROM projects WHERE user_id=?", (user["id"],)).fetchone()[0]
    if n >= MAX_PROJECTS_PER_USER: raise HTTPException(403, f"Demo giới hạn {MAX_PROJECTS_PER_USER} project/tài khoản")
    pid = str(uuid.uuid4())
    folder = root_dir(pid); folder.mkdir(parents=True)
    (folder/"requirements.txt").write_text("# Add packages here, one per line\n", encoding="utf-8")
    (folder/"bot.py").write_text('print("Hello from PyHost demo!")\nfor i in range(3):\n    print("Bot tick", i)\n', encoding="utf-8")
    with connection() as db:
        db.execute("INSERT INTO projects(id,user_id,name) VALUES(?,?,?)", (pid,user["id"],data.name))
    return {"id":pid,"name":data.name}

@app.delete("/api/projects/{pid}")
def delete_project(pid: str, user=Depends(current_user)):
    project_row(pid,user)
    shutil.rmtree(root_dir(pid), ignore_errors=True)
    with connection() as db: db.execute("DELETE FROM projects WHERE id=? AND user_id=?", (pid,user["id"]))
    return {"ok":True}

@app.get("/api/projects/{pid}/files")
def list_files(pid: str, user=Depends(current_user)):
    project_row(pid,user); root=root_dir(pid); result=[]
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink():
            result.append({"path":p.relative_to(root).as_posix(),"size":p.stat().st_size})
    return sorted(result,key=lambda x:x["path"])

@app.post("/api/projects/{pid}/files")
def create_file(pid: str, data: FileData, user=Depends(current_user)):
    project_row(pid,user); target=safe_path(root_dir(pid),data.path)
    if target.exists(): raise HTTPException(409,"File đã tồn tại")
    if len(data.content.encode()) > MAX_FILE_BYTES: raise HTTPException(413,"File quá lớn")
    target.parent.mkdir(parents=True,exist_ok=True); target.write_text(data.content,encoding="utf-8")
    return {"ok":True}

@app.get("/api/projects/{pid}/files/content")
def read_file(pid: str, path: str, user=Depends(current_user)):
    project_row(pid,user); target=safe_path(root_dir(pid),path)
    if not target.is_file() or target.is_symlink(): raise HTTPException(404,"Không tìm thấy file")
    if target.stat().st_size > MAX_FILE_BYTES: raise HTTPException(413,"File quá lớn")
    return {"path":path,"content":target.read_text(encoding="utf-8",errors="replace")}

@app.put("/api/projects/{pid}/files/content")
def edit_file(pid: str, data: FileData, user=Depends(current_user)):
    project_row(pid,user); target=safe_path(root_dir(pid),data.path)
    if not target.is_file() or target.is_symlink(): raise HTTPException(404,"Không tìm thấy file")
    if len(data.content.encode()) > MAX_FILE_BYTES: raise HTTPException(413,"File quá lớn")
    target.write_text(data.content,encoding="utf-8")
    return {"ok":True}

@app.delete("/api/projects/{pid}/files")
def delete_file(pid: str, path: str, user=Depends(current_user)):
    project_row(pid,user); target=safe_path(root_dir(pid),path)
    if not target.is_file() or target.is_symlink(): raise HTTPException(404,"Không tìm thấy file")
    target.unlink(); return {"ok":True}

@app.post("/api/projects/{pid}/upload")
async def upload(pid: str, file: UploadFile=File(...), user=Depends(current_user)):
    project_row(pid,user)
    name=Path(file.filename or "").name
    if not name or name in (".","..") or len(name)>120: raise HTTPException(400,"Tên file không hợp lệ")
    target=safe_path(root_dir(pid),name)
    if target.exists(): raise HTTPException(409,"File đã tồn tại")
    data=await file.read(MAX_UPLOAD_MB*1024*1024+1)
    if len(data)>MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,f"Demo giới hạn upload {MAX_UPLOAD_MB} MB")
    target.write_bytes(data); return {"ok":True}

@app.post("/api/projects/{pid}/run-demo")
def run_demo(pid: str, data: FileData, user=Depends(current_user)):
    project_row(pid,user)
    target=safe_path(root_dir(pid),data.path)
    if target.suffix != ".py" or not target.is_file(): raise HTTPException(400,"Chỉ chạy file .py")
    if target.stat().st_size > MAX_FILE_BYTES: raise HTTPException(413,"File quá lớn")
    output=run_python_demo(target.read_text(encoding="utf-8",errors="replace"))
    return {"output":output,"mode":"safe-demo"}

@app.get("/api/health")
def health(): return {"ok":True,"mode":"render-demo"}
