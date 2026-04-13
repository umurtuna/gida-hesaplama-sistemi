import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="COA Works ERP V15", layout="wide")

# 2. ŞİFRE SİSTEMİ
ERISIM_SIFRESI = "NMR170"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 COA Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password", key="v15_login")
    if st.button("Giriş", key="v15_login_btn"):
        if s == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 3. VERİ YÜKLEME (GID TABANLI)
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

def verileri_yukle():
    data_yapisi = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- MALZEMELER (GID 0) ---
    try:
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None and not m_df.empty:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in m_df.columns:
                    m_df[col] = m_df[col].astype(str).str.replace(',', '.', regex=False)
                    m_df[col] = pd.to_numeric(m_df[col], errors='coerce').fillna(0)
            data_yapisi["malzemeler"] = m_df.set_index("ad").to_dict('index')
    except: pass

    # --- REÇETELER (GID 2130732789) ---
    try:
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None and not r_df.empty:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            r_df["miktar_g"] = r_df["miktar_g"].astype(str).str.replace(',', '.', regex=False)
            r_df["miktar_g"] = pd.to_numeric(r_df["miktar_g"], errors='coerce').fillna(0)
            data_yapisi["receteler_tablo"] = r_df
    except: pass

    # --- KURLAR (GID 1768374636) ---
    try:
        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None and not k_df.empty:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            k_df["oran"] = k_df["oran"].astype(str).str.replace(',', '.', regex=False)
            k_df["oran"] = pd.to_numeric(k_df["oran"], errors='coerce').fillna(1.0)
            data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
    except: pass

    return data_yapisi

data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
besin_etiketleri = {"enerji": "Enerji", "yag": "Yağ", "karb": "Karb.", "seker": "Şeker", "lif": "Lif", "protein": "Prot.", "tuz": "Tuz"}

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    df = df.copy()
    df["Miktar (g)"] = pd.to_numeric(df["Miktar (g)"], errors='coerce').fillna(0.0)
    t_gram = df["Miktar (g)"].sum()
    
    if t_gram == 0: return analiz, 0
    
    for _, row in df.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        miktar = float(row["Miktar (g)"])
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = miktar / 100
            for b in besin_kalemleri:
                analiz[b] += float(m.get(b, 0)) * oran
            # Kur hesabı
            kur = float(kurlar.get(str(m.get("birim", "TRY")).upper(), 1.0))
            analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
    return analiz, t_gram

# 5. MENÜ
st.sidebar.title("COA Works ERP")
if st.sidebar.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("İşlem Seçin", ["📦 Envanter", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

# --- ENVANTER ---
if menu == "📦 Envanter":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else: st.error("Envanter yüklenemedi.")

# --- REÇETE HAZIRLA ---
elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if not data["malzemeler"]: st.error("Envanter boş.")
    else:
        if 'gecici_v15' not in st.session_state:
            st.session_state.gecici_v15 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
        
        c1, c2 = st.columns([3, 1])
        m_sec = c1.selectbox("Malzeme Seç", sorted(data["malzemeler"].keys()), key="v15_sel")
        if c2.button("➕ Ekle", key="v15_add"):
            st.session_state.gecici_v15 = pd.concat([st.session_state.gecici_v15, pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])], ignore_index=True)
        
        edit_df = st.data_editor(st.session_state.gecici_v15, num_rows="dynamic", use_container_width=True, key="v15_editor")
        st.session_state.gecici_v15 = edit_df
        
        if not edit_df.empty:
            res, tg = besin_analizi_yap(edit_df, data["malzemeler"], data["kurlar"])
            if tg > 0:
                st.divider()
                st.subheader(f"📊 Analiz ({tg:.1f}g)")
                cols = st.columns(len(besin_kalemleri))
                for i, b in enumerate(besin_kalemleri):
                    cols[i].metric(besin_etiketleri[b], f"{res[b]/(tg/100):.2f}")
                st.metric("💰 KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")

                st.divider()
                # Dinamik İsim Güncelleme Çözümü
                r_isim = st.text_input("Reçete Adı (İsim girdikten sonra Enter'a basın):", "yeni_ürün", key="v15_name")
                tablo_metni = ""
                for _, row in edit_df.iterrows():
                    if str(row['Malzeme']).strip():
                        m_str = str(row['Miktar (g)']).replace('.', ',')
                        tablo_metni += f"{r_isim}\t{row['Malzeme']}\t{m_str}\n"
                st.text_area("Excel'e Yapıştır (Hücrelere tam oturur):", tablo_metni, height=150, key="v15_copy")

# --- KATMANLI ÜRÜN ---
elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Katmanlı Ürün Analizi")
    if data["receteler_tablo"].empty: st.warning("Excel 'receteler' sayfasını kontrol edin (GID: 2130732789).")
    else:
        k_sayisi = st.number_input("Katman Sayısı", 1, 5, 2, key="v15_k_count")
        recete_list = sorted(data["receteler_tablo"]["recete_ad"].unique())
        katmanlar = []
        t_oran = 0.0
        cols = st.columns(int(k_sayisi))
        for i in range(int(k_sayisi)):
            with cols[i]:
                k_ad = st.selectbox(f"Reçete {i+1}", recete_list, key=f"v15_k_sel_{i}")
                k_o = st.number_input(f"Oran %", 0.0, 100.0, key=f"v15_k_ora_{i}")
                katmanlar.append({"ad": k_ad, "oran": k_o})
                t_oran += k_o
        
        if abs(t_oran - 100) < 0.1:
            if st.button("🧬 Analiz Yap"):
                final = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
                for k in katmanlar:
                    r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == k["ad"]].copy()
                    r_df = r_df.rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                    r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                    if r_tg > 0:
                        pay = k["oran"] / 100
                        for b in besin_kalemleri: final[b] += (r_res[b] / (r_tg / 100)) * pay
                        final["maliyet"] += (r_res["maliyet"] / (r_tg / 1000)) * pay
                st.table(pd.DataFrame({besin_etiketleri[k]: [round(final[k], 2)] for k in besin_kalemleri}))
                st.metric("Final KG Maliyeti", f"{final['maliyet']:.2f} TL")
        else: st.error(f"Toplam oran %100 olmalı (Şu an: %{t_oran})")

# --- ARŞİV ---
elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        rec_list = sorted(data["receteler_tablo"]["recete_ad"].unique())
        secilen = st.selectbox("Reçete Seç", rec_list)
        arsiv_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == secilen].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.dataframe(arsiv_df[["Malzeme", "Miktar (g)"]], use_container_width=True)
        res, tg = besin_analizi_yap(arsiv_df, data["malzemeler"], data["kurlar"])
        if tg > 0:
            st.subheader("Besin Analizi (100g)")
            cols = st.columns(len(besin_kalemleri))
            for i, b in enumerate(besin_kalemleri):
                cols[i].metric(besin_etiketleri[b], f"{res[b]/(tg/100):.2f}")
            st.metric("Maliyet (KG)", f"{res['maliyet']/tg*1000:.2f} TL")
    else: st.info("Reçete arşivi boş.")
        
