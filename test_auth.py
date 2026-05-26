"""
认证系统完整测试脚本
使用方法: python test_auth.py
测试项目:
1. 用户注册成功
2. 用户登录成功
3. 获取当前用户信息成功
4. 重复注册被拒绝（相同手机号/用户名）
5. 错误密码登录被拒绝
6. 无效 Token 被拒绝
7. 无 Token 访问被拒绝
8. Token 隔离性正确
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

# 测试结果统计
test_results = {
    "passed": 0,
    "failed": 0,
    "total": 0
}

def log_test(test_name, status, message=""):
    """记录测试结果"""
    test_results["total"] += 1
    if status:
        test_results["passed"] += 1
        print(f"✅ [{test_name}] 通过")
    else:
        test_results["failed"] += 1
        print(f"❌ [{test_name}] 失败 - {message}")
    return status


def test_1_register():
    """测试1: 用户注册成功"""
    print("\n" + "=" * 60)
    print("测试1: 用户注册成功")
    print("=" * 60)
    
    # 生成符合中国大陆手机号格式的号码 (1开头，第二位3-9，共11位)
    import random
    timestamp = int(time.time())
    user_data = {
        "name": f"测试用户_{timestamp}",
        "phone": f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}",
        "password": "test123456",
        "role": "user"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            # 验证返回字段
            required_fields = ["id", "name", "phone", "role", "created_at"]
            has_all_fields = all(field in data for field in required_fields)
            
            # 验证密码不在响应中
            no_password = "password" not in data and "hashed_password" not in data
            
            return log_test("用户注册成功", has_all_fields and no_password, 
                          "缺少必要字段或包含密码")
        else:
            print(f"错误详情: {response.text}")
            return log_test("用户注册成功", False, f"状态码: {response.status_code}")
    except Exception as e:
        return log_test("用户注册成功", False, str(e))


def test_2_login():
    """测试2: 用户登录成功"""
    print("\n" + "=" * 60)
    print("测试2: 用户登录成功")
    print("=" * 60)
    
    # 先注册一个新用户用于登录测试
    import random
    timestamp = int(time.time())
    username = f"登录测试用户_{timestamp}"
    phone = f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}"
    password = "login123"
    
    register_data = {
        "name": username,
        "phone": phone,
        "password": password
    }
    
    try:
        # 注册用户
        reg_response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if reg_response.status_code != 201:
            print(f"注册失败: {reg_response.text}")
            return log_test("用户登录成功", False, "前置注册失败")
        
        # 登录
        form_data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", data=form_data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"Token类型: {token_data.get('token_type')}")
            print(f"Access Token: {token_data['access_token'][:50]}...")
            
            # 验证返回字段
            has_token = "access_token" in token_data
            has_type = token_data.get("token_type") == "bearer"
            
            return log_test("用户登录成功", has_token and has_type, 
                          "缺少token或类型不正确")
        else:
            print(f"错误详情: {response.text}")
            return log_test("用户登录成功", False, f"状态码: {response.status_code}")
    except Exception as e:
        return log_test("用户登录成功", False, str(e))


def test_3_get_current_user():
    """测试3: 获取当前用户信息成功"""
    print("\n" + "=" * 60)
    print("测试3: 获取当前用户信息成功")
    print("=" * 60)
    
    # 先注册并登录获取token
    import random
    timestamp = int(time.time())
    username = f"信息测试用户_{timestamp}"
    phone = f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}"
    password = "info123"
    
    try:
        # 注册
        reg_response = requests.post(f"{BASE_URL}/auth/register", json={
            "name": username,
            "phone": phone,
            "password": password
        })
        
        if reg_response.status_code != 201:
            print(f"注册失败: {reg_response.text}")
            return log_test("获取当前用户信息", False, "前置注册失败")
        
        # 登录
        login_response = requests.post(f"{BASE_URL}/auth/login", data={
            "username": username,
            "password": password
        })
        
        if login_response.status_code != 200:
            print(f"登录失败: {login_response.text}")
            return log_test("获取当前用户信息", False, "前置登录失败")
        
        token = login_response.json()["access_token"]
        
        # 获取用户信息
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"用户信息: {json.dumps(user_data, ensure_ascii=False, indent=2)}")
            
            # 验证返回的用户信息正确
            is_correct_user = (
                user_data.get("name") == username and
                user_data.get("phone") == phone and
                "password" not in user_data and
                "hashed_password" not in user_data
            )
            
            return log_test("获取当前用户信息", is_correct_user, 
                          "用户信息不匹配或包含敏感信息")
        else:
            print(f"错误详情: {response.text}")
            return log_test("获取当前用户信息", False, f"状态码: {response.status_code}")
    except Exception as e:
        return log_test("获取当前用户信息", False, str(e))


def test_4_duplicate_registration():
    """测试4: 重复注册被拒绝（相同手机号/用户名）"""
    print("\n" + "=" * 60)
    print("测试4: 重复注册被拒绝")
    print("=" * 60)
    
    import random
    timestamp = int(time.time())
    base_username = f"重复测试用户_{timestamp}"
    base_phone = f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}"
    password = "dup123"
    
    try:
        # 第一次注册
        reg1 = requests.post(f"{BASE_URL}/auth/register", json={
            "name": base_username,
            "phone": base_phone,
            "password": password
        })
        
        if reg1.status_code != 201:
            print(f"首次注册失败: {reg1.text}")
            return log_test("重复注册被拒绝", False, "首次注册失败")
        
        print("✅ 首次注册成功")
        
        # 第二次注册 - 相同用户名
        reg2 = requests.post(f"{BASE_URL}/auth/register", json={
            "name": base_username,
            "phone": f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}",
            "password": password
        })
        
        print(f"相同用户名注册 - 状态码: {reg2.status_code}")
        duplicate_name_rejected = reg2.status_code in [400, 409, 500]
        
        # 第三次注册 - 相同手机号
        reg3 = requests.post(f"{BASE_URL}/auth/register", json={
            "name": f"不同用户名_{timestamp}",
            "phone": base_phone,
            "password": password
        })
        
        print(f"相同手机号注册 - 状态码: {reg3.status_code}")
        duplicate_phone_rejected = reg3.status_code in [400, 409, 500]
        
        return log_test("重复注册被拒绝", 
                       duplicate_name_rejected and duplicate_phone_rejected,
                       "重复注册未被正确拒绝")
    except Exception as e:
        return log_test("重复注册被拒绝", False, str(e))


def test_5_wrong_password():
    """测试5: 错误密码登录被拒绝"""
    print("\n" + "=" * 60)
    print("测试5: 错误密码登录被拒绝")
    print("=" * 60)
    
    import random
    timestamp = int(time.time())
    username = f"密码测试用户_{timestamp}"
    phone = f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}"
    correct_password = "correct123"
    wrong_password = "wrong456"
    
    try:
        # 注册用户
        reg_response = requests.post(f"{BASE_URL}/auth/register", json={
            "name": username,
            "phone": phone,
            "password": correct_password
        })
        
        if reg_response.status_code != 201:
            print(f"注册失败: {reg_response.text}")
            return log_test("错误密码登录被拒绝", False, "前置注册失败")
        
        # 使用错误密码登录
        login_response = requests.post(f"{BASE_URL}/auth/login", data={
            "username": username,
            "password": wrong_password
        })
        
        print(f"状态码: {login_response.status_code}")
        print(f"响应: {json.dumps(login_response.json(), ensure_ascii=False, indent=2)}")
        
        # 应该返回401
        return log_test("错误密码登录被拒绝", 
                       login_response.status_code == 401,
                       f"期望401，实际{login_response.status_code}")
    except Exception as e:
        return log_test("错误密码登录被拒绝", False, str(e))


def test_6_invalid_token():
    """测试6: 无效 Token 被拒绝"""
    print("\n" + "=" * 60)
    print("测试6: 无效 Token 被拒绝")
    print("=" * 60)
    
    try:
        # 使用无效的token访问受保护接口
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        # 应该返回401
        return log_test("无效 Token 被拒绝", 
                       response.status_code == 401,
                       f"期望401，实际{response.status_code}")
    except Exception as e:
        return log_test("无效 Token 被拒绝", False, str(e))


def test_7_no_token():
    """测试7: 无 Token 访问被拒绝"""
    print("\n" + "=" * 60)
    print("测试7: 无 Token 访问被拒绝")
    print("=" * 60)
    
    try:
        # 不提供token访问受保护接口
        response = requests.get(f"{BASE_URL}/users/me")
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        # 应该返回401
        return log_test("无 Token 访问被拒绝", 
                       response.status_code == 401,
                       f"期望401，实际{response.status_code}")
    except Exception as e:
        return log_test("无 Token 访问被拒绝", False, str(e))


def test_8_token_isolation():
    """测试8: Token 隔离性正确"""
    print("\n" + "=" * 60)
    print("测试8: Token 隔离性正确")
    print("=" * 60)
    
    import random
    timestamp = int(time.time())
    
    try:
        # 创建用户A
        user_a_name = f"用户A_{timestamp}"
        user_a_phone = f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}"
        
        reg_a = requests.post(f"{BASE_URL}/auth/register", json={
            "name": user_a_name,
            "phone": user_a_phone,
            "password": "passA123"
        })
        
        if reg_a.status_code != 201:
            print(f"用户A注册失败: {reg_a.text}")
            return log_test("Token 隔离性", False, "用户A注册失败")
        
        login_a = requests.post(f"{BASE_URL}/auth/login", data={
            "username": user_a_name,
            "password": "passA123"
        })
        
        if login_a.status_code != 200:
            print(f"用户A登录失败: {login_a.text}")
            return log_test("Token 隔离性", False, "用户A登录失败")
        
        token_a = login_a.json()["access_token"]
        
        # 创建用户B
        user_b_name = f"用户B_{timestamp}"
        user_b_phone = f"1{random.randint(3,9)}{random.randint(100000000, 999999999)}"
        
        reg_b = requests.post(f"{BASE_URL}/auth/register", json={
            "name": user_b_name,
            "phone": user_b_phone,
            "password": "passB123"
        })
        
        if reg_b.status_code != 201:
            print(f"用户B注册失败: {reg_b.text}")
            return log_test("Token 隔离性", False, "用户B注册失败")
        
        login_b = requests.post(f"{BASE_URL}/auth/login", data={
            "username": user_b_name,
            "password": "passB123"
        })
        
        if login_b.status_code != 200:
            print(f"用户B登录失败: {login_b.text}")
            return log_test("Token 隔离性", False, "用户B登录失败")
        
        token_b = login_b.json()["access_token"]
        
        # 使用用户A的token获取用户信息
        headers_a = {"Authorization": f"Bearer {token_a}"}
        response_a = requests.get(f"{BASE_URL}/users/me", headers=headers_a)
        
        # 使用用户B的token获取用户信息
        headers_b = {"Authorization": f"Bearer {token_b}"}
        response_b = requests.get(f"{BASE_URL}/users/me", headers=headers_b)
        
        if response_a.status_code != 200 or response_b.status_code != 200:
            return log_test("Token 隔离性", False, "获取用户信息失败")
        
        user_a_info = response_a.json()
        user_b_info = response_b.json()
        
        print(f"用户A信息: name={user_a_info['name']}, phone={user_a_info['phone']}")
        print(f"用户B信息: name={user_b_info['name']}, phone={user_b_info['phone']}")
        
        # 验证token隔离性
        is_isolated = (
            user_a_info["name"] == user_a_name and
            user_a_info["phone"] == user_a_phone and
            user_b_info["name"] == user_b_name and
            user_b_info["phone"] == user_b_phone and
            user_a_info["name"] != user_b_info["name"]
        )
        
        return log_test("Token 隔离性", is_isolated, 
                       "Token隔离失败，用户信息混淆")
    except Exception as e:
        return log_test("Token 隔离性", False, str(e))


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {test_results['total']}")
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")
    print(f"通过率: {(test_results['passed']/test_results['total']*100):.1f}%")
    print("=" * 60)
    
    if test_results['failed'] == 0:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  有 {test_results['failed']} 个测试失败，请检查上方详情")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 开始测试认证系统")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API地址: {BASE_URL}")
    print("=" * 60)
    
    try:
        # 执行所有测试
        test_1_register()
        test_2_login()
        test_3_get_current_user()
        test_4_duplicate_registration()
        test_5_wrong_password()
        test_6_invalid_token()
        test_7_no_token()
        test_8_token_isolation()
        
        # 打印总结
        print_summary()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器！")
        print("请先启动应用：")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
