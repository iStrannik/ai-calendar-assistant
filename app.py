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


def extract_function_call(text, function_names):
    pattern = rf"({'|'.join(function_names)})\((.*?)\)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None, None

    func_name = match.group(1)
    args_str = match.group(2)

    # Split args while preserving quoted strings
    args = []
    for arg in re.findall(r"(?:'[^']*'|\"[^\"]*\"|None)", args_str):
        arg = arg.strip().strip('"').strip("'")
        if arg == "None":
            arg = None
        args.append(arg)

    return func_name, args

def parse_single_function_call(call_str):
    visitor = MyVisitor()
    visitor.visit(ast.parse(call_str))
    return visitor.function_name, visitor.args

def extract_comment(text):
    marker = "========================\n"
    idx = text.rfind(marker)
    if idx == -1:
        return ""
    return text[idx + len(marker):].strip()

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

import re
import ast

def parse_llm_output(text, function_list, function_args_map):
    delimiter = "========================\n"
    parts = text.split(delimiter)

    if len(parts) < 3:
        return None, None  # Incomplete output

    func_call_block = parts[1].strip()
    user_comment = parts[2].strip()

    # Match function name and arguments (positional or keyword)
    func_pattern = re.compile(r"(?:`)?(" + "|".join(re.escape(fn) for fn in function_list) + r")\((.*?)\)(?:`)?", re.DOTALL)
    match = func_pattern.search(func_call_block)

    if not match:
        return None, user_comment

    func_name = match.group(1)
    args_str = match.group(2)

    # Split and parse args
    try:
        parsed_args = ast.literal_eval(f"[{args_str}]")  # safer than eval
    except Exception:
        return None, user_comment

    arg_names = function_args_map.get(func_name)
    if not arg_names or len(arg_names) != len(parsed_args):
        return None, user_comment

    args = dict(zip(arg_names, parsed_args))
    return (func_name, args), user_comment




def response(request: gr.Request, message, history):
    print(request.session)
    
    access_token, username, mail = request.username.split('\n')
    res = messenger.send_message(message)
    
    
    for alternative in res:
        print(alternative)
        
    res = str(res)
    
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
    # print(res[0][0])
    # parsed_result, user_text = messenger.parse_results(res[0][1])
    
    print("[DEBUG] -----------------------")
    # print(parsed_result, user_text)
    
    # call_string = extract_function_call(res)  # <- raw string from LLM
    # if call_string:
    #     func_name, args = parse_single_function_call(call_string)
    #     if func_name in function_map:
    #         print(func_name, args)
    #         function_map[func_name](**args)
    
    function_list = ["add_meeting", "delete_meeting", "find_slots", "change_meeting"]
    function_args_map = {
        "add_meeting": ["date_begin", "date_end", "name", "description", "participants"],
        "delete_meeting": ["name"],
        "find_slots": ["date_begin", "date_end"],
        "change_meeting": ["name", "description", "date_begin", "date_end", "participants"]
    }
    func, args = extract_function_call(res, function_list)
    print(func, args)
    
    kwargs = dict(zip(function_args_map[func], args))
    nres = function_map[func](**kwargs)
    
    
    comment = extract_comment(res)
    
    # return 1
    
    # parsed_result = res[0][0]
    # user_text = res[0][1]
    # print(parsed_result)

    # for func_name, args in parsed_result:
    #     if func_name in function_map:
    #         print(func_name, args)
    #         function_map[func_name](**args)
    
    if func == "add_meeting":
        return "Встреча добавлена"
    if func == "delete_meeting":
        return "Встреча удалена"
    if func == "find_slots":
        return "Слоты найдены: " + nres
    if func == "change_meeting":
        return "Встреча изменена"
    
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