import requests
import re
import datetime
import os

# ================= 配置区域 =================
# 读取 GitHub 的保密配置
# 从环境变量获取 Key 字符串 (SCT_A,SCT_B,SCT_C)
KEYS_STR = os.getenv("SERVERCHAN_KEY", "")

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

                # --- 【排版优化】改为清单格式 ---
                # 汇率不需要显示涨跌幅，其他需要
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
    
    # 使用 \n\n 强制换行，让手机显示更舒服
    content = f"📅 {time_str}\n\n" + "\n\n".join(results)
    
    return title, content

def push_to_wechat(title, content):
    if not KEYS_STR:
        print("⚠️ 未配置 Key")
        return
    
    # 【核心修改】分割 Key 并循环发送
    keys = KEYS_STR.split(",")
    for key in keys:
        key = key.strip() # 去除可能误填的空格
        if not key: continue
        
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": title, "desp": content}
        try:
            requests.post(url, data=data)
            print(f"✅ 已推送给: ...{key[-4:]}")
        except Exception as e:
            print(f"❌ 推送失败 ({key[-4:]}): {e}")

if __name__ == "__main__":
    title, content = get_sina_data(TARGETS)
    print("--- 预览 ---")
    print(title)
    print(content)
    print("-----------")
    push_to_wechat(title, content)
