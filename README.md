# Cronicle Telegram Bot

这是一个用于控制NAS上Cronicle任务的Telegram机器人，通过Webhook模式运行，支持通过按钮和命令触发Cronicle事件。

## 功能特点

- 基于Webhook模式的Telegram Bot
- 支持按钮菜单和命令触发Cronicle事件
- 支持用户权限控制
- 支持动作二次确认
- 支持Docker部署
- 内置健康检查服务

## 快速开始

### 前提条件

- 一个已创建的Telegram Bot（通过BotFather获取Token）
- 一个可公网访问的域名，并配置了Nginx反向代理和SSL证书
- Cronicle API访问权限

### 配置步骤

1. 复制环境变量示例文件并修改

```bash
cp .env.example .env
```

2. 编辑`.env`文件，填入必要的配置信息

```
# Telegram 配置
BOT_TOKEN=your_telegram_token
ALLOWED_USER_IDS=123456789

# NAS API 配置
API_BASE_URL=http://your-nas-ip:3012
API_KEY=your_api_key

# Webhook 域名（使用公网IP或域名）
# 如果设置为localhost或127.0.0.1，将自动切换到轮询模式
# 生产环境请设置为可从外网访问的域名或IP
WEBHOOK_HOST=127.0.0.1
# Webhook端口（默认8443）
WEBHOOK_PORT=8443
# Webhook路径（默认为/webhook/BOT_TOKEN）
WEBHOOK_PATH=/webhook/BOT_TOKEN%
```

3. 编辑`actions.yaml`文件，配置你需要的动作

```yaml
categories:
  - name: "示例分类"
    actions:
      - title: "示例动作"
        command: "example action"
        event_id: "your_cronicle_event_id"
        confirm: true  # 是否需要二次确认
```

### 使用Docker部署

```bash
docker-compose up -d
```

### Nginx反向代理配置

本项目设计为通过Nginx进行SSL终结，以下是一个示例Nginx配置：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location /webhook/your_bot_token {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 健康检查

机器人内置了健康检查服务，可通过以下URL访问：

```
http://your-server:8080/health
```

正常情况下会返回：

```json
{"status": "ok"}
```

## 命令列表

- `/start` - 打开控制菜单
- `/help` - 查看使用帮助
- `/status` - 检查机器人状态
- `/webhook_status` - 查看Webhook状态
- `/version` - 查看当前版本

此外，所有在`actions.yaml`中配置的动作都会自动生成对应的命令。

## 注意事项

- 确保Nginx配置了正确的SSL证书和反向代理设置
- 确保Telegram Bot Token正确
- 确保API_KEY有权限执行Cronicle事件
- 确保ALLOWED_USER_IDS设置正确，以防止未授权访问

## GitHub Actions

本项目包含两个GitHub Actions工作流：

1. 用于自动构建Docker镜像并推送到Docker Hub
2. 用于版本发布和Docker镜像构建

### 工作流触发条件

- 当向`main`分支推送代码时
- 当创建以`v`开头的标签时（例如`v1.0.0`）
- 当向`main`分支发起Pull Request时
- 当向`main`分支推送且`version.py`文件发生变动时（触发版本发布）

### 配置

工作流使用以下GitHub Secrets进行认证：

- `DOCKERHUB_USERNAME`：Docker Hub用户名
- `DOCKERHUB_TOKEN`：Docker Hub访问令牌

你需要在Docker Hub上创建一个访问令牌，并在GitHub仓库的Secrets设置中添加以上两个Secrets。

工作流会自动为以下情况打标签：

- 分支名称（用于分支推送）
- PR编号（用于Pull Request）
- 版本号（用于标签推送，例如`v1.0.0`）
- 主版本和次版本号（例如`v1.0`）

### 手动触发Release工作流

如果在手动触发Release工作流时遇到"Resource not accessible by integration"错误，请确保GitHub仓库的Actions权限设置正确。该工作流需要`contents: write`和`actions: write`权限来创建Release和触发其他工作流。

### 使用Docker镜像

构建的镜像可以通过以下方式拉取：

```bash
docker pull your-dockerhub-username/repo-name:[tag]
```

将`your-dockerhub-username`替换为你的Docker Hub用户名，`repo-name`替换为仓库名称，`[tag]`替换为相应的标签。
