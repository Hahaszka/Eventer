import os
import io
import json
import uuid
import asyncio
import logging
import pandas as pd
import pdfplumber
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, BackgroundTasks, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, func, or_

# --- KONFIGURACJA LOGÓW DO TERMINALA NA FRONCIE ---
log_buffer = []
class ListHandler(logging.Handler):
    def emit(self, record):
        log_buffer.append(self.format(record))
        if len(log_buffer) > 100: log_buffer.pop(0) # Trzymamy tylko 100 ostatnich logów

terminal_logger = logging.getLogger("terminal")
terminal_logger.setLevel(logging.INFO)
terminal_logger.addHandler(ListHandler())

from app.database import engine, Base, get_db, AsyncSessionLocal
from app.models import User, WarehouseProduct, VerifiedMapping
from app.schemas import UserCreate, Token, ProductBase, MappingBase, PasswordUpdate
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.core import AsyncHybridSearchEngine, AsyncLocalLLMVerifier

templates = Jinja2Templates(directory="app/templates")
upload_tasks = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        admin_user = os.getenv("INITIAL_ADMIN_USER", "admin")
        admin_pass = os.getenv("INITIAL_ADMIN_PASS", "admin")
        res = await db.execute(select(User).filter(User.username == admin_user))
        if not res.scalars().first():
            db.add(User(username=admin_user, hashed_password=get_password_hash(admin_pass)))
            await db.commit()
    yield
    await engine.dispose()

app = FastAPI(title="WMS Entity Resolution AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ==========================================
# BEZPIECZNE SERWOWANIE STRON (ROUTING)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request, access_token: str = Cookie(None)):
    if access_token: return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db), access_token: str = Cookie(None)):
    if not access_token: return RedirectResponse(url="/", status_code=303)
    try:
        user = await get_current_user(token=access_token, db=db)
        if not user: raise Exception()
    except:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("access_token")
        return response
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

# ==========================================
# API AUTH & UŻYTKOWNICY
# ==========================================
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Zły login lub hasło")
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    res = await db.execute(select(User))
    return [{"id": x.id, "username": x.username, "is_active": x.is_active} for x in res.scalars().all()]

@app.post("/users")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    if (await db.execute(select(User).filter(User.username == user.username))).scalars().first():
        raise HTTPException(status_code=400, detail="Użytkownik już istnieje")
    db.add(User(username=user.username, hashed_password=get_password_hash(user.password)))
    await db.commit()
    return {"status": "success"}

@app.put("/users/{uid}/password")
async def update_password(uid: int, pwd: PasswordUpdate, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    user = await db.get(User, uid)
    if not user: raise HTTPException(status_code=404)
    user.hashed_password = get_password_hash(pwd.new_password)
    await db.commit()
    return {"status": "success"}

@app.delete("/users/{uid}")
async def delete_user(uid: int, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    user = await db.get(User, uid)
    if user and user.username != u.username:
        await db.delete(user)
        await db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Błąd usuwania")

# ==========================================
# LAZY LOADING DLA DATATABLES (Server-Side)
# ==========================================
@app.get("/products/datatable")
async def get_products_dt(draw: int, start: int, length: int, search_value: str = "", db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    query = select(WarehouseProduct)
    if search_value:
        query = query.filter(or_(WarehouseProduct.product_name.ilike(f"%{search_value}%"), WarehouseProduct.sku_code.ilike(f"%{search_value}%")))
    
    total = await db.execute(select(func.count()).select_from(WarehouseProduct))
    filtered = await db.execute(select(func.count()).select_from(query.subquery()))
    
    res = await db.execute(query.offset(start).limit(length))
    data = [{"id": p.id, "sku": p.sku_code, "name": p.product_name} for p in res.scalars().all()]
    return {"draw": draw, "recordsTotal": total.scalar(), "recordsFiltered": filtered.scalar(), "data": data}

@app.get("/mappings/datatable")
async def get_mappings_dt(draw: int, start: int, length: int, search_value: str = "", db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    query = select(VerifiedMapping)
    if search_value:
        query = query.filter(or_(VerifiedMapping.ocr_text.ilike(f"%{search_value}%"), VerifiedMapping.sku_code.ilike(f"%{search_value}%")))
    
    total = await db.execute(select(func.count()).select_from(VerifiedMapping))
    filtered = await db.execute(select(func.count()).select_from(query.subquery()))
    
    res = await db.execute(query.offset(start).limit(length))
    data = [{"id": m.id, "ocr_text": m.ocr_text, "sku": m.sku_code, "name": m.product_name} for m in res.scalars().all()]
    return {"draw": draw, "recordsTotal": total.scalar(), "recordsFiltered": filtered.scalar(), "data": data}

# ==========================================
# CRUD: PRODUKTY I SŁOWNIK
# ==========================================
@app.post("/products/manual")
async def add_product_manual(prod: ProductBase, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    vec = await AsyncHybridSearchEngine(db)._generate_embedding(prod.name)
    db.add(WarehouseProduct(sku_code=prod.sku, product_name=prod.name, category=prod.cat, embedding=vec))
    await db.commit()
    return {"status": "success"}

@app.put("/products/{pid}")
async def update_product(pid: int, prod: ProductBase, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    p = await db.get(WarehouseProduct, pid)
    if not p: raise HTTPException(status_code=404)
    if p.product_name != prod.name:
        p.embedding = await AsyncHybridSearchEngine(db)._generate_embedding(prod.name)
    p.product_name, p.sku_code = prod.name, prod.sku
    await db.commit()
    return {"status": "success"}

@app.delete("/products/{pid}")
async def delete_product(pid: int, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    p = await db.get(WarehouseProduct, pid); await db.delete(p); await db.commit()
    return {"status": "success"}

@app.post("/mappings/manual")
async def add_map_manual(m: MappingBase, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    db.add(VerifiedMapping(ocr_text=m.ocr_text, sku_code=m.sku_code, product_name=m.product_name))
    await db.commit()
    return {"status": "success"}

@app.put("/mappings/{mid}")
async def update_mapping(mid: int, m: MappingBase, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    db_m = await db.get(VerifiedMapping, mid)
    db_m.ocr_text, db_m.sku_code, db_m.product_name = m.ocr_text, m.sku_code, m.product_name
    await db.commit()
    return {"status": "success"}

@app.delete("/mappings/{mid}")
async def delete_map(mid: int, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    m = await db.get(VerifiedMapping, mid); await db.delete(m); await db.commit()
    return {"status": "success"}

@app.get("/search-products")
async def search_products(q: str, db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    if len(q) < 2: return []
    res = await db.execute(select(WarehouseProduct).filter(WarehouseProduct.product_name.ilike(f"%{q}%")).limit(15))
    return [{"sku": x.sku_code, "name": x.product_name} for x in res.scalars().all()]

# ==========================================
# UPLOADS & ZADANIA W TLE (Z LOGOWANIEM)
# ==========================================
@app.get("/logs")
async def get_logs(u: User = Depends(get_current_user)):
    return {"logs": log_buffer}

async def process_master_task(task_id: str, df: pd.DataFrame):
    try:
        terminal_logger.info(f"🚀 Rozpoczęto wektoryzację bazy. Oczekujące pozycje: {len(df)}")
        async with AsyncSessionLocal() as db:
            ai = AsyncHybridSearchEngine(db)
            total = len(df)
            upload_tasks[task_id] = {"status": "processing", "current": 0, "total": total}
            
            for i, row in df.iterrows():
                sku, name = str(row.get('ean', f"ID-{i}")).strip(), str(row.get('name', '')).strip()
                if name:
                    if i % 10 == 0: terminal_logger.info(f"⚙️ Wektoryzowanie [{i+1}/{total}]: {name[:35]}...")
                    vec = await ai._generate_embedding(name)
                    db.add(WarehouseProduct(sku_code=sku, product_name=name, category="Import", embedding=vec))
                
                upload_tasks[task_id]["current"] = i + 1
                if i % 25 == 0: await db.commit()
                
            await db.commit()
            upload_tasks[task_id]["status"] = "completed"
            terminal_logger.info("✅ Proces wektoryzacji bazy zakończony pomyślnie!")
    except Exception as e:
        terminal_logger.error(f"❌ Błąd krytyczny wektoryzatora: {str(e)}")
        upload_tasks[task_id] = {"status": "error", "error": str(e)}

@app.post("/upload-master-data")
async def upload_master(background_tasks: BackgroundTasks, file: UploadFile = File(...), u: User = Depends(get_current_user)):
    contents = await file.read()
    try: df = pd.read_csv(io.BytesIO(contents), sep=';', dtype=str, encoding='utf-8')
    except: df = pd.read_csv(io.BytesIO(contents), sep=';', dtype=str, encoding='cp1250')
    task_id = str(uuid.uuid4())
    background_tasks.add_task(process_master_task, task_id, df)
    return {"task_id": task_id}

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    return upload_tasks.get(task_id, {"status": "not_found"})

@app.post("/upload-mappings")
async def upload_mappings(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    contents = await file.read()
    try: df = pd.read_csv(io.BytesIO(contents), sep=';', dtype=str, encoding='utf-8')
    except: df = pd.read_csv(io.BytesIO(contents), sep=';', dtype=str, encoding='cp1250')
    ins = 0
    for _, row in df.iterrows():
        ocr, sku, name = str(row.get('name_from_invoice','')).strip(), str(row.get('wh_product_number','')).strip(), str(row.get('name_from_avalio','')).strip()
        if ocr:
            stmt = select(VerifiedMapping).filter_by(ocr_text=ocr)
            if not (await db.execute(stmt)).scalars().first():
                db.add(VerifiedMapping(ocr_text=ocr, sku_code=sku, product_name=name))
                ins += 1
    await db.commit()
    terminal_logger.info(f"✅ Zapisano {ins} nowych dopasowań historycznych do Pamięci AI.")
    return {"status": "success", "inserted": ins}

@app.post("/upload-invoice")
async def process_invoice(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), u: User = Depends(get_current_user)):
    contents = await file.read()
    ai = AsyncHybridSearchEngine(db)
    v = AsyncLocalLLMVerifier()

    if file.filename.lower().endswith(".pdf") or file.content_type == "application/pdf":
        terminal_logger.info(f"📄 Wykryto plik PDF: {file.filename}. Wyodrębniam tekst...")
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            text_content = "\\n".join([page.extract_text() or "" for page in pdf.pages])
        
        terminal_logger.info("🤖 Uruchamiam model LLM do wyodrębnienia pozycji z faktury PDF...")
        items = await v.extract_items_from_text(text_content)
        terminal_logger.info(f"✅ LLM znalazł {len(items)} pozycji na fakturze PDF.")
        
    elif file.filename.lower().endswith(".json") or file.content_type == "application/json":
        terminal_logger.info(f"📄 Wykryto plik JSON: {file.filename}.")
        try:
            data = json.loads(contents.decode('utf-8'))
            if isinstance(data, dict):
                items = next((val for val in data.values() if isinstance(val, list)), [])
            elif isinstance(data, list):
                items = data
            else: items = []
            if items and isinstance(items[0], dict):
                items = [i.get('name_from_invoice', i.get('name', str(i))) for i in items]
        except Exception as e:
            terminal_logger.error(f"❌ Błąd parsowania JSON: {e}")
            items = []
    else:
        terminal_logger.info(f"📄 Wykryto plik CSV: {file.filename}.")
        try: df = pd.read_csv(io.BytesIO(contents), sep=';', dtype=str, encoding='utf-8')
        except: df = pd.read_csv(io.BytesIO(contents), sep=';', dtype=str, encoding='cp1250')
        if 'name_from_invoice' in df.columns:
            items = df['name_from_invoice'].dropna().tolist()
        else:
            items = [str(x) for x in df.iloc[:, 0].dropna().tolist()]

    if not items:
        terminal_logger.warning("⚠️ Nie znaleziono żadnych pozycji w pliku!")
        return {"results": []}

    terminal_logger.info(f"🚀 Zaczynamy AI Entity Resolution dla {len(items)} pozycji...")
    
    async def res_item(it):
        m = (await db.execute(select(VerifiedMapping).filter_by(ocr_text=it))).scalars().first()
        if m: return {"faktura": it, "sku": m.sku_code, "baza": m.product_name, "is_match": True, "reasoning": "🧠 Słownik"}
        c = await ai.search(it, top_k=1)
        if not c: return {"faktura": it, "sku": "", "baza": "Brak", "is_match": False, "reasoning": "Brak w DB"}
        best = c[0]
        if float(best['final_score']) > 0.85: return {"faktura": it, "sku": best['sku_code'], "baza": best['product_name'], "is_match": True, "reasoning": "⚡ Auto-Match"}
        dec = await v.verify_match(it, best)
        return {"faktura": it, "sku": best['sku_code'], "baza": best['product_name'], "is_match": dec['is_match'], "reasoning": f"🤖 LLM: {dec['reasoning']}"}
        
    results = await asyncio.gather(*[res_item(i) for i in items])
    terminal_logger.info("✅ Analiza faktury zakończona. Oczekuję na weryfikację użytkownika.")
    return {"results": results}