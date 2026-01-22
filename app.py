import streamlit as st
import pandas as pd
import random
import io

# --- 1. UI Setup & CSS ---
st.set_page_config(page_title="ระบบจัดตารางเรียน AI Pro", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        body { font-family: 'Sarabun', sans-serif; }
        
        .schedule-title { 
            background: #ffffff; padding: 20px; border-radius: 10px; border-left: 8px solid #0047AB; 
            margin-bottom: 20px; font-weight: bold; font-size: 24px; text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .custom-table { width: 100%; border-collapse: collapse; background: white; table-layout: fixed; }
        .custom-table th, .custom-table td { 
            border: 1px solid #dee2e6; padding: 5px; text-align: center; 
            height: 100px; vertical-align: middle; word-wrap: break-word;
        }
        
        /* ปรับขนาด Font ลง 2pt จากตัวใหญ่เดิม */
        .custom-table th { background-color: #f8f9fa; font-weight: bold; border-bottom: 3px solid #0047AB; font-size: 15px; }
        .day-col { color: #0047AB; font-weight: bold; background-color: #f1f3f9; width: 75px !important; font-size: 14px; }
        
        .main-info { font-weight: bold; display: block; color: #212529; font-size: 15px; margin-bottom: 3px; }
        .sub-info-blue { color: #0047AB; display: block; font-size: 14px; font-weight: bold; line-height: 1.2; }
        .sub-info-grey { color: #6c757d; display: block; font-size: 13px; }
        
        .type-theory { background-color: #E3F2FD !important; }
        .type-practice { background-color: #E8F5E9 !important; }
        .type-both { background-color: #FFF3E0 !important; }

        /* ส่วนสรุปขนาดเล็ก */
        .summary-bar {
            display: flex; justify-content: flex-end; gap: 20px;
            background: #fdfdfd; padding: 8px 15px; border-radius: 6px;
            border: 1px solid #eee; margin-top: 10px;
        }
        .sum-item { font-size: 13px; color: #555; }
        .sum-val { font-size: 16px; font-weight: bold; color: #0047AB; margin-left: 4px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Safe Data Loader ---
def load_data():
    files = ['teacher.csv', 'room.csv', 'student_group.csv', 'subject.csv', 'timeslot.csv', 'teach.csv', 'register.csv']
    data = {}
    try:
        for f in files:
            df = pd.read_csv(f)
            df.columns = df.columns.str.strip()
            for c in df.columns:
                df[c] = df[c].astype(str).replace('nan', '').str.strip()
            data[f.replace('.csv', '')] = df
        return data
    except Exception as e:
        st.error(f"ไม่พบไฟล์หรือข้อมูลผิดพลาด: {e}")
        return None

# --- 3. Scheduler Engine ---
def scheduler_engine(data):
    results = []
    busy_t, busy_r, busy_g = set(), set(), set()
    all_slots = data['timeslot'].copy()
    all_slots['period'] = pd.to_numeric(all_slots['period'], errors='coerce')
    primary = all_slots[(all_slots['period'] >= 1) & (all_slots['period'] <= 10) & (all_slots['period'] != 5)].to_dict('records')
    secondary = all_slots[(all_slots['period'] > 10)].to_dict('records')

    for _, reg in data['register'].iterrows():
        sid, gid = reg['subject_id'], reg['group_id']
        sub_match = data['subject'][data['subject']['subject_id'] == sid]
        if sub_match.empty: continue
        th, pr = int(float(sub_match.iloc[0].get('theory', 0))), int(float(sub_match.iloc[0].get('practice', 0)))
        needed = th + pr
        teach_match = data['teach'][data['teach']['subject_id'] == sid]
        tid = teach_match.iloc[0]['teacher_id'] if not teach_match.empty else None
        if not tid: continue
        
        placed = 0
        random.shuffle(primary)
        for slot in (primary + secondary):
            if placed >= needed: break
            tsid, day, period = slot['timeslot_id'], slot['day'], int(slot['period'])
            if (tid, tsid) in busy_t or (gid, tsid) in busy_g: continue
            for _, rm in data['room'].iterrows():
                rid = rm['room_id']
                if (rid, tsid) not in busy_r:
                    results.append({'group_id': gid, 'timeslot_id': tsid, 'day': day, 'period': period, 'subject_id': sid, 'teacher_id': tid, 'room_id': rid})
                    busy_t.add((tid, tsid)); busy_r.add((rid, tsid)); busy_g.add((gid, tsid))
                    placed += 1; break
    return pd.DataFrame(results)

# --- 4. Main App Logic ---
data_set = load_data()
if data_set:
    t_df = data_set['teacher'].copy()
    def get_safe(df, col): return df[col] if col in df.columns else pd.Series([''] * len(df))
    t_df['full_name'] = (get_safe(t_df, 'prefix') + " " + get_safe(t_df, 'firstname') + " " + get_safe(t_df, 'lastname')).str.strip()
    
    teacher_map = {str(row['teacher_id']): f"[{row['teacher_id']}] {row['full_name']}" for _, row in t_df.iterrows()}
    room_map = dict(zip(data_set['room']['room_id'], data_set['room']['room_name']))
    group_map = dict(zip(data_set['student_group']['group_id'], data_set['student_group']['group_name']))
    subject_info = data_set['subject'].set_index('subject_id').to_dict('index')

    with st.sidebar:
        st.header("⚙️ เมนูควบคุม")
        if st.button("🚀 ประมวลผลตารางใหม่", use_container_width=True):
            st.session_state.schedule_result = scheduler_engine(data_set)
        
        if 'schedule_result' in st.session_state:
            st.divider()
            view_mode = st.radio("มุมมอง", ["ตามกลุ่มเรียน", "ตามครูผู้สอน", "ตามห้องเรียน"])
            ref_map = group_map if view_mode == "ตามกลุ่มเรียน" else teacher_map if view_mode == "ตามครูผู้สอน" else room_map
            selected = st.selectbox(f"เลือก", options=list(ref_map.keys()), format_func=lambda x: ref_map.get(x, x))

    # --- 5. Rendering Table & Summary ---
    if 'schedule_result' in st.session_state and selected:
        f_res = st.session_state.schedule_result
        col_id = 'group_id' if view_mode=="ตามกลุ่มเรียน" else 'teacher_id' if view_mode=="ตามครูผู้สอน" else 'room_id'
        current_data = f_res[f_res[col_id] == str(selected)]
        
        title_text = "ตารางเรียน" if view_mode == "ตามกลุ่มเรียน" else "ตารางสอนครู" if view_mode == "ตามครูผู้สอน" else "ตารางห้อง"
        st.markdown(f'<div class="schedule-title">{title_text} : {ref_map.get(selected)}</div>', unsafe_allow_html=True)

        # Legend
        st.markdown("""<div style="display:flex; gap:15px; justify-content:center; margin-bottom:10px; font-size:13px;">
            <div style="display:flex; align-items:center; gap:5px;"><div style="width:12px; height:12px; background:#E3F2FD; border:1px solid #ccc;"></div> ทฤษฎี</div>
            <div style="display:flex; align-items:center; gap:5px;"><div style="width:12px; height:12px; background:#E8F5E9; border:1px solid #ccc;"></div> ปฏิบัติ</div>
            <div style="display:flex; align-items:center; gap:5px;"><div style="width:12px; height:12px; background:#FFF3E0; border:1px solid #ccc;"></div> ทฤษฎี+ปฏิบัติ</div>
        </div>""", unsafe_allow_html=True)

        DAYS, D_MAP = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์"], {"Mon": "จันทร์", "Tue": "อังคาร", "Wed": "พุธ", "Thu": "พฤหัสบดี", "Fri": "ศุกร์"}
        PERIODS = ["", "1", "2", "3", "4", "พัก", "6", "7", "8", "9", "10", "11", "12"]
        TIME_LABELS = ["", "08.00-09.00", "09.00-10.00", "10.00-11.00", "11.00-12.00", "12.00-13.00", "13.00-14.00", "14.00-15.00", "15.00-16.00", "16.00-17.00", "17.00-18.00", "18.00-19.00", "19.00-20.00"]

        html = '<table class="custom-table"><thead><tr>'
        for p, t in zip(PERIODS, TIME_LABELS):
            label = f"คาบ {p}<br><small>{t}</small>" if p not in ["", "พัก"] else p
            html += f'<th>{label}</th>'
        html += '</tr></thead><tbody>'

        # คำนวณสรุป
        sum_th, sum_pr = 0.0, 0.0
        for _, row in current_data.iterrows():
            info = subject_info.get(str(row['subject_id']), {})
            t_h = float(info.get('theory', 0))
            p_h = float(info.get('practice', 0))
            if (t_h + p_h) > 0:
                sum_th += (t_h / (t_h + p_h))
                sum_pr += (p_h / (t_h + p_h))

        for d in DAYS:
            html += f'<tr><td class="day-col">{d}</td>'
            for p in PERIODS[1:]:
                if p == "พัก":
                    html += '<td style="background:#f8f9fa; color:#ccc; font-size:12px;">พัก</td>'
                else:
                    match = current_data[(current_data['day'].map(D_MAP) == d) & (current_data['period'].astype(str) == p)]
                    if not match.empty:
                        row = match.iloc[0]; sid = row['subject_id']
                        info = subject_info.get(str(sid), {})
                        th_v, pr_v = float(info.get('theory', 0)), float(info.get('practice', 0))
                        c_cls = "type-both" if th_v > 0 and pr_v > 0 else "type-theory" if th_v > 0 else "type-practice" if pr_v > 0 else ""
                        t_d = teacher_map.get(row['teacher_id'], row['teacher_id'])
                        r_n, g_n = room_map.get(row['room_id'], row['room_id']), group_map.get(row['group_id'], row['group_id'])
                        l1, l2, l3 = (sid, t_d, r_n) if view_mode == "ตามกลุ่มเรียน" else (sid, g_n, r_n) if view_mode == "ตามครูผู้สอน" else (sid, t_d, g_n)
                        html += f'<td class="{c_cls}"><span class="main-info">{l1}</span><span class="sub-info-blue">{l2}</span><span class="sub-info-grey">{l3}</span></td>'
                    else: html += '<td></td>'
            html += '</tr>'
        st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

        # สรุปผล Compact
       # --- 1. ปรับปรุง CSS สำหรับ Summary Bar ---
st.markdown("""
    <style>
        .summary-bar {
            display: flex; 
            justify-content: flex-end; 
            gap: 40px;
            background: #f8f9fa; 
            padding: 12px 30px; 
            border-radius: 8px;
            border: 1px solid #dee2e6; 
            margin-top: 15px;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
        }
        .sum-item { 
            font-size: 14px; 
            color: #555; 
            font-weight: bold;
            display: flex;
            align-items: center;
        }
        .sum-val { 
            font-size: 18px; 
            font-weight: bold; 
            color: #0047AB; 
            margin-left: 8px; 
        }
        .total-label { color: #D32F2F; }
        .total-val { color: #D32F2F; font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

# ... (ส่วนประมวลผลตารางคงเดิม) ...

# --- 5. Rendering Compact Summary ---
if 'schedule_result' in st.session_state and selected:
    # [ส่วนคำนวณตัวเลข sum_th, sum_pr, total]
    total_slots = len(current_data)
    
    # แสดงแถบสรุปผลแบบใหม่
    # --- 1. ปรับปรุง CSS สำหรับ Summary Bar (คงเดิมเพื่อความสวยงาม) ---
st.markdown("""
    <style>
        .summary-bar {
            display: flex; 
            justify-content: flex-end; 
            gap: 40px;
            background: #f8f9fa; 
            padding: 12px 30px; 
            border-radius: 8px;
            border: 1px solid #dee2e6; 
            margin-top: 15px;
        }
        .sum-item { 
            font-size: 15px; 
            color: #444; 
            font-weight: bold;
            display: flex;
            align-items: center;
        }
        .sum-val { 
            font-size: 18px; 
            font-weight: bold; 
            color: #0047AB; 
            margin-left: 8px;
            margin-right: 4px;
        }
        .unit { font-size: 14px; color: #666; font-weight: normal; }
        .total-label { color: #D32F2F; }
        .total-val { color: #D32F2F; font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

# ... (ส่วนประมวลผลตารางคงเดิม) ...

# --- 5. Rendering Compact Summary (ตัดทศนิยม + เพิ่มหน่วย) ---
if 'schedule_result' in st.session_state and selected:
    # คำนวณยอดรวม (ใช้ int() เพื่อตัดทศนิยมออก)
    display_th = int(round(sum_th))
    display_pr = int(round(sum_pr))
    total_slots = len(current_data)
    
    # แสดงแถบสรุปผล
    st.markdown(f"""
        <div class="summary-bar">
            <div class="sum-item">ทฤษฎี: <span class="sum-val">{display_th}</span> <span class="unit">คาบ</span></div>
            <div class="sum-item">ปฏิบัติ: <span class="sum-val">{display_pr}</span> <span class="unit">คาบ</span></div>
            <div class="sum-item" style="border-left: 2px solid #ddd; padding-left: 30px;">
                <span class="total-label">รวม:</span> 
                <span class="sum-val total-val">{total_slots}</span> 
                <span class="total-label" style="font-size:14px; font-weight:normal;">คาบ</span>
            </div>
        </div>
    """, unsafe_allow_html=True)