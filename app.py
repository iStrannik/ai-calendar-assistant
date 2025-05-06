import os
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import FastAPI, Depends, Request
from starlette.config import Config
from google.oauth2.credentials import Credentials
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from  google_calendar_api_operations import GoogleCalendarAPIOperationsExecutor
import uuid
import re
import gradio as gr
from ast_visitor import MyVisitor
from prompt import MLMessager

app = FastAPI()

# Replace these with your own OAuth settings
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID") or ""
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET") or ""
ML_API_KEY = os.environ.get("ML_API_KEY") or ""
SECRET_KEY = uuid.uuid4().hex

config_data = {'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/calendar'},
)

SECRET_KEY = os.environ.get('SECRET_KEY') or "a_very_secret_key"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Dependency to get the current user
def get_user(request: Request):
    user = request.session.get('user')
    # print(user)
    if user:
        return user['access_token'] + '\n' + user['userinfo']['name'] + '\n' + user['userinfo']['email']
    return None

@app.get('/')
def public(user: dict = Depends(get_user)):
    if user:
        return RedirectResponse(url='/gradio')
    else:
        return RedirectResponse(url='/login-demo')

@app.route('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')

@app.route('/login')
async def login(request: Request):
    redirect_uri = 'https://ai-calendar-assistant.ru/auth'
    tmp = await oauth.google.authorize_redirect(request, redirect_uri, access_type='offline')
    print(tmp)
    return tmp

@app.route('/auth')
async def auth(request: Request):
    try:
        access_token = await oauth.google.authorize_access_token(request)
        print(access_token)
    except OAuthError:
        return RedirectResponse(url='/')
    request.session['user'] = access_token
    
    
    
    return RedirectResponse(url='/')

with gr.Blocks() as login_demo:
    gr.Button("Login", link="/login")

app = gr.mount_gradio_app(app, login_demo, path="/login-demo")


messenger = MLMessager(ML_API_KEY)



def response(request: gr.Request, message, history):
    print(request.session)
    
    access_token, username, mail = request.username.split('\n')
    res = messenger.send_message(message)
    
    print(res)

        
    # access_token = session['user']['access_token']
    creds = Credentials(token=access_token, client_secret=GOOGLE_CLIENT_SECRET, client_id=GOOGLE_CLIENT_ID, refresh_token=None)
    gexec = GoogleCalendarAPIOperationsExecutor(creds, mail, "Europe/Moscow")

    function_map = {
        "add_meeting": gexec.add_meeting,
        "delete_meeting": gexec.delete_meeting,
        "find_slots": gexec.find_slots,
        "change_meeting": gexec.change_meeting
    }
    comment = res[0][1]
    for func_call in res[0][0]:
        res_func = function_map[func_call[0]](**func_call[1])
        comment += "\n"
        if res_func is None:
            continue
        comment += res_func
    return comment
    # return f'{username} and {mail}, here is your access_token: {access_token}\n' + '\n'.join(list(map(lambda x: x[1], res)))
    # return request

demo = gr.ChatInterface(
    fn=response,
    type="messages"
)

io = demo

app = gr.mount_gradio_app(app, io, path="/gradio", auth_dependency=get_user)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=31337)