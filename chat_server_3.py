from email import message

import random
import hashlib
import secrets
from typing import Annotated
from fastapi import Cookie
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi import Request, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, Relationship,SQLModel, create_engine, Session, select 



templates = Jinja2Templates(directory="templates")
app: FastAPI = FastAPI()

sqlite_url = "sqlite:///store.db"
engine = create_engine(
    sqlite_url, 
    connect_args = {"check_same_thread": False})


class User(SQLModel, table=True):
    id : int | None = Field(default=None, primary_key=True)
    name: str
    password_hash : str
    messages : list["ChatMessage"] = Relationship(back_populates="user")
    sessions: list["UserSession"] = Relationship(back_populates="user")

# A single chat message sent by one user.
class ChatMessage(SQLModel, table=True):
    id : int | None = Field(default=None, primary_key=True)
    message: str
    user_id : int = Field(foreign_key="user.id")
    name : str | None = None
    user : User | None = Relationship(back_populates= "messages")


# The response returned by the polling endpoint.
class PollResponse(SQLModel):
    messages: list[ChatMessage]


# Small response model used after a message is accepted.
class SendResponse(SQLModel):
    ok: bool




class UserSession(SQLModel, table= True) :
    id : int | None = Field(default=None, primary_key=True)
    name: str
    user_id : int = Field(foreign_key="user.id")
    token : str
    user : User= Relationship(back_populates = "sessions")
     
   
        #qd je me connecte, je crée un token de session et je l'associe à un utilisateur avec les cookies 
        # 
class Login(SQLModel):
    password : str
    user_name : str = Field(foreign_key = "user.name")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()
      
def random_token() -> str :
    return secrets.token_hex(16)


# Static HTML page served by the `/chat` route.
@app.get("/login", response_class= HTMLResponse )
async def login_page(request: Request) :
    return templates.TemplateResponse(request=request,
                                      name="login_0.html",
                                      context= {})
             
@app.post("/login") 
async def login(login : Login, response : Response) :
    with Session(engine) as session:
        statement = select(User).where(User.name == login.user_name)
        user = session.exec(statement).first()

        if user is None or user.password_hash != hash_password(login.password) :
            return {"detail" : "Mauvais nom d'utilisateur où mot de passe"}
        
        token = random_token()
        user_session = UserSession(name=user.name, 
                                   user_id = user.id,
                                    token= token)
        session.add(user_session)
        session.commit()

        response.set_cookie(key = "session_id",value = token, httponly=True )

        return {"message" : "Connexion réusie"}

@app.post("/register")
async def register(login : Login, response : Response) :
    with Session(engine) as session :
        statement = select(User).where(User.name == login.user_name)
        user = session.exec(statement).first()

        if user is not None :
            return {"detail" : "Nom d'utilisateur non disponible"}
        
        user = User(name = login.user_name, password_hash = hash_password(login.password))
        session.add(user)
        session.commit()
        session.refresh(user)

        token = random_token()
        user_session = UserSession(name = user.name,
                                   user_id = user.id,
                                   token = token)
        session.add(user_session)
        session.commit()
        response.set_cookie(key="session_id", value= token,
                            httponly= True)
        return {"message" : "Inscription reussie"}
    


    

@app.get("/session")
async def read_session(
    session_id: Annotated[str | None, Cookie()] = None,
):
 with Session(engine) as session:
     statement = select(UserSession).where(UserSession.token == session_id)
     user_session = session.exec(statement).first()
 return user_session.user.name     


  # qd je recois une requete, je regarde les cookies, je trouve le token de session, je trouve l'utilisateur associé à ce token, et je lui affiche son nom sur la page de chat
      # si l'utilisateur n'est pas connecté, je lui affiche un formulaire de connexion, et qd il se connecte, je crée une session pour lui et je lui affiche son nom sur la page de chat
@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request, session_id : Annotated[str| None, Cookie()] = None) -> str:
    """Serve the chat client page. Returns HTTP 200 on success."""
    with Session(engine) as session:
        statement = select(UserSession).where(UserSession.token == session_id)
        user_session = session.exec(statement).first()

        if user_session is None :
            return templates.TemplateResponse(request = request,
                                              name = "login_0.html",
                                              context = {})
        else :
            user_name = user_session.user.name
            return templates.TemplateResponse(request = request,
                                              name = "chat_1.html",
                                              context = {"user_name" : user_name})

@app.get("/poll", response_model=PollResponse)
async def poll() -> PollResponse:
    """Return the current message history. Returns HTTP 200 on success."""
    with Session(engine) as session:
        statement = select(ChatMessage).order_by(ChatMessage.id)
        messages = session.exec(statement).all()
        for m in messages :
            if m.user :
                m.name = m.user.name
            else :
                m.name = "Utilisateur inconnu"
    return PollResponse(messages=list(messages))

@app.post("/send", response_model=SendResponse)
async def send(msg: ChatMessage, session_id : Annotated[str|None,Cookie()]=None) -> SendResponse:
    """Store one new chat message. Returns HTTP 200 on success."""
    with Session(engine) as session:
        statement = select(UserSession).where(UserSession.token == session_id)
        user_session = session.exec(statement).first()

        if user_session is None :
            return {"detail" : "Utilisateur non connecté"}
        
        msg.user_id = user_session.user_id
        msg.id = None
        session.add(msg)
        session.commit()
    return SendResponse(ok=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
