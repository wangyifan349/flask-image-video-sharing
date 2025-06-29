# app.py

from flask import Flask, request, redirect, url_for, render_template_string, send_file, session, jsonify, abort
import os
import shutil
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import random
import string
import base64

app = Flask(__name__)

# --------------------------
# 自定义 Flask 配置参数
# --------------------------
app.secret_key = 'your_secret_key_here'  # Session 加密密钥，请替换为安全密钥
app.config['UPLOAD_FOLDER'] = 'uploads'  # 上传文件存储目录，非 static，不自动提供静态文件访问
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大上传大小16MB

# 确保 uploads 目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# SQLite 数据库路径
DATABASE = 'users.db'

# --------------------------
# 初始化数据库
# --------------------------
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

# --------------------------
# 工具函数：路径安全检测
# --------------------------
def is_sub_path(path, directory):
    abs_directory = os.path.abspath(directory)
    abs_path = os.path.abspath(path)
    return abs_path.startswith(abs_directory)

# --------------------------
# 生成图片验证码
# --------------------------
def generate_captcha():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    width, height = 120, 40
    image = Image.new('RGB', (width, height), 'white')
    font = ImageFont.load_default()
    draw = ImageDraw.Draw(image)
    for i in range(5):
        angle = random.uniform(-25, 25)
        char = code[i]
        char_img = Image.new('RGBA', (24, 30), (255,255,255,0))
        d = ImageDraw.Draw(char_img)
        d.text((0,0), char, font=font, fill='black')
        char_img = char_img.rotate(angle, resample=Image.BILINEAR, expand=1)
        image.paste(char_img, (10 + i*20, 5), char_img)
    for _ in range(7):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill='gray', width=1)
    buffer = BytesIO()
    image.save(buffer, 'PNG')
    buffer.seek(0)
    img_b64 = base64.b64encode(buffer.read()).decode()
    return code, img_b64

# 获取验证码图片
@app.route('/captcha')
def captcha():
    code, img = generate_captcha()
    session['captcha_code'] = code.lower()
    return f"data:image/png;base64,{img}"

# --------------------------
# 登录注册共用页面
# --------------------------
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    error = ''
    captcha_image_url = url_for('captcha')
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha = request.form.get('captcha', '').strip().lower()
        action = request.form.get('action', '').strip()

        if not username or not password or not captcha:
            error = '请填写所有字段。'
        elif captcha != session.get('captcha_code', ''):
            error = '验证码错误。'
        else:
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                if action == 'register':
                    hashed = generate_password_hash(password)
                    try:
                        c.execute('INSERT INTO users (username,password) VALUES (?,?)', (username, hashed))
                        conn.commit()
                        user_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)
                        if not os.path.exists(user_dir):
                            os.makedirs(user_dir)
                        return redirect(url_for('auth'))
                    except sqlite3.IntegrityError:
                        error = '用户名已存在。'
                elif action == 'login':
                    c.execute('SELECT password FROM users WHERE username=?', (username,))
                    row = c.fetchone()
                    if row and check_password_hash(row[0], password):
                        session['username'] = username
                        return redirect(url_for('dir_listing'))
                    else:
                        error = '用户名或密码错误。'
                else:
                    error = '未知操作。'
    return render_template_string(auth_template, error=error, captcha_image=captcha_image_url)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth'))

# --------------------------
# 账户删除功能，彻底删除用户数据
# --------------------------
@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'username' not in session:
        return redirect(url_for('auth'))

    if request.method == 'POST':
        username = session['username']
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users WHERE username=?', (username,))
            conn.commit()

        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)

        session.clear()
        return redirect(url_for('auth'))
    else:
        return render_template_string(delete_account_template)

# --------------------------
# 主文件浏览及下载路由
# --------------------------
@app.route('/', defaults={'req_path': ''})
@app.route('/<path:req_path>')
def dir_listing(req_path):
    if 'username' not in session:
        return redirect(url_for('auth'))

    username = session['username']
    base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)
    abs_path = os.path.join(base_dir, req_path)

    if not is_sub_path(abs_path, base_dir):
        abort(403)
    if not os.path.exists(abs_path):
        abort(404)
    if os.path.isfile(abs_path):
        return send_file(abs_path, as_attachment=True, attachment_filename=os.path.basename(abs_path))

    files = []
    for f in sorted(os.listdir(abs_path)):
        fpath = os.path.join(req_path, f).replace('\\','/')
        fullpath = os.path.join(base_dir, fpath)
        files.append({
            'name': f,
            'path': fpath,
            'is_file': os.path.isfile(fullpath)
        })

    parent_path = '/'.join(req_path.split('/')[:-1])
    return render_template_string(index_template,
                                  files=files,
                                  current_path=req_path,
                                  parent_path=parent_path,
                                  username=username)

# --------------------------
# 文件或文件夹移动路由
# --------------------------
@app.route('/move', methods=['POST'])
def move_item():
    if 'username' not in session:
        abort(401)

    data = request.get_json()
    if not data:
        abort(400)

    username = session['username']
    base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)

    source = data.get('source', '')
    dest = data.get('destination', '')

    if not source or not dest:
        abort(400)

    src_path = os.path.join(base_dir, source)
    dst_path = os.path.join(base_dir, dest, os.path.basename(source))

    if not (is_sub_path(src_path, base_dir) and is_sub_path(dst_path, base_dir)):
        abort(403)

    if not os.path.exists(src_path):
        abort(404)
    if os.path.exists(dst_path):
        return '目标已存在', 400

    try:
        shutil.move(src_path, dst_path)
        return 'Success', 200
    except Exception as e:
        return str(e), 500

# --------------------------
# 删除文件/文件夹路由
# --------------------------
@app.route('/delete', methods=['POST'])
def delete_item():
    if 'username' not in session:
        abort(401)

    data = request.get_json()
    if not data:
        abort(400)

    username = session['username']
    base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)

    path = data.get('path', '')
    is_file = data.get('is_file', False)

    if not path:
        abort(400)

    abs_path = os.path.join(base_dir, path)
    if not is_sub_path(abs_path, base_dir):
        abort(403)

    if not os.path.exists(abs_path):
        abort(404)

    try:
        if is_file:
            os.remove(abs_path)
        else:
            shutil.rmtree(abs_path)
        return 'Success', 200
    except Exception as e:
        return str(e), 500

# --------------------------
# 重命名文件/文件夹路由
# --------------------------
@app.route('/rename', methods=['POST'])
def rename_item():
    if 'username' not in session:
        abort(401)

    data = request.get_json()
    if not data:
        abort(400)

    username = session['username']
    base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)

    path = data.get('path', '')
    new_name = secure_filename(data.get('new_name', ''))

    if not path or not new_name:
        abort(400)

    abs_path = os.path.join(base_dir, path)
    new_abs_path = os.path.join(os.path.dirname(abs_path), new_name)

    if not is_sub_path(abs_path, base_dir) or not is_sub_path(new_abs_path, base_dir):
        abort(403)
    if not os.path.exists(abs_path):
        abort(404)
    if os.path.exists(new_abs_path):
        return '目标文件已存在', 400

    try:
        os.rename(abs_path, new_abs_path)
        return 'Success', 200
    except Exception as e:
        return str(e), 500

# --------------------------
# 文件上传路由
# --------------------------
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        abort(401)

    file = request.files.get('file')
    if not file:
        abort(400)

    username = session['username']
    base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)

    path = request.form.get('path', '')

    upload_dir = os.path.join(base_dir, path)
    if not is_sub_path(upload_dir, base_dir):
        abort(403)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    filename = secure_filename(file.filename)
    save_path = os.path.join(upload_dir, filename)
    file.save(save_path)

    return 'Success', 200

# --------------------------
# 创建文件夹路由
# --------------------------
@app.route('/create_folder', methods=['POST'])
def create_folder():
    if 'username' not in session:
        abort(401)

    data = request.get_json()
    if not data:
        abort(400)

    username = session['username']
    base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)

    path = data.get('path', '')
    folder_name = secure_filename(data.get('folder_name', ''))
    if not folder_name:
        abort(400)

    folder_path = os.path.join(base_dir, path, folder_name)
    if not is_sub_path(folder_path, base_dir):
        abort(403)

    try:
        os.makedirs(folder_path)
        return 'Success', 200
    except Exception as e:
        return str(e), 500

# --------------------------
# HTML模板部分
# --------------------------

auth_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>登录/注册</title>
<style>
    body { font-family: Arial, sans-serif; background:#f5f5f5; text-align:center; }
    .container { margin-top:100px; }
    input,button { padding:10px; margin:5px; width:220px; font-size:16px; }
    button { width: 110px; }
    .error { color:red; }
    #captcha-img { cursor:pointer; margin:10px 0; }
</style>
<script>
function refreshCaptcha() {
    document.getElementById("captcha-img").src = "/captcha?" + Math.random();
}
</script>
</head>
<body>
<div class="container">
<h1>登录/注册</h1>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post">
<input type="text" name="username" placeholder="用户名" autocomplete="username" required><br>
<input type="password" name="password" placeholder="密码" autocomplete="current-password" required><br>
<input type="text" name="captcha" placeholder="验证码" autocomplete="off" required><br>
<img id="captcha-img" src="{{ captcha_image }}" alt="验证码" title="点击刷新验证码" onclick="refreshCaptcha()"><br>
<button type="submit" name="action" value="login">登录</button>
<button type="submit" name="action" value="register">注册</button>
</form>
</div>
</body>
</html>
'''

delete_account_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>删除账户</title>
<style>
    body { font-family: Arial, sans-serif; background:#f5f5f5; text-align:center; }
    .container { margin-top:100px; }
    button { padding:10px 20px; margin:5px; }
</style>
</head>
<body>
<div class="container">
<h1>删除账户</h1>
<p>您确定要永久删除您的账户吗？此操作无法撤销。</p>
<form method="post">
<button type="submit">确认删除</button>
<a href="{{ url_for('dir_listing') }}"><button type="button">取消</button></a>
</form>
</div>
</body>
</html>
'''

index_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>文件管理器 - {{ username }}</title>
<style>
    body { font-family: Arial, sans-serif; background:#fff; }
    #header { background:#333; color:#fff; padding:10px;}
    #header a { color:#fff; margin-right:10px; text-decoration:none;}
    #file-list { list-style:none; padding:0; margin:0;}
    .file-item { padding:5px; cursor:pointer; user-select:none; }
    .file-item:hover { background:#eee; }
    #context-menu, #root-menu {
        position:absolute; background:#fff; border:1px solid #ccc;
        display:none; z-index:1000; box-shadow:0 2px 5px rgba(0,0,0,0.3);
    }
    #context-menu ul, #root-menu ul { list-style:none; margin:0; padding:0; }
    #context-menu li, #root-menu li { padding:8px 12px; cursor:pointer;}
    #context-menu li:hover, #root-menu li:hover { background:#ddd;}
    #file-manager { padding:20px;}
    a { text-decoration:none; color:#000;}
    a:hover { text-decoration:underline; }
</style>
</head>
<body>
<div id="header">
    <span>当前用户：{{ username }}</span>
    <a href="{{ url_for('logout') }}">退出登录</a>
    <a href="{{ url_for('delete_account') }}">删除账户</a>
</div>
<div id="file-manager">
<ul id="file-list" oncontextmenu="onBlankContextMenu(event)">
{% if current_path %}
<li><a href="{{ url_for('dir_listing', req_path=parent_path) }}">⬅ 返回上一级</a></li>
{% endif %}
{% for file in files %}
<li class="file-item" data-file-path="{{ file.path }}" data-is-file="{{ 'true' if file.is_file else 'false' }}"
 draggable="true" ondragstart="onDragStart(event)" oncontextmenu="onFileContextMenu(event)">
{% if file.is_file %}
📄 <span style="color:blue; text-decoration:underline; cursor:pointer;" 
      onclick="downloadFile('{{ url_for('dir_listing', req_path=file.path) }}', '{{ file.name }}')">{{ file.name }}</span>
{% else %}
📁 <a href="{{ url_for('dir_listing', req_path=file.path) }}">{{ file.name }}</a>
{% endif %}
</li>
{% endfor %}
</ul>
</div>

<div id="context-menu">
<ul>
<li onclick="renameItem()">重命名</li>
<li onclick="deleteItem()">删除</li>
</ul>
</div>

<div id="root-menu">
<ul>
<li onclick="uploadFile()">上传文件</li>
<li onclick="createFolder()">创建文件夹</li>
</ul>
</div>

<script>
let draggedItem = null;
let currentItemPath = '';
let isFile = false;
const currentPath = "{{ current_path }}";
const parentPath = "{{ parent_path }}";

let userPassword = null;

async function askPassword(){
    if(!userPassword){
        userPassword = prompt('请输入用于加密/解密的密码：');
        if(!userPassword){
            alert("密码不能为空，刷新页面后可重新输入。");
        }
    }
}
askPassword();

function onDragStart(event){
    draggedItem=event.target;
    event.dataTransfer.setData("text/plain", event.target.dataset.filePath);
}

document.addEventListener("dragover", e=>e.preventDefault());

document.addEventListener("drop", e=>{
    e.preventDefault();
    const sourcePath = e.dataTransfer.getData("text/plain");
    const targetPath = currentPath;
    fetch("/move",
        {method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({"source":sourcePath,"destination":targetPath})
    }).then(r=>r.ok?location.reload():r.text().then(t=>alert("移动失败："+t)));
});

function onFileContextMenu(e){
    e.preventDefault();
    currentItemPath = e.target.dataset.filePath;
    isFile = e.target.dataset.isFile==="true";
    const menu = document.getElementById("context-menu");
    menu.style.top = e.pageY+"px";
    menu.style.left = e.pageX+"px";
    menu.style.display = "block";
}

function onBlankContextMenu(e){
    if(!e.target.classList.contains('file-item')){
        e.preventDefault();
        const menu = document.getElementById("root-menu");
        menu.style.top = e.pageY+"px";
        menu.style.left = e.pageX+"px";
        menu.style.display = "block";
    }
}

document.addEventListener("click", ()=>{
    document.getElementById("context-menu").style.display="none";
    document.getElementById("root-menu").style.display="none";
});

function deleteItem(){
    if(confirm("确定要删除吗？")){
        fetch("/delete", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({"path":currentItemPath, "is_file":isFile})
        }).then(r=>r.ok?location.reload():r.text().then(t=>alert("删除失败："+t)));
    }
}

function renameItem(){
    const newName = prompt("输入新的名称", currentItemPath.split("/").pop());
    if(newName){
        fetch("/rename", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({"path":currentItemPath, "new_name":newName})
        }).then(r=>r.ok?location.reload():r.text().then(t=>alert("重命名失败："+t)));
    }
}

async function uploadFile(){
    if(!userPassword){await askPassword(); if(!userPassword) return;}
    const input=document.createElement("input");
    input.type="file";
    input.onchange=async function(){
        const file=input.files[0];
        if(!file) return;

        const arrayBuffer=await file.arrayBuffer();

        // Web Crypto AES-GCM加密部分
        const enc = new TextEncoder();
        const pwKey = await crypto.subtle.importKey('raw', enc.encode(userPassword), 'PBKDF2', false, ['deriveKey']);
        const salt = crypto.getRandomValues(new Uint8Array(16));
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const key = await crypto.subtle.deriveKey(
            {
                name:'PBKDF2', salt, iterations:100000, hash:'SHA-256'
            }, pwKey,
            {name:'AES-GCM', length:256},
            false,
            ['encrypt']
        );
        const encrypted = await crypto.subtle.encrypt({name:'AES-GCM', iv}, key, arrayBuffer);

        // 拼接salt+iv+加密体
        const totalLength = salt.byteLength + iv.byteLength + encrypted.byteLength;
        const combined = new Uint8Array(totalLength);
        combined.set(salt, 0);
        combined.set(iv, salt.byteLength);
        combined.set(new Uint8Array(encrypted), salt.byteLength + iv.byteLength);

        const blob = new Blob([combined], {type:'application/octet-stream'});

        const formData = new FormData();
        formData.append("file", blob, file.name);
        formData.append("path", currentPath);

        const res = await fetch("/upload", {method:"POST", body:formData});
        if(res.ok) location.reload();
        else {
            const t=await res.text();
            alert("上传失败：" + t);
        }
    };
    input.click();
}

async function downloadFile(fileUrl, fileName){
    if(!userPassword){await askPassword(); if(!userPassword) return;}
    const res = await fetch(fileUrl);
    if(!res.ok){alert("下载失败"); return;}
    const arrayBuffer = await res.arrayBuffer();

    if(arrayBuffer.byteLength < 28){
        alert("文件格式错误");
        return;
    }
    const salt = arrayBuffer.slice(0,16);
    const iv = arrayBuffer.slice(16,28);
    const data = arrayBuffer.slice(28);

    const enc = new TextEncoder();
    const pwKey = await crypto.subtle.importKey('raw', enc.encode(userPassword), 'PBKDF2', false, ['deriveKey']);
    const key = await crypto.subtle.deriveKey(
        {name:'PBKDF2', salt:new Uint8Array(salt), iterations:100000, hash:'SHA-256'},
        pwKey,
        {name:'AES-GCM', length:256},
        false,
        ['decrypt']
    );
    let decrypted;
    try {
        decrypted = await crypto.subtle.decrypt({name:'AES-GCM', iv:new Uint8Array(iv)}, key, data);
    } catch(e) {
        alert("解密失败，密码错误或文件损坏");
        return;
    }
    const blob = new Blob([decrypted]);
    const url = URL.createObjectURL(blob);
    let a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

function createFolder() {
    const folderName = prompt("请输入文件夹名称");
    if (!folderName) return;
    fetch('/create_folder', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({path: currentPath, folder_name: folderName})
    }).then(res => {
        if(res.ok) location.reload();
        else res.text().then(t => alert("创建文件夹失败："+t));
    });
}
</script>
</body>
</html>
'''

# --------------------------
# 运行
# --------------------------
if __name__ == '__main__':
    app.run(debug=True)
