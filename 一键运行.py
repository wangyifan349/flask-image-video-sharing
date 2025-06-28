import os
import sqlite3
from flask import Flask, jsonify, render_template_string, redirect, url_for, flash, request, send_from_directory, abort, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, EqualTo, Length
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # 请替换为您的密钥
app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join(app.root_path, 'static', 'uploads', 'images')
app.config['UPLOAD_FOLDER_VIDEOS'] = os.path.join(app.root_path, 'static', 'uploads', 'videos')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['DATABASE'] = os.path.join(app.root_path, 'database.db')  # 数据库文件路径

# 启用 CSRF 保护
csrf = CSRFProtect(app)

# 允许的文件扩展名
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EXTENSIONS_VIDEOS = {'mp4', 'avi', 'mov', 'mkv'}

# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER_IMAGES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_VIDEOS'], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

############### 数据库部分 ###############

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row  # 使查询结果支持字典访问
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(schema_sql)
    db.commit()

# 数据库表结构（SQL 脚本）
schema_sql = """
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- 图片文件表
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    filename TEXT NOT NULL,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- 视频文件表
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    filename TEXT NOT NULL,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);
"""

# 在应用启动时检查数据库是否存在，如不存在则初始化
if not os.path.exists(app.config['DATABASE']):
    init_db()

#########################################

# User 类，继承 UserMixin
class User(UserMixin):
    def __init__(self, id, password_hash):
        self.id = id
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (user_id,)).fetchone()
        if user:
            return User(user['username'], user['password'])
        return None

    @staticmethod
    def create(username, password_hash):
        db = get_db()
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
        db.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# 表单定义

class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=25)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class UploadForm(FlaskForm):
    file = FileField('选择文件', validators=[DataRequired()])
    submit = SubmitField('上传')

class SearchForm(FlaskForm):
    keyword = StringField('搜索用户名', validators=[DataRequired()])
    submit = SubmitField('搜索')

# 检查允许的扩展名
def allowed_file(filename, type='image'):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if type == 'image':
        return ext in ALLOWED_EXTENSIONS_IMAGES
    else:
        return ext in ALLOWED_EXTENSIONS_VIDEOS

# LCS算法实现
def lcs_length(s1, s2):
    m = len(s1)
    n = len(s2)
    L = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m):
        for j in range(n):
            if s1[i].lower() == s2[j].lower():
                L[i+1][j+1] = L[i][j]+1
            else:
                L[i+1][j+1] = max(L[i+1][j], L[i][j+1])
    return L[m][n]

@app.route('/')
def index():
    return render_template_string(index_html)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))
        password_hash = generate_password_hash(form.password.data)
        User.create(username, password_hash)
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template_string(register_html, form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        user = User.get(username)
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('登录成功', 'success')
            return redirect(url_for('profile', username=user.id))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template_string(login_html, form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已登出', 'info')
    return redirect(url_for('index'))

@app.route('/profile/<username>', methods=['GET', 'POST'])
@login_required
def profile(username):
    user = User.get(username)
    if not user:
        abort(404)
    is_owner = (username == current_user.id)
    form = UploadForm()
    if form.validate_on_submit() and is_owner:
        file = request.files.get('file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            # 判断文件类型
            if allowed_file(filename, 'image'):
                save_path = app.config['UPLOAD_FOLDER_IMAGES']
                filetype = 'images'
                file_kind = 'image'
            elif allowed_file(filename, 'video'):
                save_path = app.config['UPLOAD_FOLDER_VIDEOS']
                filetype = 'videos'
                file_kind = 'video'
            else:
                flash('不支持的文件格式', 'danger')
                return redirect(url_for('profile', username=username))

            # 生成唯一文件名防止冲突
            unique_filename = f"{uuid4().hex}_{filename}"
            full_path = os.path.join(save_path, unique_filename)
            file.save(full_path)

            # 将文件信息存入数据库
            db = get_db()
            db.execute(f'INSERT INTO {filetype} (username, filename) VALUES (?, ?)', (username, unique_filename))
            db.commit()
            flash('上传成功', 'success')
            return redirect(url_for('profile', username=username))
        else:
            flash('请选择文件', 'warning')
    images, videos = get_user_files(username)
    return render_template_string(profile_html, username=username, images=images, videos=videos, form=form, is_owner=is_owner)

def get_user_files(username):
    db = get_db()
    images = db.execute('SELECT filename FROM images WHERE username = ?', (username,)).fetchall()
    videos = db.execute('SELECT filename FROM videos WHERE username = ?', (username,)).fetchall()
    images = [i['filename'] for i in images]
    videos = [v['filename'] for v in videos]
    return images, videos

@app.route('/uploads/<filetype>/<filename>')
def uploaded_file(filetype, filename):
    if filetype not in ('images', 'videos'):
        abort(404)
    folder = app.config['UPLOAD_FOLDER_IMAGES'] if filetype=='images' else app.config['UPLOAD_FOLDER_VIDEOS']
    return send_from_directory(folder, filename)

@app.route('/delete/<filetype>/<filename>', methods=['POST'])
@login_required
def delete_file(filetype, filename):
    if filetype not in ('images', 'videos'):
        abort(404)
    db = get_db()
    # 检查文件是否属于当前用户
    file = db.execute(f'SELECT * FROM {filetype} WHERE username = ? AND filename = ?', (current_user.id, filename)).fetchone()
    if not file:
        flash('无权限或文件不存在', 'danger')
        return redirect(url_for('profile', username=current_user.id))
    folder = app.config['UPLOAD_FOLDER_IMAGES'] if filetype=='images' else app.config['UPLOAD_FOLDER_VIDEOS']
    file_path = os.path.join(folder, filename)
    try:
        os.remove(file_path)
    except Exception as e:
        print('删除文件错误:', e)
    # 从数据库中删除记录
    db.execute(f'DELETE FROM {filetype} WHERE username = ? AND filename = ?', (current_user.id, filename))
    db.commit()
    flash('文件已删除', 'success')
    return redirect(url_for('profile', username=current_user.id))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    results = None
    if form.validate_on_submit():
        keyword = form.keyword.data.lower()
        # 从数据库中获取所有用户名
        db = get_db()
        users_list = db.execute('SELECT username FROM users').fetchall()
        users_list = [u['username'] for u in users_list]
        # 使用LCS算法计算所有用户名与搜索关键字的匹配度
        matches = []
        for username in users_list:
            score = lcs_length(keyword, username)
            if score > 0:
                matches.append((username, score))
        # 按匹配度降序排序
        matches.sort(key=lambda x: x[1], reverse=True)
        results = [username for username, score in matches]
    return render_template_string(search_html, form=form, results=results)

# 新增的三个接口

# 1. API接口：搜索用户
@app.route('/api/search_user')
def api_search_user():
    keyword = request.args.get('keyword', '').lower()
    if not keyword:
        return jsonify({'error': 'Keyword is required.'}), 400
    db = get_db()
    users_list = db.execute('SELECT username FROM users').fetchall()
    users_list = [u['username'] for u in users_list]
    matches = []
    for username in users_list:
        score = lcs_length(keyword, username)
        if score > 0:
            matches.append((username, score))
    # 按匹配度降序排序
    matches.sort(key=lambda x: x[1], reverse=True)
    results = [username for username, score in matches]
    return jsonify({'results': results})

# 2. API接口：获取用户的所有文件信息
@app.route('/api/user_files/<username>')
def api_user_files(username):
    user = User.get(username)
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    images, videos = get_user_files(username)
    return jsonify({'username': username, 'images': images, 'videos': videos})

# 3. API接口：下载用户的指定文件
@app.route('/api/download_file/<username>/<filetype>/<filename>')
def api_download_file(username, filetype, filename):
    if filetype not in ('images', 'videos'):
        return jsonify({'error': 'Invalid file type.'}), 400
    db = get_db()
    # 检查文件是否存在
    file = db.execute(f'SELECT * FROM {filetype} WHERE username = ? AND filename = ?', (username, filename)).fetchone()
    if not file:
        return jsonify({'error': 'File not found.'}), 404
    folder = app.config['UPLOAD_FOLDER_IMAGES'] if filetype == 'images' else app.config['UPLOAD_FOLDER_VIDEOS']
    return send_from_directory(folder, filename)

if __name__ == '__main__':
    app.run(debug=True)

######### 以下是模板字符串 #########

base_html = """
{% macro render_base(title, content) %}
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <!-- 引入 Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
  body {
    background-color: #f8f9fa;
  }
  .media-thumb {
    max-width: 200px;
    max-height: 200px;
    object-fit: cover;
  }
  .media-container {
    margin-bottom: 20px;
    text-align: center;
  }
  video {
    max-width: 200px;
    max-height: 200px;
  }
  .navbar-brand {
    font-weight: bold;
  }
  .card {
    border: none;
  }
  .card-body {
    padding: 0.5rem;
  }
  .btn-close {
    float: right;
  }
  </style>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-3">
    <div class="container">
      <a class="navbar-brand" href="{{ url_for('index') }}">图片视频分享</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse justify-content-end" id="navbarNav">
        <ul class="navbar-nav">
        {% if current_user.is_authenticated %}
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('profile', username=current_user.id) }}">我的主页</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('search') }}">搜索用户</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('logout') }}">登出</a>
          </li>
        {% else %}
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('login') }}">登录</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('register') }}">注册</a>
          </li>
        {% endif %}
        </ul>
      </div>
    </div>
  </nav>

  <div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {{ content }}
  </div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
{% endmacro %}
"""

index_html = """
{% import 'base' as base %}
{% call base.render_base('首页', caller()) %}
  <div class="text-center">
    <h1 class="mt-5 mb-4">欢迎来到图片和视频分享平台</h1>
    {% if current_user.is_authenticated %}
      <p>你好，<strong>{{ current_user.id }}</strong>！</p>
      <a href="{{ url_for('profile', username=current_user.id) }}" class="btn btn-primary btn-lg mt-3">进入我的主页</a>
    {% else %}
      <p>分享你的精彩瞬间，发现更多有趣内容！</p>
      <a href="{{ url_for('login') }}" class="btn btn-primary btn-lg mt-3">登录</a>
      <a href="{{ url_for('register') }}" class="btn btn-outline-primary btn-lg mt-3 ms-2">注册</a>
    {% endif %}
  </div>
{% endcall %}
"""

register_html = """
{% import 'base' as base %}
{% call base.render_base('注册', caller()) %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <h2 class="mb-4 text-center">注册新账号</h2>
    <form method="POST" novalidate>
      {{ form.hidden_tag() }}
      <div class="mb-3">
        {{ form.username.label(class="form-label") }}
        {{ form.username(class="form-control", placeholder="请输入用户名") }}
        {% for error in form.username.errors %}
          <div class="text-danger">{{ error }}</div>
        {% endfor %}
      </div>
      <div class="mb-3">
        {{ form.password.label(class="form-label") }}
        {{ form.password(class="form-control", placeholder="请输入密码") }}
        {% for error in form.password.errors %}
          <div class="text-danger">{{ error }}</div>
        {% endfor %}
      </div>
      <div class="mb-3">
        {{ form.confirm.label(class="form-label") }}
        {{ form.confirm(class="form-control", placeholder="请再次输入密码") }}
        {% for error in form.confirm.errors %}
          <div class="text-danger">{{ error }}</div>
        {% endfor %}
      </div>
      <button type="submit" class="btn btn-primary w-100">{{ form.submit.label.text }}</button>
    </form>
  </div>
</div>
{% endcall %}
"""

login_html = """
{% import 'base' as base %}
{% call base.render_base('登录', caller()) %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <h2 class="mb-4 text-center">登录</h2>
    <form method="POST" novalidate>
      {{ form.hidden_tag() }}
      <div class="mb-3">
        {{ form.username.label(class="form-label") }}
        {{ form.username(class="form-control", placeholder="请输入用户名") }}
        {% for error in form.username.errors %}
          <div class="text-danger">{{ error }}</div>
        {% endfor %}
      </div>
      <div class="mb-3">
        {{ form.password.label(class="form-label") }}
        {{ form.password(class="form-control", placeholder="请输入密码") }}
        {% for error in form.password.errors %}
          <div class="text-danger">{{ error }}</div>
        {% endfor %}
      </div>
      <button type="submit" class="btn btn-primary w-100">{{ form.submit.label.text }}</button>
    </form>
  </div>
</div>
{% endcall %}
"""

profile_html = """
{% import 'base' as base %}
{% call base.render_base(username + '的主页', caller()) %}
<h2 class="mb-4">{{ username }} 的主页</h2>

{% if is_owner %}
<div class="card mb-4">
  <div class="card-body">
    <h4 class="card-title">上传新文件</h4>
    <form method="POST" enctype="multipart/form-data">
      {{ form.hidden_tag() }}
      <div class="input-group">
        {{ form.file(class="form-control") }}
        <button type="submit" class="btn btn-primary">{{ form.submit.label.text }}</button>
      </div>
      {% for error in form.file.errors %}
        <div class="text-danger mt-2">{{ error }}</div>
      {% endfor %}
    </form>
  </div>
</div>
{% endif %}

<h4>图片</h4>
{% if images %}
<div class="row">
  {% for image in images %}
  <div class="col-md-3 media-container">
    <img src="{{ url_for('uploaded_file', filetype='images', filename=image) }}" alt="image" class="media-thumb rounded border">
    {% if is_owner %}
    <form method="POST" action="{{ url_for('delete_file', filetype='images', filename=image) }}" class="mt-2">
      {{ form.csrf_token }}
      <button type="submit" class="btn btn-sm btn-outline-danger">删除</button>
    </form>
    {% endif %}
  </div>
  {% endfor %}
</div>
{% else %}
<p>没有上传的图片。</p>
{% endif %}

<h4 class="mt-5">视频</h4>
{% if videos %}
<div class="row">
  {% for video in videos %}
  <div class="col-md-3 media-container">
    <video controls class="media-thumb rounded border">
      <source src="{{ url_for('uploaded_file', filetype='videos', filename=video) }}">
      您的浏览器不支持视频标签。
    </video>
    {% if is_owner %}
    <form method="POST" action="{{ url_for('delete_file', filetype='videos', filename=video) }}" class="mt-2">
      {{ form.csrf_token }}
      <button type="submit" class="btn btn-sm btn-outline-danger">删除</button>
    </form>
    {% endif %}
  </div>
  {% endfor %}
</div>
{% else %}
<p>没有上传的视频。</p>
{% endif %}

{% endcall %}
"""

search_html = """
{% import 'base' as base %}
{% call base.render_base('搜索用户', caller()) %}
<h2 class="mb-4">搜索用户</h2>
<form method="POST" class="mb-4" novalidate>
  {{ form.hidden_tag() }}
  <div class="input-group">
    {{ form.keyword(class="form-control", placeholder="输入用户名关键字") }}
    <button class="btn btn-primary" type="submit">{{ form.submit.label.text }}</button>
  </div>
  {% for error in form.keyword.errors %}
    <div class="text-danger mt-2">{{ error }}</div>
  {% endfor %}
</form>

{% if results is not none %}
  {% if results %}
  <ul class="list-group">
  {% for user in results %}
    <li class="list-group-item d-flex justify-content-between align-items-center">
      <a href="{{ url_for('profile', username=user) }}">{{ user }}</a>
    </li>
  {% endfor %}
  </ul>
  {% else %}
  <p>未找到匹配的用户。</p>
  {% endif %}
{% endif %}
{% endcall %}
"""

# 将 base_html 添加到模板环境中
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.jinja_env.globals['base'] = app.jinja_env.from_string(base_html)
