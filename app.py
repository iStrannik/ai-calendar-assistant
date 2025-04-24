import os
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import FastAPI, Depends, Request
from starlette.config import Config
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import random
from  google_calendar_api_operations import GoogleCalendarAPIOperationsExecutor
import uuid
import gradio as gr
from ast_visitor import MyVisitor
from prompt import MLMessager

app = FastAPI()

# Replace these with your own OAuth settings
GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""
ML_API_KEY = ""
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
    if user:
        return user['access_token'] + '\n' + user['userinfo']['name']
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
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.route('/auth')
async def auth(request: Request):
    try:
        access_token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse(url='/')
    request.session['user'] = access_token
    return RedirectResponse(url='/')

with gr.Blocks() as login_demo:
    gr.Button("Login", link="/login")

app = gr.mount_gradio_app(app, login_demo, path="/login-demo")


messenger = MLMessager(ML_API_KEY)



def random_response(request: gr.Request, message, history):
    access_token, username = request.username.split('\n')
    res = messenger.send_message(message)
    
    gexec = GoogleCalendarAPIOperationsExecutor(access_token, username)

    function_map = {
        "add_meeting": gexec.add_meeting,
        "delete_meeting": gexec.delete_meeting
    }
    
    parsed_result, user_text = messenger.parse_results(res)

    for func_name, args in parsed_result:
        if func_name in function_map:
            function_map[func_name](**args)
    
    # return f'{username}, here is your access_token: {access_token}\n' + '\n'.join(list(map(lambda x: x[1], res)))
    return user_text

demo = gr.ChatInterface(
    fn=random_response,
    type="messages"
)

io = demo

app = gr.mount_gradio_app(app, io, path="/gradio", auth_dependency=get_user)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=31337)
