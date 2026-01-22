import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
from fpdf import FPDF

# --- Configuration ---
st.set_page_config(page_title="AI Timetable with Time Slots", layout="wide")

THAI_DAYS = {'Mon': 'จันทร์', 'Tue': 'อังคาร', 'Wed': 'พุธ', 'Thu': 'พฤหัสบดี', 'Fri': 'ศุกร์'}
# กำหนดช่วงเวลา 12 คาบ
TIME_SLOTS = [
    "08.00-09.00", "09.00-10.00", "10.00-11.00", "11.00-12.00",
    "12.00-13.00", "13.00-14.00", "14.00-15.00", "15.00-16.00",
    "16.00-17.00", "17.00-18.00", "18.00-19.00", "19.00-20.00"
]

# --- 1. ฟังก์ชันสร้าง PDF พร้อมช่วงเวลา ---
def generate_pdf_bytes(df_filtered, title_val):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    font_name = "Arial"
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path, uni=True)
        font_name = "THSarabun"
    
    pdf.set_font(font_name, '', 16)
    pdf.cell(0, 10, f'Timetable Report: {title_val}', ln=True, align='C')
    pdf.ln(2)

    # วาด Header คาบและเวลา
    pdf.set_font(font_name, '', 8)
    col_w = 22
    pdf.cell(20, 12, "Day / Time", border=1, align='C')
    for i, t_slot in enumerate(TIME_SLOTS):
        # แสดง คาบที่ และ ช่วงเวลา
        x, y = pdf.get_x(), pdf.get_y()
        pdf.rect(x, y, col_w, 12)
        pdf.set_xy(x, y + 1)
        pdf.cell(col_w, 5, f'Period {i+1}', align='C')
        pdf.set_xy(x, y + 6)
        pdf.cell(col_w, 5, t_slot, align='C')
        pdf.set_xy(x + col_w, y)
    pdf.ln(12)

    # วาดข้อมูลรายวัน
    pdf.set_font(font_name, '', 10)
    days_map = {'Mon': 'จันทร์', 'Tue': 'อังคาร', 'Wed': 'พุธ', 'Thu': 'พฤหัสบดี', 'Fri': 'ศุกร์'}
    for d_en, d_th in days_map.items():
        pdf.cell(20, 15, d_th if font_name == "THSarabun" else d_en, border=1, align='C')
        for p in range(1, 13):
            if p == 5:
                pdf.cell(col_w, 15, "REST", border=1, align='C')
                continue
            match = df_filtered[(df_filtered['day'] == d_en) & (df_filtered['period'] == p)]
            if not match.empty:
                txt = f"{match.iloc[0]['subject_id']}\n{match.iloc[0]['teacher_id']}"
                x, y = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(col_w, 7.5, txt, border=1, align='C')
                pdf.set_xy(x + col_w, y)
            else:
                pdf.cell(col_w, 15, "", border=1, align='C')
        pdf.ln()
    
    return bytes(pdf.output())

# --- 2. ฟังก์ชันแสดงตารางหน้าเว็บพร้อมช่วงเวลา ---
def draw_web_table(df_filtered):
    days = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์']
    periods = list(range(1, 13))
    grid = pd.DataFrame("", index=days, columns=periods)
    
    df_filtered['day_th'] = df_filtered['day'].map(THAI_DAYS)
    for _, row in df_filtered.iterrows():
        content = f"<b>{row['subject_id']}</b><br>{row['teacher_id']}<br>{row['room_id']}"
        if row['day_th'] in days:
            grid.at[row['day_th'], row['period']] = content
    grid[5] = "🍴 พัก"

    # สร้าง Header HTML ที่มีเวลา
    header_html = "".join([
        f"<th><div style='font-size:9px; color:#bdc3c7;'>{t}</div>คาบ {p}</th>" 
        for p, t in zip(periods, TIME_SLOTS)
    ])

    rows_html = "".join([
        f"<tr><td style='background:#f1f3f6; font-weight:bold;'>{d}</td>" + 
        "".join([f"<td>{grid.at[d, p]}</td>" for p in periods]) + "</tr>"
        for d in days
    ])

    html_code = f"""
    <div style="overflow-x:auto;">
    <style>
        table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; table-layout: fixed; min-width: 1000px; }}
        th {{ background: #2c3e50; color: white; padding: 8px; font-size: 11px; border: 1px solid #444; }}
        td {{ text-align: center; border: 1px solid #ddd; height: 55px; font-size: 10px; line-height: 1.3; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
    </style>
    <table>
        <thead><tr><th style="width:80px;">วัน / เวลา</th>{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    </div>
    """
    components.html(html_code, height=400, scrolling=True)

# --- 3. UI MAIN ---
st.title("📅 AI Timetable (With Time Slots 08.00-20.00)")

if os.path.exists('output.csv'):
    main_df = pd.read_csv('output.csv')
    tab1, tab2, tab3 = st.tabs(["👥 รายกลุ่มเรียน", "🏫 รายห้องเรียน", "👨‍🏫 รายรหัสครู"])
    
    def display_section(df_part, unique_id):
        draw_web_table(df_part)
        if st.button(f"📥 สร้างไฟล์ PDF ({unique_id})", key=f"btn_{unique_id}"):
            with st.spinner("กำลังเตรียมไฟล์ PDF..."):
                pdf_data = generate_pdf_bytes(df_part, unique_id)
                st.download_button(
                    label="✅ คลิกเพื่อดาวน์โหลด PDF",
                    data=pdf_data,
                    file_name=f"Timetable_{unique_id}.pdf",
                    mime="application/pdf",
                    key=f"dl_{unique_id}"
                )

    with tab1:
        sel_g = st.selectbox("เลือกกลุ่มเรียน:", sorted(main_df['group_id'].unique()), key="g_sel")
        display_section(main_df[main_df['group_id'] == sel_g], sel_g)
    with tab2:
        sel_r = st.selectbox("เลือกห้องเรียน:", sorted(main_df['room_id'].unique()), key="r_sel")
        display_section(main_df[main_df['room_id'] == sel_r], sel_r)
    with tab3:
        sel_t = st.selectbox("เลือกตามรหัสครู:", sorted(main_df['teacher_id'].unique()), key="t_sel")
        display_section(main_df[main_df['teacher_id'] == sel_t], sel_t)
else:
    st.info("กรุณารันการประมวลผลจัดตารางสอนก่อน")