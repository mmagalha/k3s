# f5_simulator.py
# F5 BIG-IP iControl REST API Simulator with Basic and Token Authentication
# 
# Default credentials:
#   Username: admin
#   Password: f5password
#
# These can be overridden with environment variables:
#   F5_USERNAME=myuser
#   F5_PASSWORD=mypassword
#
# Authentication methods supported:
#   1. Basic Authentication (HTTP Basic Auth)
#   2. Token Authentication (X-F5-Auth-Token header)
#
# Usage examples:
#   # Basic Auth
#   curl -u admin:f5password http://localhost:8080/mgmt/tm/ltm/pool
#   
#   # Token Auth
#   TOKEN=$(curl -X POST http://localhost:8080/mgmt/shared/authn/login \
#     -H "Content-Type: application/json" \
#     -d '{"username":"admin","password":"f5password","loginProviderName":"tmos"}' \
#     | jq -r '.token.token')
#   curl -H "X-F5-Auth-Token: $TOKEN" http://localhost:8080/mgmt/tm/sys
#   
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
import json
import re
import secrets
import traceback

# --- logging setup ---
# Configure root logger to capture uvicorn warnings
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# F5 simulator logger
logger = logging.getLogger("f5_simulator")
logger.setLevel(logging.DEBUG)

# Uvicorn access logger
access_logger = logging.getLogger("uvicorn.access")
access_logger.setLevel(logging.DEBUG)

# Create formatter
fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")

# Console handler
sh = logging.StreamHandler()
sh.setFormatter(fmt)
logger.addHandler(sh)
access_logger.addHandler(sh)

# File handler
fh = logging.FileHandler("f5_simulator.log")
fh.setFormatter(fmt)
logger.addHandler(fh)
access_logger.addHandler(fh)

# --- app & storage ---
app = FastAPI(title="Fake F5 iControl-REST Simulator")
security = HTTPBasic()

# Middleware para logging detalhado
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log da requisição recebida
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"🔍 INCOMING REQUEST: {request.method} {request.url} from {client_ip}")
    logger.info(f"📋 Headers: {dict(request.headers)}")
    
    try:
        # Ler body se disponível (sem consumir o stream)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    try:
                        body_str = body.decode('utf-8')
                        logger.info(f"📄 Body: {body_str}")
                    except Exception as e:
                        logger.warning(f"❌ Could not decode body: {e}")
                        logger.info(f"📄 Raw body bytes: {len(body)} bytes")
            except Exception as e:
                logger.warning(f"❌ Could not read body: {e}")
        
        response = await call_next(request)
        
        # Log da resposta
        logger.info(f"✅ RESPONSE: {response.status_code}")
        return response
        
    except Exception as e:
        logger.error(f"❌ REQUEST FAILED: {e}")
        logger.error(f"🔥 Traceback: {traceback.format_exc()}")
        raise

# Handler de exceção global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"🚨 UNHANDLED EXCEPTION: {exc}")
    logger.error(f"🔥 Request details: {request.method} {request.url}")
    logger.error(f"🔥 Headers: {dict(request.headers)}")
    logger.error(f"🔥 Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# Default credentials (can be overridden with environment variables)
import os
DEFAULT_USERNAME = os.getenv("F5_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("F5_PASSWORD", "f5password")

# Keyed by (partition, name) -> pool dict
POOLS: Dict[Tuple[str, str], Dict[str, Any]] = {}
# Members keyed by (partition, poolname) -> dict of memberName -> member dict
POOL_MEMBERS: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
# Virtuals keyed by (partition, name)
VIRTUALS: Dict[Tuple[str, str], Dict[str, Any]] = {}
# Active tokens for authentication
ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}


def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication credentials"""
    correct_username = secrets.compare_digest(credentials.username, DEFAULT_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, DEFAULT_PASSWORD)
    
    if not (correct_username and correct_password):
        logger.warning("Authentication failed for user: %s", credentials.username)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.debug("User authenticated: %s", credentials.username)
    return credentials.username


def authenticate_user_or_token(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    """Verify authentication via Basic Auth or Token (F5 style)"""
    # Check for token in X-F5-Auth-Token header first
    auth_token = request.headers.get("X-F5-Auth-Token")
    
    if auth_token:
        # Token authentication
        if auth_token in ACTIVE_TOKENS:
            token_info = ACTIVE_TOKENS[auth_token]
            
            # Check if token is expired
            import time
            current_micros = int(time.time() * 1000000)
            if current_micros > token_info["expiration"]:
                logger.warning(f"Token expired: {auth_token}")
                del ACTIVE_TOKENS[auth_token]
                raise HTTPException(
                    status_code=401,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Basic"},
                )
            
            logger.debug(f"Token authenticated: {token_info['username']}")
            return token_info["username"]
        else:
            logger.warning(f"Invalid token: {auth_token}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Basic"},
            )
    
    # Fall back to basic authentication
    return authenticate_user(credentials)


# helper to log request fully
async def log_request(req: Request):
    body_bytes = await req.body()
    try:
        body_text = body_bytes.decode("utf-8")
    except Exception:
        body_text = str(body_bytes)
    # try pretty JSON
    body_json = None
    try:
        body_json = json.loads(body_text) if body_text else None
        body_pretty = json.dumps(body_json, indent=2, ensure_ascii=False)
    except Exception:
        body_pretty = body_text
    logger.info("REQUEST %s %s", req.method, req.url.path)
    logger.debug("Headers: %s", dict(req.headers))
    logger.debug("Body: %s", body_pretty)
    return body_json

# utilities to parse F5 resource id URIs like "~Common~pool1" or "/Common/pool1"
def parse_f5_id(id_raw: str) -> Tuple[str, str]:
    """
    Accept forms:
      - ~Common~pool1
      - /Common/pool1
      - Common/pool1
      - pool1 (defaults to Common)
    Returns (partition, name)
    """
    if id_raw.startswith("~"):
        parts = id_raw.strip("~").split("~")
        if len(parts) >= 2:
            return parts[0], parts[1]
    if "/" in id_raw:
        parts = id_raw.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    # fallback
    return ("Common", id_raw)

# --- Authentication endpoints ---
@app.post("/mgmt/shared/authn/login")
async def login(request: Request):
    """F5 iControl REST authentication endpoint"""
    body_json = await log_request(request)
    if not body_json:
        raise HTTPException(status_code=400, detail="empty body")
    
    username = body_json.get("username")
    password = body_json.get("password")
    login_provider = body_json.get("loginProviderName", "tmos")
    
    # Validate credentials
    if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
        # Generate a fake token - usando formato similar ao da documentação
        import uuid
        token_uuid = str(uuid.uuid4()).replace('-', '').upper()[:26]  # Formato similar: VUT2YR667OICEHAEKWBGWOJ3HF
        
        # Calcular timestamps
        import time
        current_time = datetime.utcnow()
        start_time_iso = current_time.isoformat() + "Z"
        current_micros = int(current_time.timestamp() * 1000000)
        expiration_micros = current_micros + (1200 * 1000000)  # 1200 segundos = 20 minutos
        
        logger.info(f"✅ LOGIN SUCCESSFUL for user: {username}")
        
        # Formato exato baseado na documentação F5
        response = {
            "username": username,
            "loginReference": {
                "link": f"https://localhost/mgmt/cm/system/authn/providers/tmos/login"
            },
            "loginProviderName": login_provider,
            "token": {
                "token": token_uuid,
                "name": token_uuid,
                "userName": username,
                "authProviderName": login_provider,
                "user": {
                    "link": f"https://localhost/mgmt/cm/system/authn/providers/tmos/users/{str(uuid.uuid4())}"
                },
                "timeout": 1200,
                "startTime": start_time_iso,
                "address": "127.0.0.1",
                "partition": "[All]", 
                "generation": 1,
                "lastUpdateMicros": current_micros,
                "expirationMicros": expiration_micros,
                "kind": "shared:authz:tokens:authtokenitemstate",
                "selfLink": f"https://localhost/mgmt/shared/authz/tokens/{token_uuid}"
            },
            "generation": 0,
            "lastUpdateMicros": 0
        }
        
        # Armazenar token para validação posterior
        ACTIVE_TOKENS[token_uuid] = {
            "username": username,
            "expiration": expiration_micros,
            "created": current_micros
        }
        
        return response
    else:
        logger.warning(f"❌ LOGIN FAILED for user: {username}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

# --- System information endpoints ---
@app.get("/mgmt/tm/sys")
async def get_sys_info(request: Request, user: str = Depends(authenticate_user_or_token)):
    """F5 system information endpoint"""
    await log_request(request)
    
    logger.info("📊 SYSTEM INFO requested")
    return {
        "kind": "tm:sys:collectionstate",
        "selfLink": "https://localhost/mgmt/tm/sys?ver=17.1.0",
        "items": [
            {
                "reference": {
                    "link": "https://localhost/mgmt/tm/sys/application?ver=17.1.0"
                }
            },
            {
                "reference": {
                    "link": "https://localhost/mgmt/tm/sys/db?ver=17.1.0"
                }
            },
            {
                "reference": {
                    "link": "https://localhost/mgmt/tm/sys/global-settings?ver=17.1.0"
                }
            },
            {
                "reference": {
                    "link": "https://localhost/mgmt/tm/sys/provision?ver=17.1.0"
                }
            }
        ]
    }

@app.get("/mgmt/tm/sys/global-settings")
async def get_global_settings(request: Request, user: str = Depends(authenticate_user_or_token)):
    """F5 global settings endpoint"""
    await log_request(request)
    
    return {
        "kind": "tm:sys:global-settings:globalsettingsstate",
        "selfLink": "https://localhost/mgmt/tm/sys/global-settings?ver=17.1.0",
        "entries": {
            "https://localhost/mgmt/tm/sys/global-settings/0": {
                "nestedStats": {
                    "entries": {
                        "hostname": {"description": "f5-simulator"},
                        "product": {"description": "BIG-IP VE"},
                        "version": {"description": "17.1.0"},
                        "edition": {"description": "Point Release 1"},
                        "userMode": {"description": "Appliance"},
                        "builtOn": {"description": "241118 184920"},
                        "jobId": {"description": "1234567"}
                    }
                }
            }
        }
    }

# Endpoint adicional para validação de tokens
@app.get("/mgmt/shared/authz/tokens/{token_id}")
async def get_token_info(token_id: str, request: Request):
    """F5 token information endpoint"""
    await log_request(request)
    
    if token_id in ACTIVE_TOKENS:
        token_info = ACTIVE_TOKENS[token_id]
        
        # Check if token is expired
        import time
        current_micros = int(time.time() * 1000000)
        if current_micros > token_info["expiration"]:
            logger.warning(f"Token expired: {token_id}")
            del ACTIVE_TOKENS[token_id]
            raise HTTPException(status_code=404, detail="Token not found or expired")
        
        return {
            "token": token_id,
            "name": token_id,
            "userName": token_info["username"],
            "authProviderName": "tmos",
            "user": {
                "link": f"https://localhost/mgmt/cm/system/authn/providers/tmos/users/{token_info['username']}"
            },
            "timeout": 1200,
            "address": "127.0.0.1",
            "partition": "[All]",
            "generation": 1,
            "lastUpdateMicros": token_info["created"],
            "expirationMicros": token_info["expiration"],
            "kind": "shared:authz:tokens:authtokenitemstate",
            "selfLink": f"https://localhost/mgmt/shared/authz/tokens/{token_id}"
        }
    else:
        raise HTTPException(status_code=404, detail="Token not found")

# --- Pools collection ---
@app.options("/mgmt/tm/ltm/pool")
@app.get("/mgmt/tm/ltm/pool")
async def list_pools(request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    items = []
    for (partition, name), p in POOLS.items():
        item = p.copy()
        item.setdefault("tmPartition", partition)
        item["name"] = name
        items.append(item)
    return {"items": items, "kind": "tm:ltm:pool:poolcollectionstate", "selfLink": "/mgmt/tm/ltm/pool"}

@app.post("/mgmt/tm/ltm/pool", status_code=201)
async def create_pool(request: Request, user: str = Depends(authenticate_user_or_token)):
    body_json = await log_request(request)
    if not body_json:
        raise HTTPException(status_code=400, detail="empty body")
    # expected minimal fields: name or fullPath, tmPartition or partition
    name = body_json.get("name") or body_json.get("fullPath") or body_json.get("partition")
    # better: look for 'name' else 'fullPath' else 'fullPath' with /Common/...
    if "name" in body_json:
        name = body_json["name"]
    elif "fullPath" in body_json:
        # fullPath like /Common/pool1
        fp = body_json["fullPath"]
        parts = fp.strip("/").split("/")
        partition = parts[0] if len(parts) > 1 else "Common"
        name = parts[-1]
    if not name:
        raise HTTPException(status_code=400, detail="missing name")
    partition = body_json.get("tmPartition") or body_json.get("partition") or "Common"
    key = (partition, name)
    # create canonical pool representation (pick fields from body)
    pool = {
        "name": name,
        "tmPartition": partition,
        "description": body_json.get("description", ""),
        "loadBalancingMode": body_json.get("loadBalancingMode", body_json.get("lb_method", "round-robin")),
        "minUpMembers": body_json.get("minUpMembers", body_json.get("min_up_members", 0)),
        "minUpMembersAction": body_json.get("minUpMembersAction", body_json.get("min_up_members_action", "failover")),
        "minUpMembersChecking": body_json.get("minUpMembersChecking", body_json.get("min_up_members_checking", "disabled")),
        "monitor": body_json.get("monitor") or body_json.get("monitor_type") or body_json.get("monitor_type", "none"),
        "membersReference": {"link": f"/mgmt/tm/ltm/pool/~{partition}~{name}/members"},
        "selfLink": f"/mgmt/tm/ltm/pool/~{partition}~{name}"
    }
    POOLS[key] = pool
    POOL_MEMBERS.setdefault(key, {})
    logger.info("POOL CREATED %s/%s", partition, name)
    return pool

# resource operations
@app.get("/mgmt/tm/ltm/pool/{resource_id}")
async def get_pool(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, name = parse_f5_id(resource_id)
    key = (partition, name)
    if key not in POOLS:
        raise HTTPException(status_code=404, detail="pool not found")
    return POOLS[key]

@app.put("/mgmt/tm/ltm/pool/{resource_id}")
@app.patch("/mgmt/tm/ltm/pool/{resource_id}")
async def update_pool(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    body_json = await log_request(request)
    partition, name = parse_f5_id(resource_id)
    key = (partition, name)
    if key not in POOLS:
        raise HTTPException(status_code=404, detail="pool not found")
    pool = POOLS[key]
    # merge shallow fields
    for k, v in (body_json or {}).items():
        # map known field names to canonical
        if k in ("loadBalancingMode", "lb_method"):
            pool["loadBalancingMode"] = v
        elif k in ("minUpMembers", "min_up_members"):
            pool["minUpMembers"] = v
        elif k in ("monitor", "monitor_type"):
            pool["monitor"] = v
        else:
            pool[k] = v
    logger.info("POOL UPDATED %s/%s", partition, name)
    return pool

@app.delete("/mgmt/tm/ltm/pool/{resource_id}")
async def delete_pool(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, name = parse_f5_id(resource_id)
    key = (partition, name)
    if key in POOLS:
        del POOLS[key]
        POOL_MEMBERS.pop(key, None)
        logger.info("POOL DELETED %s/%s", partition, name)
        return {"message": "deleted"}
    raise HTTPException(status_code=404, detail="pool not found")

# --- Pool members collection (collection endpoint) ---
@app.get("/mgmt/tm/ltm/pool/{resource_id}/members")
async def list_pool_members(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, poolname = parse_f5_id(resource_id)
    key = (partition, poolname)
    if key not in POOLS:
        raise HTTPException(status_code=404, detail="pool not found")
    members = list(POOL_MEMBERS.get(key, {}).values())
    return {"items": members, "selfLink": f"/mgmt/tm/ltm/pool/~{partition}~{poolname}/members"}

@app.post("/mgmt/tm/ltm/pool/{resource_id}/members", status_code=201)
async def create_pool_member(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    body_json = await log_request(request)
    partition, poolname = parse_f5_id(resource_id)
    key = (partition, poolname)
    if key not in POOLS:
        raise HTTPException(status_code=404, detail="pool not found")
    if not body_json:
        raise HTTPException(status_code=400, detail="empty body")
    # a member natural key may be 'name' or 'address' or 'fullPath' -- we'll use 'name' or fallback to address
    member_name = body_json.get("name") or body_json.get("address") or f"{poolname}:{body_json.get('port','0')}"
    members = POOL_MEMBERS.setdefault(key, {})
    member = {
        "name": member_name,
        "address": body_json.get("address"),
        "port": body_json.get("port"),
        "description": body_json.get("description", ""),
        "session": body_json.get("session", "user-enabled"),
        "ratio": body_json.get("ratio", 1),
        "state": body_json.get("state", "user-up"),
        "selfLink": f"/mgmt/tm/ltm/pool/~{partition}~{poolname}/members/~{partition}~{member_name}"
    }
    members[member_name] = member
    logger.info("POOL MEMBER CREATED %s/%s -> %s", partition, poolname, member_name)
    return member

@app.get("/mgmt/tm/ltm/pool/{resource_id}/members/{member_id}")
async def get_pool_member(resource_id: str, member_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, poolname = parse_f5_id(resource_id)
    mpart, mname = parse_f5_id(member_id)
    # member id may contain ~partition~membername — prefer extracted mname
    key = (partition, poolname)
    if key not in POOLS:
        raise HTTPException(status_code=404, detail="pool not found")
    members = POOL_MEMBERS.get(key, {})
    # member key may be mname
    mm = members.get(mname) or members.get(member_id)
    if not mm:
        raise HTTPException(status_code=404, detail="member not found")
    return mm

@app.put("/mgmt/tm/ltm/pool/{resource_id}/members/{member_id}")
@app.patch("/mgmt/tm/ltm/pool/{resource_id}/members/{member_id}")
async def update_pool_member(resource_id: str, member_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    body_json = await log_request(request)
    partition, poolname = parse_f5_id(resource_id)
    _, mname = parse_f5_id(member_id)
    key = (partition, poolname)
    members = POOL_MEMBERS.get(key, {})
    if mname not in members:
        raise HTTPException(status_code=404, detail="member not found")
    member = members[mname]
    for k, v in (body_json or {}).items():
        member[k] = v
    logger.info("POOL MEMBER UPDATED %s/%s -> %s", partition, poolname, mname)
    return member

@app.delete("/mgmt/tm/ltm/pool/{resource_id}/members/{member_id}")
async def delete_pool_member(resource_id: str, member_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, poolname = parse_f5_id(resource_id)
    _, mname = parse_f5_id(member_id)
    key = (partition, poolname)
    members = POOL_MEMBERS.get(key, {})
    if mname in members:
        del members[mname]
        logger.info("POOL MEMBER DELETED %s/%s -> %s", partition, poolname, mname)
        return {"message": "deleted"}
    raise HTTPException(status_code=404, detail="member not found")

# --- Virtuals ---
@app.get("/mgmt/tm/ltm/virtual")
async def list_virtuals(request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    items = []
    for (partition, name), v in VIRTUALS.items():
        item = v.copy()
        item.setdefault("tmPartition", partition)
        item["name"] = name
        items.append(item)
    return {"items": items, "selfLink": "/mgmt/tm/ltm/virtual"}

@app.post("/mgmt/tm/ltm/virtual", status_code=201)
async def create_virtual(request: Request, user: str = Depends(authenticate_user_or_token)):
    body_json = await log_request(request)
    if not body_json:
        raise HTTPException(status_code=400, detail="empty body")
    name = body_json.get("name") or (body_json.get("fullPath") and body_json["fullPath"].split("/")[-1])
    if not name:
        raise HTTPException(status_code=400, detail="missing name")
    partition = body_json.get("tmPartition") or body_json.get("partition") or "Common"
    key = (partition, name)
    virtual = {
        "name": name,
        "tmPartition": partition,
        "description": body_json.get("description", ""),
        "destination": body_json.get("destination"),
        "pool": body_json.get("pool"),
        "enabled": body_json.get("enabled", True),
        "connectionLimit": body_json.get("connectionLimit", 0),
        "selfLink": f"/mgmt/tm/ltm/virtual/~{partition}~{name}"
    }
    VIRTUALS[key] = virtual
    logger.info("VIRTUAL CREATED %s/%s", partition, name)
    return virtual

@app.get("/mgmt/tm/ltm/virtual/{resource_id}")
async def get_virtual(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, name = parse_f5_id(resource_id)
    key = (partition, name)
    if key not in VIRTUALS:
        raise HTTPException(status_code=404, detail="virtual not found")
    return VIRTUALS[key]

@app.put("/mgmt/tm/ltm/virtual/{resource_id}")
@app.patch("/mgmt/tm/ltm/virtual/{resource_id}")
async def update_virtual(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    body_json = await log_request(request)
    partition, name = parse_f5_id(resource_id)
    key = (partition, name)
    if key not in VIRTUALS:
        raise HTTPException(status_code=404, detail="virtual not found")
    v = VIRTUALS[key]
    for k, val in (body_json or {}).items():
        v[k] = val
    logger.info("VIRTUAL UPDATED %s/%s", partition, name)
    return v

@app.delete("/mgmt/tm/ltm/virtual/{resource_id}")
async def delete_virtual(resource_id: str, request: Request, user: str = Depends(authenticate_user_or_token)):
    await log_request(request)
    partition, name = parse_f5_id(resource_id)
    key = (partition, name)
    if key in VIRTUALS:
        del VIRTUALS[key]
        logger.info("VIRTUAL DELETED %s/%s", partition, name)
        return {"message": "deleted"}
    raise HTTPException(status_code=404, detail="virtual not found")

# root health
@app.get("/")
async def root():
    return {
        "ok": True, 
        "time": datetime.utcnow().isoformat(),
        "auth": "Basic authentication required",
        "default_credentials": f"username: {DEFAULT_USERNAME}, password: {DEFAULT_PASSWORD}"
    }

# Catch-all para capturar requisições não mapeadas
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    logger.warning(f"🔍 UNMAPPED ENDPOINT: {request.method} /{path}")
    logger.warning(f"📋 Headers: {dict(request.headers)}")
    
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                body_str = body.decode('utf-8')
                logger.warning(f"📄 Body: {body_str}")
        except Exception as e:
            logger.warning(f"❌ Could not read body: {e}")
    
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found", 
            "method": request.method,
            "path": f"/{path}",
            "available_endpoints": [
                "GET /",
                "GET /mgmt/tm/ltm/pool",
                "POST /mgmt/tm/ltm/pool",
                "GET /mgmt/tm/ltm/pool/{id}",
                "PUT/PATCH /mgmt/tm/ltm/pool/{id}",
                "DELETE /mgmt/tm/ltm/pool/{id}",
                "GET /mgmt/tm/ltm/pool/{id}/members",
                "POST /mgmt/tm/ltm/pool/{id}/members",
                "# ... and virtual server endpoints"
            ]
        }
    )

# run with: uvicorn f5_simulator:app --host 0.0.0.0 --port 8080
if __name__ == "__main__":
    logger.info("🚀 Starting F5 Simulator with detailed logging...")
    logger.info(f"👤 Default credentials: {DEFAULT_USERNAME}:{DEFAULT_PASSWORD}")
    
    uvicorn.run(
        "f5_simulator:app", 
        host="0.0.0.0", 
        port=8080, 
        log_level="debug",
        access_log=True,
        reload=False,
        loop="asyncio"
    )
