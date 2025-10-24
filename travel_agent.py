# travel_agent.py
import os
from typing import Dict, List, TypedDict, Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from datetime import datetime, timedelta
import re
import json
import random

# ==================== 配置区域 ====================
USE_API = True
DEEPSEEK_API_KEY = "sk-a83*****************59d"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# ==================== 状态定义 ====================
class TravelPlanningState(TypedDict):
    """旅行规划的状态管理"""
    user_input: str
    guest_name: str
    destination: str
    travel_date: str
    nights: int
    extracted_info: dict
    flights_result: Optional[dict]
    hotels_result: List[dict]
    selected_hotel: Optional[dict]
    booking_result: Optional[dict]
    current_step: str
    error_message: Optional[str]
    execution_log: List[str]

def get_llm():
    """获取 LLM 实例"""
    if USE_API:
        print(f"🌐 使用 DeepSeek API")
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.1
        )
    else:
        from langchain_community.llms import Ollama
        print(f"🖥️  使用本地 Ollama 模型")
        return Ollama(model="deepseek-r1:1.5b", temperature=0.1)

# ==================== 改进的模拟 API 函数 ====================
def search_flights(destination: str, date: str) -> Optional[dict]:
    """查询指定日期飞往某地的航班信息 - 改进版"""
    print(f"🔍 正在查询 {date} 前往 {destination} 的航班...")
    
    # 支持的目的地列表
    supported_destinations = {
        "北京": ["CA123", "MU456", "CZ789"],
        "上海": ["MU123", "CA456", "HO789"], 
        "广州": ["CZ123", "MU456", "CA789"],
        "东京": ["JL123", "NH456", "CA789"],
        "新加坡": ["SQ123", "CA456", "MU789"],
        "深圳": ["ZH123", "CA456", "MU789"],
        "杭州": ["CA123", "MU456", "JD789"],
        "成都": ["CA123", "3U456", "MU789"]
    }
    
    # 检查目的地是否支持
    if destination not in supported_destinations:
        return None
    
    # 为每个日期生成一致的随机结果（基于日期哈希）
    random.seed(hash(date) % 1000)  # 确保同一天的结果一致
    
    # 80%的概率有航班，20%的概率无航班（模拟真实情况）
    if random.random() < 0.2:
        return None
    
    flight_number = random.choice(supported_destinations[destination])
    base_prices = {
        "北京": 1200, "上海": 1100, "广州": 1000, 
        "东京": 3500, "新加坡": 3200, "深圳": 900,
        "杭州": 800, "成都": 950
    }
    
    # 价格波动 ±20%
    base_price = base_prices.get(destination, 1500)
    price_variation = random.randint(-200, 200)
    price = base_price + price_variation
    
    # 随机起飞时间
    departure_times = ["08:00", "10:30", "13:15", "16:45", "19:20", "22:00"]
    departure_time = random.choice(departure_times)
    
    return {
        "flight_number": flight_number,
        "price": price,
        "departure_time": departure_time,
        "airline": flight_number[:2]
    }

def search_hotels(destination: str, check_in_date: str, check_out_date: str) -> List[dict]:
    """根据地点和日期查询酒店 - 改进版"""
    print(f"🔍 正在查询 {destination} 从 {check_in_date} 到 {check_out_date} 的酒店...")
    
    hotels_data = {
        "北京": [
            {"name": "北京王府井酒店", "price_per_night": 800, "available": True, "rating": 4.3},
            {"name": "北京国贸大酒店", "price_per_night": 1200, "available": True, "rating": 4.5},
            {"name": "北京华尔道夫酒店", "price_per_night": 1600, "available": True, "rating": 4.6}
        ],
        "上海": [
            {"name": "上海外滩华尔道夫", "price_per_night": 1500, "available": True, "rating": 4.7},
            {"name": "上海浦东香格里拉", "price_per_night": 1300, "available": True, "rating": 4.6},
            {"name": "上海半岛酒店", "price_per_night": 2200, "available": True, "rating": 4.8}
        ],
        "广州": [
            {"name": "广州白天鹅宾馆", "price_per_night": 900, "available": True, "rating": 4.4},
            {"name": "广州四季酒店", "price_per_night": 1400, "available": True, "rating": 4.7},
            {"name": "广州文华东方酒店", "price_per_night": 1600, "available": True, "rating": 4.6}
        ],
        "东京": [
            {"name": "东京帝国酒店", "price_per_night": 2000, "available": True, "rating": 4.6},
            {"name": "安缦东京", "price_per_night": 4500, "available": True, "rating": 4.9},
            {"name": "东京柏悦酒店", "price_per_night": 2800, "available": True, "rating": 4.7}
        ],
        "新加坡": [
            {"name": "滨海湾金沙酒店", "price_per_night": 2500, "available": True, "rating": 4.8},
            {"name": "莱佛士酒店", "price_per_night": 3500, "available": True, "rating": 4.9},
            {"name": "文华东方酒店", "price_per_night": 1800, "available": True, "rating": 4.7}
        ],
        "深圳": [
            {"name": "深圳瑞吉酒店", "price_per_night": 1100, "available": True, "rating": 4.5},
            {"name": "深圳君悦酒店", "price_per_night": 900, "available": True, "rating": 4.4},
            {"name": "深圳四季酒店", "price_per_night": 1300, "available": True, "rating": 4.6}
        ],
        "杭州": [
            {"name": "杭州西湖国宾馆", "price_per_night": 1200, "available": True, "rating": 4.6},
            {"name": "杭州柏悦酒店", "price_per_night": 1400, "available": True, "rating": 4.7},
            {"name": "杭州西子湖四季酒店", "price_per_night": 1600, "available": True, "rating": 4.8}
        ],
        "成都": [
            {"name": "成都瑞吉酒店", "price_per_night": 1000, "available": True, "rating": 4.5},
            {"name": "成都尼依格罗酒店", "price_per_night": 1100, "available": True, "rating": 4.6},
            {"name": "成都华尔道夫酒店", "price_per_night": 1300, "available": True, "rating": 4.7}
        ]
    }
    
    return hotels_data.get(destination, [])

def book_flight_and_hotel(flight_number: str, hotel_name: str, guest_name: str) -> dict:
    """预订机票和酒店"""
    print(f"📦 正在为 {guest_name} 预订航班 {flight_number} 和酒店 {hotel_name}...")
    import hashlib
    booking_id = "BK" + flight_number + hashlib.md5(hotel_name.encode()).hexdigest()[:6].upper()
    
    return {
        "status": "success", 
        "booking_id": booking_id,
        "flight_number": flight_number,
        "hotel_name": hotel_name,
        "guest_name": guest_name,
        "message": "预订成功！请查收确认邮件。",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ==================== 改进的信息提取 ====================
def extract_info_with_llm(user_input: str) -> dict:
    """使用 DeepSeek API 提取信息 - 改进版"""
    try:
        llm = get_llm()
        
        # 获取当前日期作为参考
        today = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        请从以下用户输入中精确提取旅行规划的关键信息：
        
        用户输入: "{user_input}"
        
        今天是 {today}，请根据这个参考日期计算相对日期。
        
        请提取以下信息：
        1. 目的地 (destination) - 如：北京、上海、广州、东京、新加坡、深圳、杭州、成都等
        2. 旅行日期 (travel_date) - 格式必须为：YYYY-MM-DD
        3. 入住晚数 (nights) - 数字
        4. 客人姓名 (guest_name) - 中文姓名
        
        重要：如果用户没有指定具体日期，请使用 {today} 作为默认日期。
        
        请严格按照以下JSON格式返回，不要添加任何其他内容：
        {{
            "destination": "提取到的目的地",
            "travel_date": "计算后的具体日期", 
            "nights": 入住晚数,
            "guest_name": "提取到的姓名"
        }}
        """
        
        response = llm.invoke(prompt)
        print(f"🤖 DeepSeek 解析结果: {response.content}")
        
        # 尝试解析 JSON 响应
        try:
            json_match = re.search(r'\{[^}]+\}', response.content)
            if json_match:
                extracted_info = json.loads(json_match.group())
                
                # 验证必要字段并设置默认值
                required_fields = ["destination", "travel_date", "nights", "guest_name"]
                for field in required_fields:
                    if field not in extracted_info:
                        if field == "nights":
                            extracted_info[field] = 2
                        elif field == "travel_date":
                            extracted_info[field] = today
                        elif field == "destination":
                            extracted_info[field] = "北京"
                        elif field == "guest_name":
                            extracted_info[field] = "游客"
                
                return extracted_info
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
        
        # 如果解析失败，使用简单规则
        return extract_info_simple(user_input)
        
    except Exception as e:
        print(f"DeepSeek API 调用失败: {e}")
        return extract_info_simple(user_input)

def extract_info_simple(user_input: str) -> dict:
    """简化版信息提取 - 改进版"""
    # 获取当前日期作为默认
    today = datetime.now()
    
    extracted_info = {
        "destination": "北京",
        "travel_date": today.strftime("%Y-%m-%d"),  # 使用当前日期
        "nights": 2,
        "guest_name": "游客"
    }
    
    # 目的地提取
    destinations = ["北京", "上海", "广州", "东京", "Singapore", "深圳", "杭州", "成都"]
    for dest in destinations:
        if dest in user_input:
            extracted_info["destination"] = dest
            break
    
    # 晚数提取
    night_patterns = {
        "一晚": 1, "1晚": 1, "一天": 1, "1天": 1,
        "两晚": 2, "2晚": 2, "两天": 2, "2天": 2, 
        "三晚": 3, "3晚": 3, "三天": 3, "3天": 3,
        "四晚": 4, "4晚": 4, "四天": 4, "4天": 4,
        "五晚": 5, "5晚": 5, "五天": 5, "5天": 5
    }
    
    for pattern, nights in night_patterns.items():
        if pattern in user_input:
            extracted_info["nights"] = nights
            break
    
    # 姓名提取 - 改进版
    name_patterns = [
        r'名字是(\S{2,4})', r'我叫(\S{2,4})', r'姓名(\S{2,4})',
        r'我是(\S{2,4})', r'称我为(\S{2,4})'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, user_input)
        if match:
            name = match.group(1)
            if name and len(name) >= 2:
                extracted_info["guest_name"] = name
                break
    
    return extracted_info

# ==================== 工具节点 ====================
def extract_information_node(state: TravelPlanningState) -> TravelPlanningState:
    """信息提取节点"""
    print("\n📍 步骤1: 提取用户需求信息...")
    
    user_input = state["user_input"]
    
    # 使用 DeepSeek API 进行智能提取
    extracted_info = extract_info_with_llm(user_input)
    
    state["extracted_info"] = extracted_info
    state["destination"] = extracted_info["destination"]
    state["travel_date"] = extracted_info["travel_date"] 
    state["nights"] = extracted_info["nights"]
    state["guest_name"] = extracted_info["guest_name"]
    state["current_step"] = "information_extracted"
    state["execution_log"].append("✅ 用户需求信息提取完成")
    
    print(f"  目的地: {state['destination']}")
    print(f"  旅行日期: {state['travel_date']}")
    print(f"  入住晚数: {state['nights']}晚")
    print(f"  客人姓名: {state['guest_name']}")
    
    return state

def search_flights_node(state: TravelPlanningState) -> TravelPlanningState:
    """查询航班节点 - 改进版"""
    print(f"\n📍 步骤2: 查询前往 {state['destination']} 的航班...")
    
    flights_result = search_flights(state["destination"], state["travel_date"])
    state["flights_result"] = flights_result
    
    if flights_result:
        state["current_step"] = "flights_found"
        state["execution_log"].append(f"✅ 找到航班: {flights_result['flight_number']}")
        print(f"  ✅ 找到航班: {flights_result['flight_number']}")
        print(f"     航空公司: {flights_result['airline']}")
        print(f"     价格: {flights_result['price']}元")
        print(f"     起飞时间: {flights_result['departure_time']}")
    else:
        state["current_step"] = "flights_not_found"
        state["error_message"] = f"抱歉，{state['travel_date']} 前往 {state['destination']} 的航班已售罄或暂无航班"
        state["execution_log"].append("❌ 未找到合适航班")
        print("  ❌ 未找到合适航班")
        print(f"  💡 建议尝试其他日期或目的地")
    
    return state

def search_hotels_node(state: TravelPlanningState) -> TravelPlanningState:
    """查询酒店节点"""
    print(f"\n📍 步骤3: 查询 {state['destination']} 的酒店...")
    
    if not state["flights_result"]:
        state["error_message"] = "无法查询酒店：未找到可用航班"
        state["current_step"] = "error"
        return state
    
    check_in_date = state["travel_date"]
    check_out_date = (datetime.strptime(check_in_date, "%Y-%m-%d") + 
                     timedelta(days=state["nights"])).strftime("%Y-%m-%d")
    
    hotels_result = search_hotels(state["destination"], check_in_date, check_out_date)
    state["hotels_result"] = hotels_result
    
    if hotels_result:
        state["current_step"] = "hotels_found"
        state["execution_log"].append(f"✅ 找到 {len(hotels_result)} 家酒店")
        print(f"  ✅ 找到 {len(hotels_result)} 家可用酒店")
        for i, hotel in enumerate(hotels_result, 1):
            total_price = hotel["price_per_night"] * state["nights"]
            print(f"     {i}. {hotel['name']} - 评分: {hotel['rating']} - {hotel['price_per_night']}元/晚 (总计: {total_price}元)")
    else:
        state["current_step"] = "hotels_not_found"
        state["error_message"] = f"抱歉，未找到 {state['destination']} 的可用酒店"
        state["execution_log"].append("❌ 未找到合适酒店")
        print("  ❌ 未找到合适酒店")
    
    return state

def select_hotel_node(state: TravelPlanningState) -> TravelPlanningState:
    """选择酒店节点"""
    print(f"\n📍 步骤4: 选择酒店...")
    
    if not state["hotels_result"]:
        state["error_message"] = "无法选择酒店：未找到可用酒店"
        state["current_step"] = "error"
        return state
    
    hotels = state["hotels_result"]
    
    # 智能选择策略：选择性价比最高的（评分/价格）
    best_hotel = None
    best_score = 0
    
    for hotel in hotels:
        # 简单的性价比计算：评分 * 100 / 价格
        value_score = (hotel.get("rating", 4.0) * 100) / hotel["price_per_night"]
        if value_score > best_score:
            best_score = value_score
            best_hotel = hotel
    
    state["selected_hotel"] = best_hotel
    state["current_step"] = "hotel_selected"
    state["execution_log"].append(f"✅ 已选择酒店: {best_hotel['name']}")
    
    total_price = best_hotel["price_per_night"] * state["nights"]
    print(f"  ✅ 智能选择: {best_hotel['name']}")
    print(f"     评分: {best_hotel['rating']}")
    print(f"     价格: {best_hotel['price_per_night']}元/晚")
    print(f"     总价: {total_price}元 ({state['nights']}晚)")
    
    return state

def booking_node(state: TravelPlanningState) -> TravelPlanningState:
    """预订节点"""
    print(f"\n📍 步骤5: 执行预订操作...")
    
    if not state["flights_result"] or not state["selected_hotel"]:
        state["error_message"] = "无法执行预订：缺少航班或酒店信息"
        state["current_step"] = "error"
        return state
    
    flight_number = state["flights_result"]["flight_number"]
    hotel_name = state["selected_hotel"]["name"]
    guest_name = state["guest_name"]
    
    booking_result = book_flight_and_hotel(flight_number, hotel_name, guest_name)
    state["booking_result"] = booking_result
    state["current_step"] = "booking_completed"
    state["execution_log"].append("✅ 预订完成")
    
    print(f"  ✅ 预订成功!")
    print(f"     预订ID: {booking_result['booking_id']}")
    print(f"     航班: {flight_number}")
    print(f"     酒店: {hotel_name}")
    print(f"     客人: {guest_name}")
    print(f"     时间: {booking_result['timestamp']}")
    
    return state

def error_handling_node(state: TravelPlanningState) -> TravelPlanningState:
    """错误处理节点"""
    print(f"\n❌ 错误处理: {state['error_message']}")
    state["execution_log"].append(f"❌ 流程中断: {state['error_message']}")
    return state

# ==================== 条件路由 ====================
def route_after_extraction(state: TravelPlanningState) -> str:
    return "search_flights"

def route_after_flight_search(state: TravelPlanningState) -> str:
    if state["flights_result"]:
        return "search_hotels"
    else:
        return "error"

def route_after_hotel_search(state: TravelPlanningState) -> str:
    if state["hotels_result"]:
        return "select_hotel"
    else:
        return "error"

def route_after_hotel_selection(state: TravelPlanningState) -> str:
    if state["selected_hotel"]:
        return "booking"
    else:
        return "error"

def route_after_booking(state: TravelPlanningState) -> str:
    if state["booking_result"] and state["booking_result"]["status"] == "success":
        return "end"
    else:
        return "error"

# ==================== 构建工作流 ====================
def create_travel_agent():
    """创建旅行规划Agent"""
    workflow = StateGraph(TravelPlanningState)
    
    workflow.add_node("extract_information", extract_information_node)
    workflow.add_node("search_flights", search_flights_node)
    workflow.add_node("search_hotels", search_hotels_node)
    workflow.add_node("select_hotel", select_hotel_node)
    workflow.add_node("booking", booking_node)
    workflow.add_node("error", error_handling_node)
    
    workflow.set_entry_point("extract_information")
    
    workflow.add_conditional_edges("extract_information", route_after_extraction, {"search_flights": "search_flights"})
    workflow.add_conditional_edges("search_flights", route_after_flight_search, {"search_hotels": "search_hotels", "error": "error"})
    workflow.add_conditional_edges("search_hotels", route_after_hotel_search, {"select_hotel": "select_hotel", "error": "error"})
    workflow.add_conditional_edges("select_hotel", route_after_hotel_selection, {"booking": "booking", "error": "error"})
    workflow.add_conditional_edges("booking", route_after_booking, {"end": END, "error": "error"})
    workflow.add_edge("error", END)
    
    return workflow.compile()

# ==================== 改进的交互模式 ====================
def interactive_demo():
    """交互式演示 - 改进版"""
    print("🤖 旅行规划 Agent 交互模式")
    print("=" * 60)
    print("🎯 支持的目的地: 北京、上海、广州、东京、新加坡、深圳、杭州、成都")
    print("📅 支持各种日期格式:")
    print("  - '明天去北京'")
    print("  - '下周一去上海'") 
    print("  - '2025-10-30 去广州'")
    print("  - '去深圳' (默认今天)")
    print("🏨 入住晚数: 1晚 到 5晚")
    print("输入 'quit' 或 '退出' 结束程序")
    print("=" * 60)
    
    agent = create_travel_agent()
    
    while True:
        user_input = input("\n🎯 请输入您的旅行需求: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '退出', 'q']:
            print("👋 感谢使用旅行规划 Agent，再见！")
            break
            
        if not user_input:
            print("⚠️  请输入有效的旅行需求")
            continue
        
        print("\n" + "=" * 60)
        print(f"📝 处理中: {user_input}")
        print("=" * 60)
        
        initial_state: TravelPlanningState = {
            "user_input": user_input,
            "guest_name": "", "destination": "", "travel_date": "", "nights": 0,
            "extracted_info": {}, "flights_result": None, "hotels_result": [],
            "selected_hotel": None, "booking_result": None, "current_step": "start",
            "error_message": None, "execution_log": []
        }
        
        try:
            final_state = agent.invoke(initial_state)
            
            print("\n" + "=" * 60)
            print("📊 执行结果总结:")
            print("=" * 60)
            
            if final_state["booking_result"]:
                booking = final_state["booking_result"]
                flight = final_state["flights_result"]
                hotel = final_state["selected_hotel"]
                
                flight_price = flight["price"] if flight else 0
                hotel_total = hotel["price_per_night"] * final_state["nights"] if hotel else 0
                total_cost = flight_price + hotel_total
                
                print(f"🎉 预订成功!")
                print(f"   📋 预订ID: {booking['booking_id']}")
                print(f"   ✈️  航班: {booking['flight_number']} - {flight_price}元")
                print(f"   🏨 酒店: {booking['hotel_name']} - {hotel_total}元")
                print(f"   👤 客人: {booking['guest_name']}")
                print(f"   💰 总费用: {total_cost}元")
                print(f"   📅 行程: {final_state['travel_date']} 起, {final_state['nights']}晚")
                print(f"   ⏰ 预订时间: {booking['timestamp']}")
                print(f"\n   💌 {booking['message']}")
            elif final_state["error_message"]:
                print(f"😞 {final_state['error_message']}")
                print("💡 建议：")
                print("   • 尝试调整旅行日期")
                print("   • 选择其他目的地")
                print("   • 稍后重试")
            else:
                print("⚠️  流程未完成，请重试")
            
            print(f"\n📝 执行日志:")
            for log in final_state["execution_log"]:
                print(f"   • {log}")
            
        except Exception as e:
            print(f"❌ 处理过程中出现错误: {e}")
            print("💡 请检查网络连接或稍后重试")
        
        print("=" * 60)
        print("\n")

if __name__ == "__main__":
    interactive_demo()
