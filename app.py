import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
from fpdf import FPDF

# --- ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="AI Timetable Final", layout="wide")

THAI_DAYS = {'Mon': 'จันทร์', 'Tue': 'อังคาร', 'Wed': 'พุธ', 'Thu': 'พฤหัสบดี', 'Fri': 'ศุกร์'}

# --- 1. ฟังก์ชันสร้าง PDF (แก้ไขปัญหา Bytearray) ---
def generate_pdf_bytes(df_filtered, title_val):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # ตั้งค่าฟอนต์
    font_name = "Arial"
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path, uni=True)
        font_name = "THSarabun"
    
    pdf.set_font(font_name, '', 16)
    pdf.cell(0, 10, f'Timetable Report: {title_val}', ln=True, align='C')
    pdf.ln(5)

    # วาดตาราง PDF
    pdf.set_font(font_name, '', 10)
    col_w = 22
    pdf.cell(20, 10, "Day/Period", border=1, align='C')
    for i in range(1, 13):
        pdf.cell(col_w, 10, str(i), border=1, align='C')
    pdf.ln()

    days_map = {'Mon': 'จันทร์', 'Tue': 'อังคาร', 'Wed': 'พุธ', 'Thu': 'พฤหัสบดี', 'Fri': 'ศุกร์'}
    for d_en, d_th in days_map.items():
        pdf.cell(20, 15, d_th if font_name == "THSarabun" else d_en, border=1, align='C')
        for p in range(1, 13):
            if p == 5:
                pdf.cell(col_w, 15, "-", border=1, align='C')
                continue
            match = df_filtered[(df_filtered['day'] == d_en) & (df_filtered['period'] == p)]
            if not match.empty:
                # แสดง รหัสวิชา / รหัสครู
                txt = f"{match.iloc[0]['subject_id']}\n{match.iloc[0]['teacher_id']}"
                x, y = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(col_w, 7.5, txt, border=1, align='C')
                pdf.set_xy(x + col_w, y)
            else:
                pdf.cell(col_w, 15, "", border=1, align='C')
        pdf.ln()
    
    # แปลงผลลัพธ์จาก bytearray เป็น bytes เพื่อแก้ปัญหา StreamlitAPIException
    return bytes(pdf.output())

# --- 2. ฟังก์ชันแสดงตารางหน้าเว็บ ---
def draw_web_table(df_filtered):
    days = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์']
    periods = list(range(1, 13))
    grid = pd.DataFrame("", index=days, columns=periods)
    
    df_filtered['day_th'] = df_filtered['day'].map(THAI_DAYS)
    for _, row in df_filtered.iterrows():
        content = f"<b>{row['subject_id']}</b><br>{row['teacher_id']}<br>{row['room_id']}"
        if row['day_th'] in days:
            grid.at[row['day_th'], row['period']] = content
    grid[5] = "พัก"

    rows_html = "".join([
        f"<tr><td style='background:#f1f3f6; font-weight:bold;'>{d}</td>" + 
        "".join([f"<td>{grid.at[d, p]}</td>" for p in periods]) + "</tr>"
        for d in days
    ])

    html_code = f"""
    <style>
        table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; table-layout: fixed; }}
        th {{ background: #2c3e50; color: white; padding: 5px; font-size: 11px; border: 1px solid #444; }}
        td {{ text-align: center; border: 1px solid #ddd; height: 50px; font-size: 10px; }}
    </style>
    <table>
        <thead><tr><th>วัน/คาบ</th>{"".join([f'<th>{p}</th>' for p in periods])}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """
    components.html(html_code, height=350)

# --- 3. UI MAIN ---
st.title("🖥️ AI Timetable Management System")

# เพิ่มปุ่มรัน AI (ถ้าต้องการ)
if st.sidebar.button("⚙️ รันการจัดตารางใหม่"):
    # ฟังก์ชัน run_scheduling_ai() ของคุณที่นี่
    st.sidebar.success("จัดตารางสำเร็จ")

if os.path.exists('output.csv'):
    main_df = pd.read_csv('output.csv')
    tab1, tab2, tab3 = st.tabs(["👥 รายกลุ่ม", "🏫 รายห้อง", "👨‍🏫 รายครู"])
    
    # ฟังก์ชันช่วยสร้างปุ่มดาวน์โหลดเพื่อลดโค้ดซ้ำซ้อน
    def download_section(df_part, unique_id):
        draw_web_table(df_part)
        # สร้าง PDF เฉพาะเมื่อผู้ใช้คลิกปุ่มเพื่อประหยัด RAM
        if st.button(f"📥 เตรียมไฟล์ PDF ({unique_id})", key=f"btn_{unique_id}"):
            with st.spinner("กำลังสร้าง PDF..."):
                pdf_data = generate_pdf_bytes(df_part, unique_id)
                st.download_button(
                    label="✅ คลิกเพื่อดาวน์โหลด",
                    data=pdf_data,
                    file_name=f"Timetable_{unique_id}.pdf",
                    mime="application/pdf",
                    key=f"dl_{unique_id}"
                )

    with tab1:
        sel_g = st.selectbox("เลือกกลุ่มเรียน:", sorted(main_df['group_id'].unique()), key="g_sel")
        download_section(main_df[main_df['group_id'] == sel_g], sel_g)

    with tab2:
        sel_r = st.selectbox("เลือกห้องเรียน:", sorted(main_df['room_id'].unique()), key="r_sel")
        download_section(main_df[main_df['room_id'] == sel_r], sel_r)

    with tab3:
        sel_t = st.selectbox("เลือกตามรหัสครู:", sorted(main_df['teacher_id'].unique()), key="t_sel")
        download_section(main_df[main_df['teacher_id'] == sel_t], sel_t)
else:
    st.warning("ไม่พบไฟล์ output.csv กรุณากดรันระบบที่เมนูด้านซ้าย")