# 📷 Flask 图片和视频分享平台 🎥

欢迎来到**Flask 图片和视频分享平台**！该平台允许用户轻松注册、登录、上传及管理图片和视频。您还可以搜索其他用户，并探索社区共享的创意内容。立刻开始分享您的精彩时刻吧！

## ✨ 功能特点

- 📝 **用户注册和登录**：支持用户注册和登录的直观界面。
- 📤 **上传和管理文件**：用户可以上传和管理图片和视频，支持格式包括：`png`, `jpg`, `jpeg`, `gif`, `mp4`, `avi`, `mov`, `mkv`。
- 🔍 **搜索用户**：采用最长公共子序列算法，按匹配度排序搜索结果。
- 👀 **浏览用户主页**：查看其他用户分享的多彩内容。
- 🌐 **RESTful API**：
  - 搜索用户
  - 获取用户全部文件信息
  - 下载指定用户文件

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
│   ├── search.html
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
- **🗂️ 管理文件**：浏览和管理您的上传内容，允许删除不需要的文件。

### 搜索与浏览用户

- **🔎 搜索用户**：访问 `/search` 页面，输入关键字，智能搜索其他用户。
- **👤 查看个人主页**：在搜索结果中点击用户名，进入该用户主页，探索他们分享的内容。

### 🔗 API 接口

使用命令行工具（如 `wget`）与以下 API 交互：

#### 1. 用户搜索 API

- **URL**：`/api/search_user`
- **方法**：GET
- **参数**：`keyword` - 要搜索的用户名关键字。
- **示例**：

  ```bash
  wget -qO- "http://127.0.0.1:5000/api/search_user?keyword=alice"
  ```

#### 2. 获取用户文件信息 API

- **URL**：`/api/user_files/<username>`
- **方法**：GET
- **示例**：

  ```bash
  wget -qO- "http://127.0.0.1:5000/api/user_files/alice"
  ```

#### 3. 下载指定用户文件 API

- **URL**：`/api/download_file/<username>/<filetype>/<filename>`
- **方法**：GET
- **参数**：
  - `filetype`：`images` 或 `videos`
  - `filename`：文件名
- **示例**：

  ```bash
  wget "http://127.0.0.1:5000/api/download_file/alice/images/image1.jpg"
  ```

## ⚠️ 注意事项

- 该应用使用内存存储用户和文件信息，程序重启后数据会丢失。建议使用数据库进行持久化存储。
- 确保程序有权限在 `static/uploads/images` 和 `static/uploads/videos` 目录下读写。
- 请将 `app.config['SECRET_KEY']` 替换为您自己的安全密钥，以确保会话安全。
- 实施文件上传安全检查，防止上传恶意文件。

## 📄 许可证

本项目根据 GNU 通用公共许可证 v3.0 授权。

```
GNU 通用公共许可证
版本 3，2007 年 6 月 29 日

版权所有 (C) 2007 自由软件基金会, Inc. <http://fsf.org/>

允许任何人复制和发布本许可证文件的逐字副本，
但不允许更改。

...

[在此处包含完整的许可证文本]
```

## 🔗 联系

如有任何问题或需要支持，欢迎通过 [GitHub](https://github.com/wangyifan349) 与项目所有者联系。

wangyifan349@gmail.com
