# GoofishV2

## 安装

### 环境要求

- Python 3.13+
- MongoDB
- Minio 服务

### 依赖安装

```bash
pip install -r requirements.txt
# 或者使用 pyproject.toml
pip install -e .
```

### Playwright 安装

```bash
playwright install
```

## 配置

在根目录创建 `.env` 文件，参考示例：

```env
# Minio
MINIO_ENDPOINT="localhost:9000"
MINIO_ACCESS_KEY="your-access-key"
MINIO_SECRET_KEY="your-secret-key"

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DB=goofishv2

# Ctrips API Configuration
CTRIP_PRODUCTION_API=https://m.ctrip.com/restapi/soa2/14984/json/getHomeProductList
CTRIP_PRODUCTION_DETAIL_API=https://m.ctrip.com/restapi/soa2/14984/json/findProductDetail
CTRIP_CREATE_SHORT_URL_API=https://m.ctrip.com/restapi/soa2/14984/json/createShortUrl
CTRIP_CITYNAME=上海

# Baidu Model
BAIDU_API_URL="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token="
BAIDU_API_KEY="your-api-key"
BAIDU_SECRET_KEY="your-secret-key"

# Agiso API Configuration
AGISO_UPLOAD_IMAGE_API=https://aldsidle.agiso.com/api/GoodsManage/MediaUpload
AGISO_INSERT_DRAFT_API=https://aldsidle.agiso.com/api/GoodsManage/InsertDraft
AGISO_PUBLISH_API=https://aldsidle.agiso.com/api/GoodsManage/Publish
AGISO_SEARCH_GOODS_LIST_API=https://aldsidle.agiso.com/api/GoodsManage/SearchGoodsList
AGISO_UPDATE_ITEM_STATUS_API=https://aldsidle.agiso.com/api/GoodsManage/UpdateItemStatus

# SMTP
SMTP_SERVER=smtp.example.com
SMTP_PORT=465
SMTP_USER=your-email@example.com
SMTP_PASS=your-password
```

## 使用方法

### 登录与 Cookie 获取

首次使用需要获取各平台的登录 Cookie：

```bash
python cli.py login --platform goofish
python cli.py login --platform ctrip
python cli.py login --platform agiso
```

### 启动服务

```bash
# 启动 Web 服务器
python server.py

# 或使用 uvicorn
uvicorn server:app --reload
```

### 执行爬虫任务

```bash
python cli.py crawl --city 上海
```

### 商品合并和上传

```bash
python cli.py merge
python cli.py upload
```

### 启动 IM 自动回复系统

```bash
python cli.py im
```

## 系统结构

- `ai/`: AI 模型接口和商品管理
- `api/`: 第三方平台 API 接口封装
- `captcha/`: 验证码处理模块
- `cookies/`: 存储各平台 Cookie
- `db/`: 数据库连接和操作
- `helpers/`: 各平台登录助手
- `im/`: 即时通讯模块，处理客户消息
- `report/`: 报告生成和发送
- `route/`: FastAPI 路由定义
- `templates/`: 模板处理

## API 文档

启动服务后，访问 `http://localhost:8000/docs` 查看 Swagger API 文档。
