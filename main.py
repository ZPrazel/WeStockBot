import requests
import re
import datetime
import os

# ================= 配置区域 =================
# 读取 GitHub 的保密配置
KEYS_STR = os.getenv("SERVERCHAN_KEY", "")
# 【新增】读取 DeepSeek 的 API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

TARGETS = {
    "美股纳指": {"code": "gb_ixic", "type": "us"},
    "标普500":  {"code": "gb_inx",  "type": "us"},
    "港股恒指": {"code": "rt_hkHSI", "type": "hk"},
    "美元/人民币": {"code": "fx_susdcny", "type": "fx"},
    "黄金期货": {"code": "hf_GC", "type": "future"},
    "白银期货": {"code": "hf_SI", "type": "future"},
    "铜期货":   {"code": "hf_HG", "type": "future"},
}

def get_sina_data(targets):
    codes = [item['code'] for item in targets.values()]
    url = f"http://hq.sinajs.cn/list={','.join(codes)}"
    headers = {"Referer": "https://finance.sina.com.cn/"}

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        text = resp.text
    except Exception as e:
        return "获取失败", str(e)

    results = []
    main_title_info = ""

    for name, config in targets.items():
        pattern = f'var hq_str_{config["code"]}="(.*?)";'
        match = re.search(pattern, text)
        
        if match:
            data_str = match.group(1)
            parts = data_str.split(',')
            try:
                price, change_pct = 0.0, 0.0
                
                # --- 解析逻辑 ---
                if config['type'] == 'us':
                    price = float(parts[1])
                    change_pct = float(parts[2])
                elif config['type'] == 'hk':
                    price = float(parts[6])
                    change_pct = float(parts[8])
                elif config['type'] == 'future':
                    price = float(parts[0])
                    prev_close = float(parts[7])
                    if prev_close > 0:
                        change_pct = ((price - prev_close) / prev_close) * 100
                elif config['type'] == 'fx':
                    price = float(parts[1])
                    change_pct = 0.0 

                # --- 图标逻辑 ---
                if change_pct > 0:
                    icon, sign = "🔴", "+"
                elif change_pct < 0:
                    icon, sign = "🟢", ""
                else:
                    icon, sign = "⚪", ""

                # --- 排版优化 ---
                if name == "美元/人民币":
                     line = f"{icon} **{name}**: {price:.4f}"
                else:
                     line = f"{icon} **{name}**: {price:,.2f} ({sign}{change_pct:.2f}%)"
                
                # 收集标题信息
                if name == "美股纳指":
                    main_title_info += f"纳指 {sign}{change_pct:.2f}%"
                if name == "美元/人民币":
                    main_title_info += f" | 汇率 {price:.2f}"
                    
            except:
                line = f"⚪ **{name}**: 解析出错"
        else:
            line = f"⚪ **{name}**: 无数据"
            
        results.append(line)

    time_str = datetime.datetime.now().strftime("%m-%d %H:%M")
    title = f"盘前: {main_title_info}"
    
    content = f"📅 {time_str}\n\n" + "\n\n".join(results)
    
    return title, content

# ================= 新增：大模型“狗屁分析”大脑 =================
def get_ai_analysis(market_data):
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。"

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    # 这里的 Prompt 就是所谓的 Vibe-coding 灵魂
    prompt = f"""
    你是一位华尔街资深量化对冲基金经理。请根据以下我抓取的最新的全球市场盘前数据，
    写一段60字左右的晨间市场情绪总结和宏观风险提示。
    要求：语气冷酷、专业、充满华尔街精英感，直接给结论，不要废话，不要免责声明。
    
    【盘前数据】
    {market_data}
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个无情的宏观交易分析机器。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7, # 稍微加点温度，让“狗屁分析”更具玄学色彩
        "max_tokens": 150
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        ai_text = response.json()['choices'][0]['message']['content'].strip()
        return f"🤖 **【Agent 晨间研判】**\n\n{ai_text}"
    except Exception as e:
        return f"🤖 AI 分析生成失败: {str(e)}"

# ==============================================================

def push_to_wechat(title, content):
    if not KEYS_STR:
        print("⚠️ 未配置 Server酱 Key")
        return
    
    keys = KEYS_STR.split(",")
    for key in keys:
        key = key.strip()
        if not key: continue
        
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": title, "desp": content}
        try:
            requests.post(url, data=data)
            print(f"✅ 已推送给: ...{key[-4:]}")
        except Exception as e:
            print(f"❌ 推送失败 ({key[-4:]}): {e}")

if __name__ == "__main__":
    # 1. 抓取数据
    title, content = get_sina_data(TARGETS)
    
    # 2. 调用大模型大脑进行分析
    print("⏳ 正在请求 DeepSeek 大脑进行推演...")
    ai_analysis = get_ai_analysis(content)
    
    # 3. 拼装最终推文
    final_content = f"{content}\n\n---\n\n{ai_analysis}"

    print("--- 预览 ---")
    print(title)
    print(final_content)
    print("-----------")
    
    # 4. 推送
    push_to_wechat(title, final_content)
