from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os

app = Flask(__name__)

# 根目录（文件管理根路径），当前目录下的 'files' 文件夹
ROOT_DIR = os.path.abspath('files')

# 保证文件夹存在
os.makedirs(ROOT_DIR, exist_ok=True)

# 安全路径，避免目录穿越漏洞
def safe_path(req_path):
    # 使用绝对路径并限制在ROOT_DIR内
    full_path = os.path.abspath(os.path.join(ROOT_DIR, req_path))
    if not full_path.startswith(ROOT_DIR):
        raise Exception('非法路径访问')
    return full_path

# 主页面 HTML，集成Bootstrap 5，美化，黑底红字，字体大，开放布局，没有边框
# 备注：Bootstrap 5 通过 CDN 载入，使用类 container-fluid，p-4 边距，黑底红字主题
HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>文件管理器（黑底红字版）</title>
  <!-- Bootstrap 5 CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #000000;  /* 黑色背景 */
      color: #ff4444;             /* 红色字体 */
      font-size: 1.25rem;         /* 字体稍大 */
      min-height: 100vh;
      padding-top: 1rem;
      padding-bottom: 1rem;
      user-select: none;
    }
    /* 去除默认ul样式，保持左内边距 */
    ul {
      list-style: none;
      padding-left: 1.2rem;
      margin-bottom: 0;
    }
    /* li 鼠标悬停提示可点击 */
    li {
      cursor: pointer;
      padding: 0.1rem 0;
      user-select:none;
    }
    li.folder::before {
      content: "📁 "; /* 文件夹图标 */
    }
    li.file::before {
      content: "📄 "; /* 文件图标 */
    }

    #contextMenu {
      position: absolute;
      background: #000000;
      border: none;
      padding: 0.2rem 0;
      display: none;
      z-index: 1000;
      box-shadow: none;
      width: 160px;
      font-weight: 600;
      color: #ff4444;
      font-size: 1rem;
    }
    #contextMenu div {
      padding: 0.35rem 1rem;
      cursor: pointer;
      transition: background-color 0.15s ease-in-out;
    }
    #contextMenu div:hover {
      background-color: #330000;
    }

    #uploadFile {
      display: none;
    }

    #dropZone {
      border: none;
      padding: 1rem;
      margin-top: 0.75rem;
      text-align: center;
      color: #cc2222;
      background-color: #110000;
      font-size: 1.1rem;
      font-weight: 600;
      user-select:none;
      border-radius: 0.3rem;
      transition: background-color 0.3s ease;
    }
    #dropZone.dragover {
      background-color: #440000;
      color: #ff4444;
    }

    .btn-custom {
      background: none;
      border: none;
      color: #ff4444;
      font-weight: 700;
      font-size: 1.1rem;
      padding: 0.15rem 0.6rem;
      transition: color 0.2s ease;
    }
    .btn-custom:hover {
      color: #ff7777;
      text-decoration: underline;
      background: none;
      box-shadow: none;
    }

    /* 显示路径文字大小加粗 */
    #path {
      font-size: 1.2rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      user-select: text;
    }

    /* 上级目录 li 独立样式 */
    li.up {
      color: #ff6666;
      font-weight: 700;
    }
    li.up:hover {
      color: #ff9999;
    }
  </style>
</head>
<body>
<div class="container-fluid px-4">

  <h1 class="mb-3">📂 文件管理器（黑底红字版）</h1>

  <div class="mb-3" style="user-select:none;">
    <!-- 操作菜单按钮 -->
    <button class="btn-custom" onclick="showRootMenu()">菜单操作</button>
    <!-- 隐藏文件上传输入框 -->
    <input type="file" id="uploadFile" multiple>
  </div>

  <!-- 当前路径显示 -->
  <div id="path" class="mb-2" title="当前文件夹路径"></div>

  <!-- 拖拽上传区域 -->
  <div id="dropZone" class="mb-3" title="将文件拖拽到这里上传">⬇ 拖拽文件到这里上传 ⬇</div>

  <!-- 文件列表显示 -->
  <div id="fileList" class="fs-5" style="word-break:break-word;"></div>

  <!-- 右键菜单容器 -->
  <div id="contextMenu"></div>
</div>

<!-- Bootstrap 5 JS Bundle (Popper + Bootstrap) -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
let currentPath = '';
let contextTarget = null;
let contextTargetName = '';
let contextTargetType = '';

const contextMenu = document.getElementById('contextMenu');
const dropZone = document.getElementById('dropZone');
const uploadInput = document.getElementById('uploadFile');

// 列出目录文件
function listFiles(path='') {
    fetch('/list?path=' + encodeURIComponent(path))
    .then(res => res.json())
    .then(data => {
        currentPath = path;
        document.getElementById('path').textContent = '当前路径：/' + path;
        let html = '<ul>';
        if(path){
          const upPath = path.split('/').slice(0,-1).join('/');
          html += `<li class="up" onclick="listFiles('${upPath}')">⬆ 上级目录</li>`;
        }
        data.forEach(item => {
            html += `<li class="${item.type}" oncontextmenu="showMenu(event, '${item.name}', '${item.type}')" ondblclick="openItem('${item.name}', '${item.type}')">${item.name}</li>`;
        });
        html += '</ul>';
        document.getElementById('fileList').innerHTML = html;
    }).catch(() => {
        alert('无法获取文件列表，请稍后重试');
    });
}

// 打开文件或文件夹
function openItem(name, type) {
    if(type === 'folder') {
        listFiles(currentPath ? currentPath + '/' + name : name);
    } else {
        window.open('/download?path=' + encodeURIComponent(currentPath ? currentPath + '/' + name : name), '_blank');
    }
}

// 根菜单，显示新建文件夹和上传按钮
function showRootMenu() {
    contextTarget = null;
    contextTargetName = null;
    contextTargetType = null;
    showCustomMenu([
        {text: '新建文件夹', action: createFolder},
        {text: '上传文件', action: () => uploadInput.click()}
    ], window.innerWidth/2, window.innerHeight/2);
}

// 右键菜单事件，显示菜单
function showMenu(event, name, type) {
    event.preventDefault();
    contextTarget = event.target;
    contextTargetName = name;
    contextTargetType = type;

    const menuItems = [];

    if(type === 'folder') {
        menuItems.push({text: '打开', action: () => openItem(name, type)});
        menuItems.push({text: '重命名', action: renameItem});
        menuItems.push({text: '删除', action: deleteItem});
        menuItems.push({text: '上传文件', action: () => {uploadInput.click(); closeMenu();}});
        menuItems.push({text: '新建文件夹', action: createFolder});
    } else {
        menuItems.push({text: '下载', action: () => openItem(name, type)});
        menuItems.push({text: '重命名', action: renameItem});
        menuItems.push({text: '删除', action: deleteItem});
    }
    showCustomMenu(menuItems, event.pageX, event.pageY);
}

// 显示自定义菜单
function showCustomMenu(items, x, y) {
    contextMenu.innerHTML = '';
    for(const item of items){
        const div = document.createElement('div');
        div.textContent = item.text;
        div.onclick = () => {item.action(); closeMenu();}
        contextMenu.appendChild(div);
    }
    contextMenu.style.display = 'block';

    // 防止菜单溢出屏幕
    let maxX = window.innerWidth - contextMenu.offsetWidth;
    let maxY = window.innerHeight - contextMenu.offsetHeight;
    if(x > maxX) x = maxX;
    if(y > maxY) y = maxY;
    contextMenu.style.left = x + 'px';
    contextMenu.style.top = y + 'px';
}

// 关闭菜单
function closeMenu() {
    contextMenu.style.display = 'none';
}

// 点击页面关闭菜单
window.onclick = () => closeMenu();
window.oncontextmenu = () => closeMenu();

// 删除文件或文件夹
function deleteItem() {
    if(!contextTargetName) return;
    if(confirm('确定删除 "' + contextTargetName + '" ？')) {
        let fullPath = currentPath ? currentPath + '/' + contextTargetName : contextTargetName;
        fetch('/delete', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({path: fullPath})
        })
        .then(res=>res.json())
        .then(data => {
            alert(data.message);
            listFiles(currentPath);
        }).catch(() => alert('删除失败，网络异常'));
    }
}

// 重命名文件或文件夹
function renameItem() {
    if(!contextTargetName) return;
    let newName = prompt('输入 "' + contextTargetName + '" 的新名称：', contextTargetName);
    if(newName && newName.trim() && newName !== contextTargetName) {
        if(/[\\/]/.test(newName)) {
            alert('名称不能包含 / 或 \\ ');
            return;
        }
        let fullPath = currentPath ? currentPath + '/' + contextTargetName : contextTargetName;
        fetch('/rename', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({path: fullPath, new_name: newName.trim()})
        })
        .then(res=>res.json())
        .then(data => {
            alert(data.message);
            listFiles(currentPath);
        }).catch(() => alert('重命名失败，网络异常'));
    }
}

// 新建文件夹
function createFolder() {
    let folderName = prompt('请输入文件夹名称');
    if(folderName){
        folderName = folderName.trim();
        if(!folderName) return;
        if(/[\\/]/.test(folderName)) {
           alert('文件夹名称不能包含 / 或 \\ ');
           return;
        }
        fetch('/mkdir', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({path: currentPath, folder: folderName})
        })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            listFiles(currentPath);
        }).catch(() => alert('创建文件夹失败，网络异常'));
    }
}

// 文件上传input改变事件
uploadInput.onchange = () => {
    if(uploadInput.files.length > 0){
        let formData = new FormData();
        for(let f of uploadInput.files){
            formData.append('files', f);
        }
        formData.append('path', currentPath);
        fetch('/upload', {method: 'POST', body: formData})
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            listFiles(currentPath);
            uploadInput.value = '';
        }).catch(() => alert('上传失败，网络异常'));
    }
}

// 拖拽上传事件绑定
dropZone.ondragover = (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
}
dropZone.ondragleave = (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
}
dropZone.ondrop = (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    let files = e.dataTransfer.files;
    if(files.length > 0){
        let formData = new FormData();
        for(let f of files){
            formData.append('files', f);
        }
        formData.append('path', currentPath);
        fetch('/upload', {method: 'POST', body: formData})
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            listFiles(currentPath);
        }).catch(() => alert('上传失败，网络异常'));
    }
}

// 页面首次加载列出根目录
listFiles();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    # 渲染主页，集成Bootstrap黑底红字风格
    return render_template_string(HTML)

@app.route('/list')
def list_files():
    # 返回指定路径下的文件夹和文件列表，JSON格式
    req_path = request.args.get('path', '').strip('/')
    try:
        full_path = safe_path(req_path)
        if not os.path.exists(full_path):
            return jsonify([])

        items = []
        for name in sorted(os.listdir(full_path), key=lambda x: (not os.path.isdir(os.path.join(full_path, x)), x.lower())):
            if name.startswith('.'):
                continue  # 忽略隐藏文件
            item_path = os.path.join(full_path, name)
            item_type = 'folder' if os.path.isdir(item_path) else 'file'
            items.append({'name': name, 'type': item_type})
        return jsonify(items)
    except Exception:
        return jsonify([])

@app.route('/download')
def download_file():
    # 下载指定文件
    req_path = request.args.get('path', '').strip('/')
    try:
        full_path = safe_path(req_path)
        if not os.path.isfile(full_path):
            return "文件未找到", 404
        # 使用 send_from_directory 支持中文文件名
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception:
        return "非法路径或文件不存在", 403

@app.route('/delete', methods=['POST'])
def delete_file_or_dir():
    # 删除文件或文件夹
    data = request.get_json()
    req_path = data.get('path', '').strip('/')
    if not req_path:
        return jsonify({'message': '路径不能为空'})
    try:
        full_path = safe_path(req_path)
        if not os.path.exists(full_path):
            return jsonify({'message': '文件或文件夹不存在'})
        if os.path.isdir(full_path):
            os.rmdir(full_path)
        else:
            os.remove(full_path)
        return jsonify({'message': '删除成功'})
    except Exception as e:
        return jsonify({'message': f'删除失败: {e}'})

@app.route('/rename', methods=['POST'])
def rename():
    # 重命名文件或文件夹
    data = request.get_json()
    req_path = data.get('path', '').strip('/')
    new_name = data.get('new_name', '').strip()
    if not new_name or '/' in new_name or '\\' in new_name:
        return jsonify({'message': '新名称不能为空，且不能包含 / 或 \\ '})
    try:
        old_full = safe_path(req_path)
        if not os.path.exists(old_full):
            return jsonify({'message': '源文件/文件夹不存在'})
        new_full = os.path.join(os.path.dirname(old_full), new_name)
        if os.path.exists(new_full):
            return jsonify({'message': '目标名称已存在'})
        os.rename(old_full, new_full)
        return jsonify({'message': '重命名成功'})
    except Exception as e:
        return jsonify({'message': f'重命名失败: {e}'})

@app.route('/mkdir', methods=['POST'])
def mkdir():
    # 创建新文件夹
    data = request.get_json()
    req_path = data.get('path', '').strip('/')
    folder_name = data.get('folder', '').strip()
    if not folder_name or '/' in folder_name or '\\' in folder_name:
        return jsonify({'message': '文件夹名称不能为空，且不能包含 / 或 \\ '})
    try:
        parent_path = safe_path(req_path)
        new_folder_path = os.path.join(parent_path, folder_name)
        if os.path.exists(new_folder_path):
            return jsonify({'message': '文件夹已存在'})
        os.makedirs(new_folder_path)
        return jsonify({'message': '新建文件夹成功'})
    except Exception as e:
        return jsonify({'message': f'创建失败: {e}'})

@app.route('/upload', methods=['POST'])
def upload():
    # 上传文件到当前文件夹
    upload_files = request.files.getlist('files')
    req_path = request.form.get('path', '').strip('/')
    try:
        upload_dir = safe_path(req_path)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        count = 0
        for file in upload_files:
            if file and file.filename:
                # 防止上传文件名包含路径，且避免隐藏文件上传
                filename = os.path.basename(file.filename)
                if filename.startswith('.'):
                    continue
                save_path = os.path.join(upload_dir, filename)
                file.save(save_path)
                count += 1
        return jsonify({'message': f'成功上传 {count} 个文件'})
    except Exception as e:
        return jsonify({'message': f'上传失败: {e}'})

if __name__ == '__main__':
    # 运行服务，调试模式开启，0.0.0.0 监听所有网卡 IP 方便局域网访问
    app.run(host='0.0.0.0', port=5000, debug=True)

"""

代码全部都是报错，实在是受不了，这个精简一点可能能运行吧，希望能运行吧。
"""
