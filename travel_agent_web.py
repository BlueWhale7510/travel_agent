import streamlit as st
import os
from typing import Dict, List, TypedDict, Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from datetime import datetime, timedelta
import re
import json
import random

# 页面配置
st.set_page_config(
    page_title="智能旅行规划助手",
    page_icon="✈️",
    layout="wide"
)

# 初始化 session state
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'execution_history' not in st.session_state:
    st.session_state.execution_history = []
if 'current_state' not in st.session_state:
    st.session_state.current_state = None

# ==================== 配置区域 ====================
DEEPSEEK_API_KEY = "sk-a837b9ca3a554fe792e55b6e966d759d"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

def get_llm():
    """获取 LLM 实例"""
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.1
    )

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

# ==================== 模拟 API 函数 ====================
def search_flights(destination: str, date: str) -> Optional[dict]:
    """查询指定日期飞往某地的航班信息"""
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
    
    if destination not in supported_destinations:
        return None
    
    random.seed(hash(date) % 1000)
    if random.random() < 0.2:
        return None
    
    flight_number = random.choice(supported_destinations[destination])
    base_prices = {
        "北京": 1200, "上海": 1100, "广州": 1000, 
        "东京": 3500, "新加坡": 3200, "深圳": 900,
        "杭州": 800, "成都": 950
    }
    
    base_price = base_prices.get(destination, 1500)
    price_variation = random.randint(-200, 200)
    price = base_price + price_variation
    
    departure_times = ["08:00", "10:30", "13:15", "16:45", "19:20", "22:00"]
    departure_time = random.choice(departure_times)
    
    return {
        "flight_number": flight_number,
        "price": price,
        "departure_time": departure_time,
        "airline": flight_number[:2]
    }

def search_hotels(destination: str, check_in_date: str, check_out_date: str) -> List[dict]:
    """根据地点和日期查询酒店"""
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

# ==================== 信息提取 ====================
# 在 travel_agent_web.py 中替换 extract_info_simple 函数

def extract_info_with_llm_web(user_input: str) -> dict:
    """使用 DeepSeek API 提取信息 - Web 版本"""
    try:
        llm = get_llm()
        
        # 获取当前日期作为参考
        today = datetime.now()
        
        prompt = f"""
        请从以下用户输入中精确提取旅行规划的关键信息：
        
        用户输入: "{user_input}"
        
        今天是 {today.strftime('%Y-%m-%d')}，请根据这个参考日期计算相对日期。
        "下周三"指的是 {today.year}年{today.month}月{today.day}日 之后的第一个星期三。
        
        请提取以下信息：
        1. 目的地 (destination) - 如：北京、上海、广州、东京、新加坡、深圳、杭州、成都等
        2. 旅行日期 (travel_date) - 格式必须为：YYYY-MM-DD
        3. 入住晚数 (nights) - 数字
        4. 客人姓名 (guest_name) - 只提取姓名，不要包含标点符号
        
        重要规则：
        - 如果用户说"下周三"，请计算具体的日期
        - 姓名只提取中文名字，不要包含逗号等标点
        - 如果信息不完整，请使用合理的默认值
        
        请严格按照以下JSON格式返回：
        {{
            "destination": "目的地",
            "travel_date": "YYYY-MM-DD", 
            "nights": 2,
            "guest_name": "姓名"
        }}
        """
        
        response = llm.invoke(prompt)
        st.write(f"🤖 DeepSeek 解析结果: {response.content}")
        
        # 尝试解析 JSON 响应
        try:
            # 从响应中提取 JSON
            json_match = re.search(r'\{[^}]*\}', response.content)
            if json_match:
                extracted_info = json.loads(json_match.group())
                
                # 清理姓名中的标点符号
                if 'guest_name' in extracted_info:
                    extracted_info['guest_name'] = re.sub(r'[，。！？、；]', '', extracted_info['guest_name'])
                
                # 验证必要字段
                required_fields = ["destination", "travel_date", "nights", "guest_name"]
                for field in required_fields:
                    if field not in extracted_info:
                        if field == "nights":
                            extracted_info[field] = 2
                        elif field == "travel_date":
                            extracted_info[field] = today.strftime("%Y-%m-%d")
                        elif field == "destination":
                            extracted_info[field] = "北京"
                        elif field == "guest_name":
                            extracted_info[field] = "游客"
                
                return extracted_info
        except json.JSONDecodeError as e:
            st.warning(f"JSON 解析失败，使用备用方案: {e}")
        
        # 如果解析失败，使用改进的简单规则
        return extract_info_simple_improved(user_input)
        
    except Exception as e:
        st.error(f"DeepSeek API 调用失败: {e}")
        return extract_info_simple_improved(user_input)

def extract_info_simple_improved(user_input: str) -> dict:
    """改进的简化版信息提取"""
    # 获取当前日期作为默认
    today = datetime.now()
    
    extracted_info = {
        "destination": "北京",
        "travel_date": today.strftime("%Y-%m-%d"),
        "nights": 2,
        "guest_name": "游客"
    }
    
    # 目的地提取
    destinations = ["北京", "上海", "广州", "东京", "新加坡", "深圳", "杭州", "成都"]
    for dest in destinations:
        if dest in user_input:
            extracted_info["destination"] = dest
            break
    
    # 日期计算 - 处理"下周三"等相对日期
    if "下周三" in user_input:
        # 计算下周三的日期
        days_until_wednesday = (2 - today.weekday() + 7) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7  # 如果今天是周三，下周三就是7天后
        next_wednesday = today + timedelta(days=days_until_wednesday)
        extracted_info["travel_date"] = next_wednesday.strftime("%Y-%m-%d")
    elif "下周一" in user_input:
        days_until_monday = (0 - today.weekday() + 7) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        extracted_info["travel_date"] = next_monday.strftime("%Y-%m-%d")
    elif "明天" in user_input:
        tomorrow = today + timedelta(days=1)
        extracted_info["travel_date"] = tomorrow.strftime("%Y-%m-%d")
    
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
    
    # 姓名提取 - 改进版，清理标点符号
    name_patterns = [
        r'我是(\S{2,4})[，。！？]', r'我叫(\S{2,4})[，。！？]', 
        r'姓名(\S{2,4})[，。！？]', r'名字是(\S{2,4})[，。！？]',
        r'我是(\S{2,4})\s', r'我叫(\S{2,4})\s', r'姓名(\S{2,4})\s'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, user_input)
        if match:
            name = match.group(1)
            if name and len(name) >= 2:
                # 清理姓名中的标点符号
                name = re.sub(r'[，。！？、；]', '', name)
                extracted_info["guest_name"] = name
                break
    
    # 如果没有找到姓名，尝试更宽松的匹配
    if extracted_info["guest_name"] == "游客":
        name_match = re.search(r'我是(\S{2,4})|我叫(\S{2,4})|姓名(\S{2,4})', user_input)
        if name_match:
            name = name_match.group(1) or name_match.group(2) or name_match.group(3)
            if name and len(name) >= 2:
                name = re.sub(r'[，。！？、；]', '', name)
                extracted_info["guest_name"] = name
    
    return extracted_info

# ==================== 工具节点 ====================
def extract_information_node(state: TravelPlanningState) -> TravelPlanningState:
    """信息提取节点"""
    user_input = state["user_input"]
    
    # 使用改进的信息提取
    extracted_info = extract_info_with_llm_web(user_input)
    
    state["extracted_info"] = extracted_info
    state["destination"] = extracted_info["destination"]
    state["travel_date"] = extracted_info["travel_date"] 
    state["nights"] = extracted_info["nights"]
    state["guest_name"] = extracted_info["guest_name"]
    state["current_step"] = "information_extracted"
    state["execution_log"].append("✅ 用户需求信息提取完成")
    
    return state

def search_flights_node(state: TravelPlanningState) -> TravelPlanningState:
    """查询航班节点"""
    flights_result = search_flights(state["destination"], state["travel_date"])
    state["flights_result"] = flights_result
    
    if flights_result:
        state["current_step"] = "flights_found"
        state["execution_log"].append(f"✅ 找到航班: {flights_result['flight_number']}")
    else:
        state["current_step"] = "flights_not_found"
        state["error_message"] = f"抱歉，{state['travel_date']} 前往 {state['destination']} 的航班已售罄或暂无航班"
        state["execution_log"].append("❌ 未找到合适航班")
    
    return state

def search_hotels_node(state: TravelPlanningState) -> TravelPlanningState:
    """查询酒店节点"""
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
    else:
        state["current_step"] = "hotels_not_found"
        state["error_message"] = f"抱歉，未找到 {state['destination']} 的可用酒店"
        state["execution_log"].append("❌ 未找到合适酒店")
    
    return state

def select_hotel_node(state: TravelPlanningState) -> TravelPlanningState:
    """选择酒店节点"""
    if not state["hotels_result"]:
        state["error_message"] = "无法选择酒店：未找到可用酒店"
        state["current_step"] = "error"
        return state
    
    hotels = state["hotels_result"]
    best_hotel = None
    best_score = 0
    
    for hotel in hotels:
        value_score = (hotel.get("rating", 4.0) * 100) / hotel["price_per_night"]
        if value_score > best_score:
            best_score = value_score
            best_hotel = hotel
    
    state["selected_hotel"] = best_hotel
    state["current_step"] = "hotel_selected"
    state["execution_log"].append(f"✅ 已选择酒店: {best_hotel['name']}")
    
    return state

def booking_node(state: TravelPlanningState) -> TravelPlanningState:
    """预订节点"""
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
    
    return state

def error_handling_node(state: TravelPlanningState) -> TravelPlanningState:
    """错误处理节点"""
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

# ==================== Streamlit 界面 ====================
def main():
    # 侧边栏
    with st.sidebar:
        st.title("🔧 设置")
        st.info("使用 DeepSeek API 进行智能旅行规划")
        
        st.subheader("使用说明")
        st.markdown("""
        **支持的目的地:**
        - 北京、上海、广州
        - 东京、新加坡
        - 深圳、杭州、成都
        
        **输入示例:**
        - 我想去北京玩3天，我叫张三
        - 预订上海2晚酒店，姓名李四
        - 明天去广州，住一晚
        """)
    
    # 主界面
    st.title("✈️ 智能旅行规划助手")
    st.markdown("基于 LangGraph 和 DeepSeek AI 的智能旅行规划系统")
    
    # 初始化 Agent
    if st.session_state.agent is None:
        st.session_state.agent = create_travel_agent()
    
    # 输入区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        user_input = st.text_area(
            "🎯 请输入您的旅行需求:",
            placeholder="例如：我想预订去北京的机票和酒店，住3晚，我叫张三",
            height=100
        )
    
    with col2:
        st.markdown("### 快速模板")
        templates = {
            "北京3日游": "我想去北京玩3天，住两晚，我叫王伟",
            "上海商务行": "预订上海2晚酒店，明天出发，姓名李华",
            "广州周末游": "周末去广州，住一晚，名字张三"
        }
        
        for name, template in templates.items():
            if st.button(name):
                user_input = template
    
    # 处理按钮
    if st.button("🚀 开始规划", type="primary", use_container_width=True):
        if not user_input.strip():
            st.error("请输入旅行需求")
            return
        
        # 清空历史记录
        st.session_state.execution_history = []
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 初始化状态
        initial_state: TravelPlanningState = {
            "user_input": user_input,
            "guest_name": "", "destination": "", "travel_date": "", "nights": 0,
            "extracted_info": {}, "flights_result": None, "hotels_result": [],
            "selected_hotel": None, "booking_result": None, "current_step": "start",
            "error_message": None, "execution_log": []
        }
        
        # 执行 Agent
        try:
            # 步骤1: 信息提取
            status_text.text("📍 步骤1: 提取用户需求信息...")
            state = st.session_state.agent.invoke(initial_state)
            progress_bar.progress(20)
            
            # 显示提取的信息
            with st.expander("📋 提取的旅行信息", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("目的地", state["destination"])
                with col2:
                    st.metric("旅行日期", state["travel_date"])
                with col3:
                    st.metric("入住晚数", f"{state['nights']}晚")
                with col4:
                    st.metric("客人姓名", state["guest_name"])
            
            # 步骤2: 查询航班
            status_text.text("📍 步骤2: 查询航班...")
            state = st.session_state.agent.invoke(state)
            progress_bar.progress(40)
            
            if state["flights_result"]:
                flight = state["flights_result"]
                with st.expander("✈️ 航班信息", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("航班号", flight["flight_number"])
                    with col2:
                        st.metric("价格", f"¥{flight['price']}")
                    with col3:
                        st.metric("起飞时间", flight["departure_time"])
                    with col4:
                        st.metric("航空公司", flight["airline"])
            else:
                st.error("❌ 未找到合适航班")
                progress_bar.progress(100)
                return
            
            # 步骤3: 查询酒店
            status_text.text("📍 步骤3: 查询酒店...")
            state = st.session_state.agent.invoke(state)
            progress_bar.progress(60)
            
            if state["hotels_result"]:
                with st.expander("🏨 可选酒店", expanded=True):
                    for i, hotel in enumerate(state["hotels_result"], 1):
                        total_price = hotel["price_per_night"] * state["nights"]
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{hotel['name']}**")
                            st.write(f"评分: {hotel['rating']} ⭐")
                        with col2:
                            st.write(f"¥{hotel['price_per_night']}/晚")
                        with col3:
                            st.write(f"总计: ¥{total_price}")
                        st.divider()
            else:
                st.error("❌ 未找到合适酒店")
                progress_bar.progress(100)
                return
            
            # 步骤4: 选择酒店
            status_text.text("📍 步骤4: 智能选择酒店...")
            state = st.session_state.agent.invoke(state)
            progress_bar.progress(80)
            
            if state["selected_hotel"]:
                hotel = state["selected_hotel"]
                total_price = hotel["price_per_night"] * state["nights"]
                with st.expander("🎯 智能选择的酒店", expanded=True):
                    st.success(f"**{hotel['name']}**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("评分", f"{hotel['rating']} ⭐")
                    with col2:
                        st.metric("每晚价格", f"¥{hotel['price_per_night']}")
                    with col3:
                        st.metric("总价", f"¥{total_price}")
            
            # 步骤5: 执行预订
            status_text.text("📍 步骤5: 执行预订...")
            state = st.session_state.agent.invoke(state)
            progress_bar.progress(100)
            
            if state["booking_result"]:
                booking = state["booking_result"]
                flight = state["flights_result"]
                hotel = state["selected_hotel"]
                
                flight_price = flight["price"]
                hotel_total = hotel["price_per_night"] * state["nights"]
                total_cost = flight_price + hotel_total
                
                # 显示最终结果
                st.success("🎉 预订成功！")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 预订详情")
                    st.info(f"**预订ID:** {booking['booking_id']}")
                    st.info(f"**客人:** {booking['guest_name']}")
                    st.info(f"**行程:** {state['travel_date']} 起, {state['nights']}晚")
                    st.info(f"**预订时间:** {booking['timestamp']}")
                
                with col2:
                    st.subheader("💰 费用明细")
                    st.info(f"**机票:** ¥{flight_price}")
                    st.info(f"**酒店:** ¥{hotel_total}")
                    st.info(f"**总计:** ¥{total_cost}")
                
                st.balloons()
                
            else:
                st.error(f"❌ {state['error_message']}")
        
        except Exception as e:
            st.error(f"处理过程中出现错误: {e}")
        
        finally:
            status_text.text("完成")
    
    # 显示执行日志
    if st.session_state.execution_history:
        with st.expander("📝 执行日志"):
            for log in st.session_state.execution_history:
                st.write(log)

if __name__ == "__main__":
    main()