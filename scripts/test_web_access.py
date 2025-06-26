#!/usr/bin/env python3
"""
测试Web界面访问的脚本
"""

import requests
import time
import sys

def test_web_access():
    """测试Web界面是否可以访问"""
    url = "http://localhost:8501"
    
    print(f"🌐 测试Web界面访问: {url}")
    
    try:
        # 等待几秒让Streamlit完全启动
        print("⏳ 等待Streamlit启动...")
        time.sleep(3)
        
        # 发送HTTP请求
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Web界面访问成功！")
            print(f"📊 状态码: {response.status_code}")
            print(f"📄 内容长度: {len(response.text)} 字符")
            
            # 检查是否包含Streamlit特征内容
            if "streamlit" in response.text.lower() or "st-" in response.text:
                print("✅ 确认为Streamlit应用")
            else:
                print("⚠️  响应内容可能不是Streamlit应用")
            
            return True
        else:
            print(f"❌ Web界面访问失败，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Web界面，请确认应用已启动")
        return False
    except requests.exceptions.Timeout:
        print("❌ 连接超时，Web界面可能启动缓慢")
        return False
    except Exception as e:
        print(f"❌ 访问Web界面时出错: {e}")
        return False

if __name__ == "__main__":
    success = test_web_access()
    sys.exit(0 if success else 1)
