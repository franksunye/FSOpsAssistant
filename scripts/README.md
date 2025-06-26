# FSOA 脚本说明

本目录包含FSOA系统的核心启动和管理脚本。

## 📋 脚本列表

### 🚀 启动脚本

#### `start_web.py`
**用途**: 启动Web管理界面  
**适用场景**: 开发测试、配置管理、系统监控  
**命令**: `python scripts/start_web.py`  
**端口**: 默认8501  
**特点**: 
- 仅启动Streamlit Web界面
- 不包含Agent后台服务
- 适合开发调试和配置管理

#### `start_agent.py`
**用途**: 启动Agent后台服务  
**适用场景**: 生产环境后台运行  
**命令**: `python scripts/start_agent.py`  
**特点**:
- 仅启动Agent定时任务服务
- 后台运行，无Web界面
- 适合服务器部署

#### `start_full_app.py`
**用途**: 启动完整应用（Web界面 + Agent服务）  
**适用场景**: 完整功能演示、小规模生产部署  
**命令**: `python scripts/start_full_app.py`  
**特点**:
- 同时启动Web界面和Agent服务
- 完整的系统功能
- 适合一体化部署

### 🔧 管理脚本

#### `init_db.py`
**用途**: 初始化数据库  
**适用场景**: 首次部署、数据库重置  
**命令**: `python scripts/init_db.py`  
**功能**:
- 创建数据库表结构
- 初始化基础配置数据
- 验证数据库连接

#### `run_tests.py`
**用途**: 运行测试套件  
**适用场景**: 开发验证、CI/CD流程  
**命令**: `python scripts/run_tests.py [选项]`  
**选项**:
- `--unit`: 仅运行单元测试
- `--integration`: 仅运行集成测试
- `--coverage`: 生成代码覆盖率报告
- `--verbose`: 详细输出

## 🚀 快速开始

### 开发环境
```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 启动Web界面进行开发测试
python scripts/start_web.py
```

### 生产环境
```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 启动完整应用
python scripts/start_full_app.py
```

### 测试验证
```bash
# 运行完整测试套件
python scripts/run_tests.py

# 运行单元测试
python scripts/run_tests.py --unit

# 生成覆盖率报告
python scripts/run_tests.py --coverage
```

## 📝 使用建议

### 开发阶段
1. 使用 `start_web.py` 进行界面开发和功能测试
2. 使用 `run_tests.py` 进行代码验证
3. 通过Web界面的[系统管理 → 系统测试]进行集成测试

### 部署阶段
1. 首先运行 `init_db.py` 初始化数据库
2. 配置 `.env` 文件中的必要参数
3. 使用 `start_full_app.py` 启动完整服务
4. 通过Web界面进行系统配置和验证

### 生产运维
1. 使用 `start_agent.py` 在后台运行Agent服务
2. 单独部署Web界面用于管理和监控
3. 定期运行测试脚本验证系统健康状态

## ⚠️ 注意事项

1. **环境配置**: 确保 `.env` 文件配置正确
2. **数据库初始化**: 首次运行前必须执行 `init_db.py`
3. **端口占用**: Web界面默认使用8501端口
4. **权限要求**: 确保脚本具有执行权限
5. **依赖检查**: 运行前确保所有Python依赖已安装

## 🔍 故障排除

### 常见问题
- **模块导入错误**: 检查Python路径和依赖安装
- **配置加载失败**: 验证 `.env` 文件格式和内容
- **数据库连接错误**: 确认数据库文件权限和路径
- **端口占用**: 检查8501端口是否被其他程序占用

### 调试建议
1. 查看控制台输出的错误信息
2. 检查日志文件 `logs/fsoa.log`
3. 通过Web界面的系统测试功能诊断问题
4. 使用 `run_tests.py --verbose` 获取详细测试信息
