# -*- coding: utf-8 -*-
"""
UI-TARS 多步循环Agent - 支持完整任务自动化
可以执行"打开浏览器搜索bilibili"这样的复杂任务
"""

import os
import sys

# 添加本地代码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'codes'))

import base64
import json
import time
from openai import OpenAI
from PIL import Image
import pyautogui
from ui_tars.action_parser import parse_action_to_structure_output, parsing_response_to_pyautogui_code
from ui_tars.prompt import COMPUTER_USE_DOUBAO, MOBILE_USE_DOUBAO

# ====== 配置 ======
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="ad381c78-bb42-44c0-bbef-9e8058f09b58"
)

MODEL_NAME = "doubao-1-5-ui-tars-250428"
MAX_STEPS = 20  # 最大执行步数，防止无限循环
SLEEP_AFTER_ACTION = 2  # 每次动作后等待时间（秒）


def take_screenshot(save_path="temp_screenshot.png"):
    """截取当前屏幕"""
    screenshot = pyautogui.screenshot()
    screenshot.save(save_path)
    return save_path


def encode_image_to_base64(image_path):
    """将图片编码为base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_image_size(image_path):
    """获取图片尺寸"""
    with Image.open(image_path) as img:
        return img.size


def execute_action(parsed_action, image_width, image_height):
    """执行单个动作"""
    action_type = parsed_action['action_type']
    action_inputs = parsed_action['action_inputs']
    
    print(f"  动作类型: {action_type}")
    print(f"  参数: {json.dumps(action_inputs, ensure_ascii=False)}")
    
    # 生成pyautogui代码
    pyautogui_code = parsing_response_to_pyautogui_code(
        responses=[parsed_action],
        image_height=image_height,
        image_width=image_width
    )
    
    # 执行代码
    try:
        exec(pyautogui_code)
        print(f"  ✓ 执行成功")
        return True
    except Exception as e:
        print(f"  ✗ 执行失败: {e}")
        return False


def run_agent_loop(task, max_steps=MAX_STEPS, use_mobile=False):
    """
    运行多步循环Agent
    
    Args:
        task: 任务描述，如 "打开谷歌浏览器并搜索bilibili"
        max_steps: 最大执行步数
        use_mobile: 是否使用移动端模式
    """
    
    print("=" * 70)
    print(f"🤖 UI-TARS Agent 开始执行任务")
    print("=" * 70)
    print(f"任务: {task}")
    print(f"最大步数: {max_steps}")
    print("=" * 70)
    
    # 准备提示模板
    prompt_template = MOBILE_USE_DOUBAO if use_mobile else COMPUTER_USE_DOUBAO
    
    # 初始化对话历史
    messages = []
    
    for step in range(1, max_steps + 1):
        print(f"\n{'='*70}")
        print(f"📸 步骤 {step}/{max_steps}")
        print(f"{'='*70}")
        
        # 1. 截取屏幕
        print("正在截取屏幕...")
        screenshot_path = take_screenshot()
        image_width, image_height = get_image_size(screenshot_path)
        base64_image = encode_image_to_base64(screenshot_path)
        print(f"✓ 截图完成 ({image_width}x{image_height})")
        
        # 2. 构建提示
        if step == 1:
            # 第一步：包含任务描述
            prompt = prompt_template.format(
                language="Chinese",
                instruction=task
            )
        else:
            # 后续步骤：继续执行任务
            prompt = prompt_template.format(
                language="Chinese", 
                instruction=f"继续执行任务: {task}"
            )
        
        # 3. 构建消息
        user_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }}
            ]
        }
        messages.append(user_message)
        
        # 4. 调用API
        print("正在调用Doubao API...")
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.0,
                max_tokens=400,
                stream=False
            )
            
            model_response = response.choices[0].message.content
            print(f"\n模型响应:\n{model_response}\n")
            
            # 添加助手响应到历史
            messages.append({
                "role": "assistant",
                "content": model_response
            })
            
        except Exception as e:
            print(f"✗ API调用失败: {e}")
            break
        
        # 5. 解析动作
        try:
            parsed_actions = parse_action_to_structure_output(
                text=model_response,
                factor=1000,
                origin_resized_height=image_height,
                origin_resized_width=image_width,
                model_type="doubao"
            )
        except Exception as e:
            print(f"✗ 解析失败: {e}")
            break
        
        # 6. 检查是否完成
        if parsed_actions and parsed_actions[0]['action_type'] == 'finished':
            print("\n" + "=" * 70)
            print("✓ 任务完成!")
            print("=" * 70)
            result = parsed_actions[0]['action_inputs'].get('content', '任务已完成')
            print(f"结果: {result}")
            break
        
        # 7. 执行所有动作
        print(f"\n执行动作 (共 {len(parsed_actions)} 个):")
        for i, action in enumerate(parsed_actions, 1):
            print(f"\n动作 {i}:")
            thought = action.get('thought')
            if thought:
                print(f"  思考: {thought}")
            
            success = execute_action(action, image_width, image_height)
            if not success:
                print(f"✗ 动作执行失败，终止任务")
                return
            
            # 动作间短暂等待
            if i < len(parsed_actions):
                time.sleep(0.5)
        
        # 8. 等待界面更新
        print(f"\n等待 {SLEEP_AFTER_ACTION} 秒，等待界面更新...")
        time.sleep(SLEEP_AFTER_ACTION)
    
    else:
        # 达到最大步数
        print("\n" + "=" * 70)
        print(f"⚠ 已达到最大步数 ({max_steps})，任务未完成")
        print("=" * 70)


def run_custom_task():
    """运行自定义任务"""
    print("\n" + "=" * 70)
    print("🤖 UI-TARS Agent - 自定义任务模式")
    print("=" * 70)
    
    # 获取任务描述
    task = input("\n请输入任务描述: ").strip()
    if not task:
        print("❌ 任务描述不能为空")
        return
    
    # 获取最大步数
    max_steps_input = input("最大步数 (默认20): ").strip()
    max_steps = int(max_steps_input) if max_steps_input else 20
    
    # 获取设备类型
    device = input("设备类型 (desktop/mobile，默认desktop): ").strip().lower()
    use_mobile = device == "mobile"
    
    # 显示配置信息
    print("\n" + "=" * 70)
    print("📋 任务配置")
    print("=" * 70)
    print(f"任务描述: {task}")
    print(f"最大步数: {max_steps}")
    print(f"设备类型: {'移动端' if use_mobile else '桌面端'}")
    print("=" * 70)
    
    # 确认执行
    confirm = input("\n是否开始执行? (y/n，默认y): ").strip().lower()
    if confirm and confirm != 'y':
        print("❌ 已取消执行")
        return
    
    # 执行任务
    run_agent_loop(task, max_steps, use_mobile)


if __name__ == "__main__":
    import sys
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                  UI-TARS 多步循环 Agent                          ║
║                  支持完整任务自动化                              ║
╚══════════════════════════════════════════════════════════════════╝

💡 使用示例:
   - 打开谷歌浏览器
   - 打开谷歌浏览器并搜索bilibili
   - 打开Word并创建新文档
   - 打开微信并发送消息给张三
    """)
    
    run_custom_task()
