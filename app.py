import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="COA Works ERP V18", layout="wide")

# 2. GÜVENLİK
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 COA Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if s == "NMR170":
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 3. VERİ YÜKLEME
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

@st.cache_data(ttl=60) # Önbelleği 1 dakikaya düşürdüm (daha hızlı güncellenmesi için)
def verileri_yukle_v18():
    data_yapisi = {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "kurlar": {"USD": 32.5, "EUR": 35.0}}
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            for col in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]:
                if col in m_df.columns:
                    m_df[col] = pd.to_numeric(m_df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            data_yapisi["malzemeler"] = m_df.set_index("ad").to_dict('index')
        
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            data_yapisi["receteler_tablo"] = r_df

        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
    except: pass
    return data_yapisi

data = verileri_yukle_v18()

# 4. HESAPLAMA MOTORU
def besin_analizi_v18(df, malzemeler, kurlar):
    analiz = {k: 0.0 for k in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "maliyet"]}
    df_calc = df.copy()
    df_calc["Miktar (g)"] = pd.to_numeric(df_calc["Miktar (g)"], errors='coerce').fillna(0.0)
    t_gram = df_calc["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df_calc.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        miktar = float(row["Miktar (g)"])
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = miktar / 100
            for b in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]:
                analiz[b] += float(m.get(b, 0)) * oran
            kur = float(kurlar.get(str(m.get("birim", "TRY")).upper(), 1.0))
            analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
    return analiz, t_gram

# 5. ARAYÜZ
st.sidebar.title("COA Works ERP")
if st.sidebar.button("🔄 Verileri Excel'den Çek"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("Menü", ["📦 Envanter", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

if menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    
    # İsim alanını en başa aldık ki her şeyi etkilesin
    r_adi = st.text_input("Ürün İsmi (Excel'e bu isimle geçer):", "urun_01", key="v18_name")

    if 'gecici_v18' not in st.session_state:
        st.session_state.gecici_v18 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])

    col1, col2 = st.columns([3, 1])
    m_list = sorted(data["malzemeler"].keys())
    secilen_m = col1.selectbox("Malzeme Seç", m_list)
    
    if col2.button("➕ Listeye Ekle"):
        yeni = pd.DataFrame([{"Malzeme": secilen_m, "Miktar (g)": 0.0}])
        st.session_state.gecici_v18 = pd.concat([st.session_state.gecici_v18, yeni], ignore_index=True)
        st.rerun()

    # VERİ EDİTÖRÜ
    edited_data = st.data_editor(
        st.session_state.gecici_v18,
        num_rows="dynamic",
        use_container_width=True,
        key="v18_editor"
    )
    st.session_state.gecici_v18 = edited_data

    if not edited_data.empty:
        res, tg = besin_analizi_v18(edited_data, data["malzemeler"], data["kurlar"])
        if tg > 0:
            st.divider()
            # Analiz Değerleri
            cols = st.columns(7)
            etiketler = ["Enerji", "Yağ", "Karb", "Şeker", "Lif", "Prot", "Tuz"]
            anahtar = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
            for i in range(7):
                cols[i].metric(etiketler[i], f"{res[anahtar[i]]/(tg/100):.1f}")
            st.metric("💰 KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")

            st.divider()
            st.subheader("📋 Excel İçin Kopyala")
            
            # KOPYALAMA METNİ (Anlık Güncellenir)
            tablo_text = ""
            for _, row in edited_data.iterrows():
                m_isim = str(row['Malzeme']).strip()
                if m_isim and m_isim != "None":
                    # Sayı formatını Excel'e uygun hale getiriyoruz
                    m_miktar = str(row['Miktar (g)']).replace('.', ',')
                    tablo_text += f"{r_adi}\t{m_isim}\t{m_miktar}\n"
            
            # Veri değiştiğinde burası anında güncellenecektir
            st.text_area("Bu metni kopyalayıp Excel 'receteler' sayfasına yapıştırın:", 
                         value=tablo_text, 
                         height=200, 
                         key="v18_copy_box")

# Diğer sekmeler (Envanter, Katmanlı Ürün, Arşiv) V17 ile aynı yapıdadır.
# ... (Kodun geri kalanı stabil olduğu için aynı kalıyor)
