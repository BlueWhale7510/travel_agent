# check_installation.py
try:
    from langchain_core.messages import HumanMessage
    print("✅ langchain-core 安装成功")
except ImportError as e:
    print(f"❌ langchain-core 安装失败: {e}")

try:
    from langchain_community.llms import Ollama
    print("✅ langchain-community 安装成功")
except ImportError as e:
    print(f"❌ langchain-community 安装失败: {e}")

try:
    from langgraph.graph import StateGraph
    print("✅ langgraph 安装成功")
except ImportError as e:
    print(f"❌ langgraph 安装失败: {e}")

try:
    from datetime import datetime, timedelta
    print("✅ 标准库导入成功")
except ImportError as e:
    print(f"❌ 标准库导入失败: {e}")

# 测试 Ollama 连接
try:
    import subprocess
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Ollama 服务运行正常")
        if 'deepseek-r1:1.5b' in result.stdout:
            print("✅ DeepSeek R1 1.5b 模型已安装")
        else:
            print("⚠️  DeepSeek R1 1.5b 模型未安装，运行: ollama pull deepseek-r1:1.5b")
    else:
        print("❌ Ollama 服务未运行")
except Exception as e:
    print(f"❌ Ollama 检查失败: {e}")