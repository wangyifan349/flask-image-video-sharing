# 📷 Flask 图片和视频分享平台 🎥

欢迎来到 **Flask 图片和视频分享平台**！该平台让您能够轻松注册、登录、上传和管理图片与视频。您还可以搜索其他用户，探索他们分享的精彩内容。现在就加入我们，分享您的精彩瞬间吧！

## ✨ 功能特点

- 📝 **用户注册和登录**：提供直观简洁的用户注册和登录界面。
- 📤 **上传和管理文件**：支持上传和管理图片与视频，支持格式包括：`png`、`jpg`、`jpeg`、`gif`、`mp4`、`avi`、`mov`、`mkv`。
- 🔍 **智能用户搜索**：采用最长公共子序列算法，按匹配度降序排列搜索结果，精准找到您感兴趣的用户。
- 👀 **浏览用户主页**：可访问其他用户的主页，查看他们分享的所有图片和视频。
- 🌐 **开放 API 接口**：
  - **用户搜索接口**：方便地搜索用户信息。
  - **获取用户文件信息接口**：获取指定用户的所有图片和视频信息。
  - **下载指定文件接口**：直接下载用户的特定图片或视频文件。

## 📁 项目结构

```plaintext
flask-image-video-sharing/
├── app.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   └── search.html
├── static/
│   └── uploads/
│       ├── images/
│       └── videos/
└── requirements.txt
```

## 🚀 快速开始

### 环境要求

- Python 3.7+
- pip

### 安装步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/wangyifan349/flask-image-video-sharing.git
   cd flask-image-video-sharing
   ```

2. **创建并激活虚拟环境**

   ```bash
   python -m venv venv
   source venv/bin/activate   # 对于 Linux/MacOS
   venv\Scripts\activate      # 对于 Windows
   ```

3. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

4. **运行应用**

   ```bash
   python app.py
   ```

5. **访问应用**

   在浏览器中打开：[http://127.0.0.1:5000](http://127.0.0.1:5000)

## 📚 使用指南

### 用户注册和登录

- **🆕 注册**：访问 `/register` 页面，简单注册您的账户。
- **🔑 登录**：通过 `/login` 页面使用您的凭证进行登录。

### 上传与管理功能

- **🏠 用户主页**：登录后，自动导航至您的用户主页。
- **➕ 上传文件**：选择并上传图片或视频，与社区分享您的创意。
- **🗑️ 管理文件**：浏览和管理您的上传内容，支持删除不需要的文件。

### 搜索与浏览用户

- **🔎 搜索用户**：访问 `/search` 页面，输入关键字，智能搜索其他用户。
- **👤 查看个人主页**：在搜索结果中点击用户名，可进入该用户主页，探索他们分享的内容。

### 🌐 API 接口使用

使用命令行工具（如 `wget`）可以直接与以下 API 交互：

#### 1. 用户搜索 API

- **URL**：`/api/search_user`
- **方法**：GET
- **参数**：
  - `keyword`（必需）：要搜索的用户名关键字。
- **示例**：

  ```bash
  wget -qO- "http://127.0.0.1:5000/api/search_user?keyword=alice"
  ```

- **返回示例**：

  ```json
  {
    "results": ["alice", "alice123"]
  }
  ```

#### 2. 获取用户文件信息 API

- **URL**：`/api/user_files/<username>`
- **方法**：GET
- **示例**：

  ```bash
  wget -qO- "http://127.0.0.1:5000/api/user_files/alice"
  ```

- **返回示例**：

  ```json
  {
    "username": "alice",
    "images": ["image1.jpg", "image2.png"],
    "videos": ["video1.mp4", "video2.avi"]
  }
  ```

#### 3. 下载指定用户文件 API

- **URL**：`/api/download_file/<username>/<filetype>/<filename>`
- **方法**：GET
- **参数**：
  - `filetype`：`images` 或 `videos`
  - `filename`：文件名，从第二个 API 获取
- **示例**：

  ```bash
  wget "http://127.0.0.1:5000/api/download_file/alice/images/image1.jpg"
  ```

## ⚠️ 注意事项

- **数据持久性**：该应用目前使用内存存储用户和文件信息，程序重启后数据会丢失。建议在生产环境中使用数据库（如 SQLite、MySQL、PostgreSQL）进行持久化存储。
- **文件权限**：请确保程序有权限在 `static/uploads/images` 和 `static/uploads/videos` 目录下读写。
- **安全密钥**：请将 `app.config['SECRET_KEY']` 替换为您自己的随机密钥，以确保会话安全。
- **文件安全**：务必实施文件上传安全检查，防止用户上传恶意文件，建议对文件类型和大小进行验证。
- **API 安全性**：在实际应用中，建议对 API 接口添加身份验证和权限控制，防止未授权的访问。

## 📄 许可证

本项目根据 [GNU 通用公共许可证 第 3 版](https://www.gnu.org/licenses/gpl-3.0.zh-cn.html)（GPLv3）授权。

**注**：由于版权原因，README 中不直接包含完整的许可证文本。您可以通过 [GNU 官网](https://www.gnu.org/licenses/gpl-3.0.zh-cn.html) 阅读许可证的完整内容。

## 🔗 联系方式

如果您有任何问题或需要支持，欢迎通过以下方式与我联系：

- **GitHub**：[wangyifan349](https://github.com/wangyifan349)
- **Email**：wangyifan349@gmail.com

---

感谢您的关注和使用！✨
