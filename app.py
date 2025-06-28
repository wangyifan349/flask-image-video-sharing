import os
from flask import Flask, jsonify, render_template, redirect, url_for, flash, request, send_from_directory, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, EqualTo, Length
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # 请替换为您的密钥
app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join('static', 'uploads', 'images')
app.config['UPLOAD_FOLDER_VIDEOS'] = os.path.join('static', 'uploads', 'videos')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EXTENSIONS_VIDEOS = {'mp4', 'avi', 'mov', 'mkv'}

# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER_IMAGES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_VIDEOS'], exist_ok=True)

# 简单内存“数据库”
users = {}  # username -> User对象
user_files = {}  # username -> {'images': [filename], 'videos': [filename]}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User 类，继承 UserMixin
class User(UserMixin):
    def __init__(self, username, password_hash):
        self.id = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

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
    L = [[0]*(n+1) for i in range(m+1)]
    for i in range(m):
        for j in range(n):
            if s1[i].lower() == s2[j].lower():
                L[i+1][j+1] = L[i][j]+1
            else:
                L[i+1][j+1] = max(L[i+1][j], L[i][j+1])
    return L[m][n]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        if username in users:
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))
        password_hash = generate_password_hash(form.password.data)
        new_user = User(username, password_hash)
        users[username] = new_user
        user_files[username] = {'images': [], 'videos': []}
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        user = users.get(username)
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('登录成功', 'success')
            return redirect(url_for('profile', username=user.id))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已登出', 'info')
    return redirect(url_for('index'))

@app.route('/profile/<username>', methods=['GET', 'POST'])
@login_required
def profile(username):
    if username not in users:
        abort(404)
    is_owner = (username == current_user.id)
    form = UploadForm()
    if form.validate_on_submit() and is_owner:
        file = request.files.get('file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            # 判断文件类型
            ext = filename.rsplit('.',1)[1].lower()
            if allowed_file(filename, 'image'):
                save_path = app.config['UPLOAD_FOLDER_IMAGES']
                filetype = 'images'
            elif allowed_file(filename, 'video'):
                save_path = app.config['UPLOAD_FOLDER_VIDEOS']
                filetype = 'videos'
            else:
                flash('不支持的文件格式', 'danger')
                return redirect(url_for('profile', username=username))

            # 生成唯一文件名防止冲突
            unique_filename = f"{uuid4().hex}_{filename}"
            file.save(os.path.join(save_path, unique_filename))
            user_files[username][filetype].append(unique_filename)
            flash('上传成功', 'success')
            return redirect(url_for('profile', username=username))
        else:
            flash('请选择文件', 'warning')
    images = user_files[username]['images']
    videos = user_files[username]['videos']
    return render_template('profile.html', username=username, images=images, videos=videos, form=form, is_owner=is_owner)

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
    user_file_list = user_files.get(current_user.id)
    if not user_file_list or filename not in user_file_list[filetype]:
        flash('无权限或文件不存在', 'danger')
        return redirect(url_for('profile', username=current_user.id))
    folder = app.config['UPLOAD_FOLDER_IMAGES'] if filetype=='images' else app.config['UPLOAD_FOLDER_VIDEOS']
    file_path = os.path.join(folder, filename)
    try:
        os.remove(file_path)
    except Exception as e:
        print('删除文件错误:', e)
    user_file_list[filetype].remove(filename)
    flash('文件已删除', 'success')
    return redirect(url_for('profile', username=current_user.id))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    results = []
    if form.validate_on_submit():
        keyword = form.keyword.data.lower()
        # 使用LCS算法计算所有用户名与搜索关键字的匹配度
        matches = []
        for username in users.keys():
            score = lcs_length(keyword, username)
            if score > 0:
                matches.append((username, score))
        # 按匹配度降序排序
        matches.sort(key=lambda x: x[1], reverse=True)
        results = [username for username, score in matches]
    return render_template('search.html', form=form, results=results)

# 新增的三个接口

# 1. API接口：搜索用户
@app.route('/api/search_user')
def api_search_user():
    keyword = request.args.get('keyword', '').lower()
    if not keyword:
        return jsonify({'error': 'Keyword is required.'}), 400
    matches = []
    for username in users.keys():
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
    if username not in users:
        return jsonify({'error': 'User not found.'}), 404
    images = user_files[username]['images']
    videos = user_files[username]['videos']
    return jsonify({'username': username, 'images': images, 'videos': videos})

# 3. API接口：下载用户的指定文件
@app.route('/api/download_file/<username>/<filetype>/<filename>')
def api_download_file(username, filetype, filename):
    if username not in users:
        return jsonify({'error': 'User not found.'}), 404
    if filetype not in ('images', 'videos'):
        return jsonify({'error': 'Invalid file type.'}), 400
    if filename not in user_files[username][filetype]:
        return jsonify({'error': 'File not found.'}), 404
    folder = app.config['UPLOAD_FOLDER_IMAGES'] if filetype == 'images' else app.config['UPLOAD_FOLDER_VIDEOS']
    return send_from_directory(folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
