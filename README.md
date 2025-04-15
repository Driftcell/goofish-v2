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

## Helper 类使用指南

GoofishV2 项目中的 Helper 类用于处理各平台的登录和会话管理，提供了统一的接口进行浏览器自动化操作。

### 基础 LoginHelper 类

所有登录助手的基类，提供了通用的浏览器操作功能。

```python
from playwright.async_api import async_playwright
from helpers.base import LoginHelper

async with async_playwright() as p:
    login_helper = LoginHelper(playwright=p)
    await login_helper.init(headless=False)  # 初始化浏览器环境
    cookies = await login_helper.get_cookies()  # 获取当前会话 cookies
    await login_helper.save_cookies("cookies/example.json")  # 保存 cookies 到文件
```

### GoofishLoginHelper 类

专用于闲鱼平台登录的助手类。

```python
from playwright.async_api import async_playwright
from helpers.goofish import GoofishLoginHelper

async with async_playwright() as p:
    login_helper = GoofishLoginHelper(playwright=p)
    await login_helper.init()  # 初始化并打开闲鱼网站
    qr_code = await login_helper.login("qrcode.png")  # 生成登录二维码并保存到文件
    
    # 等待用户扫码登录
    while await login_helper.check_login_state() != LoginState.LOGINED:
        await asyncio.sleep(1)
        
    # 保存登录状态
    await login_helper.save_cookies("cookies/goofish.json")
```

### AgisoLoginHelper 类

专用于 Agiso 系统登录的助手类，继承自 GoofishLoginHelper。

```python
from playwright.async_api import async_playwright
from helpers.agiso import AgisoLoginHelper

async with async_playwright() as p:
    login_helper = AgisoLoginHelper(playwright=p)
    await login_helper.init()  # 初始化并打开闲鱼网站
    await login_helper.login()  # 显示登录二维码
    
    # 等待用户扫码登录
    while await login_helper.check_login_state() != LoginState.LOGINED:
        await asyncio.sleep(1)
        
    # 获取 TOKEN 和 cookies
    token = await login_helper.get_token()  # 获取 Agiso 系统的 TOKEN
    cookies = await login_helper.get_cookies()  # 获取当前会话 cookies
    
    # 保存登录状态
    await login_helper.save_cookies("cookies/agiso.json")
```

### CtripLoginHelper 类

专用于携程系统登录的助手类。

```python
from playwright.async_api import async_playwright
from helpers.ctrip import CtripLoginHelper

async with async_playwright() as p:
    login_helper = CtripLoginHelper(
        playwright=p,
        entrypoint="https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale"
    )
    await login_helper.init()  # 初始化并打开携程联盟页面
    
    # 等待用户手动登录
    while await login_helper.check_login_state() != LoginState.LOGINED:
        await asyncio.sleep(1)
        
    # 获取关键参数
    alliance_id = login_helper.alliance_id()  # 获取联盟ID
    sid = login_helper.sid()  # 获取会话ID
    
    # 保存登录状态
    await login_helper.save_cookies("cookies/ctrip.json")
```

## API 类使用指南

GoofishV2 项目提供了与各平台交互的 API 类，封装了数据抓取和上传的功能。

### CtripApi 类

用于与携程旅游 API 交互，抓取产品信息。

```python
from api.ctrip import CtripApi
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorClient

# 创建数据库和 MinIO 连接
db_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = db_client[os.getenv("MONGO_DB")]
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)

# 初始化携程 API 客户端
ctrip_api = CtripApi(
    cookies=ctrip_cookies,  # 从 cookies 文件加载
    db=db,
    minio=minio_client,
    alliance_id=alliance_id,  # 从 CtripLoginHelper 获取
    sid=sid  # 从 CtripLoginHelper 获取
)

# 运行爬虫，抓取上海的产品信息
await ctrip_api.run(city_name="上海", download_images_task_num=10)
```

### AgisoApi 类

用于与 Agiso 系统交互，上传和管理商品。

```python
from api.agiso import AgisoApi
from minio import Minio

# 初始化 Agiso API 客户端
agiso_api = AgisoApi(
    cookies=agiso_cookies,  # 从 cookies 文件加载
    token=token,  # 从 AgisoLoginHelper 获取
    minio=minio_client
)

# 搜索已上传的商品
goods_list = await agiso_api.search_good_list()

# 上传新商品
await agiso_api.upload_item(
    item=product_info,  # 要上传的商品信息
    draft=False,  # 是否仅保存为草稿
    price_mode="fixed",  # 价格模式：fixed (固定价格) 或 smart (使用原价)
    price=0.01,  # 如果 price_mode 为 fixed，则使用此价格
    template=description_template  # 商品描述模板
)

# 更新商品状态
await agiso_api.update_item_status(id="商品ID", online=True)  # 上架商品
```

## API 文档

启动服务后，访问 `http://localhost:8000/docs` 查看 Swagger API 文档。
