import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARI
st.set_page_config(page_title="Cocoa Works ERP V7", layout="wide")

# 2. ŞİFRE
ERISIM_SIFRESI = "NMR170" 
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Cocoa Works Güvenli Giriş")
    sifre = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if sifre == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Hatalı!")
    st.stop()

# 3. BAĞLANTI
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    varsayilan_data = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    
    # MALZEMELERİ AYRI OKU
    malz_dict = {}
    try:
        malz_df = conn.read(worksheet="malzemeler", ttl=0)
        if malz_df is not None and not malz_df.empty:
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in malz_df.columns:
                    # Virgül-Nokta ve Tip Dönüşümü
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            malz_dict = malz_df.set_index("ad").to_dict('index')
    except Exception as e:
        st.warning(f"⚠️ 'malzemeler' sayfası okunurken hata oluştu (Veri girilmemiş olabilir).")

    # REÇETELERİ AYRI OKU
    rece_df = varsayilan_data["receteler_tablo"]
    try:
        temp_rece = conn.read(worksheet="receteler", ttl=0)
        if temp_rece is not None: rece_df = temp_rece
    except: pass

    # KURLARI AYRI OKU
    kurlar_dict = varsayilan_data["kurlar"]
    try:
        temp_kur = conn.read(worksheet="kurlar", ttl=0)
        if temp_kur is not None and not temp_kur.empty:
            kurlar_dict = temp_kur.set_index("doviz")["oran"].to_dict()
    except: pass

    return {"malzemeler": malz_dict, "receteler_tablo": rece_df, "kurlar": kurlar_dict}

data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 4. ARAYÜZ
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("Menü", ["📦 Malzeme Envanteri", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else: 
        st.error("Excel'den veri çekilemedi. Lütfen 'malzemeler' sekmesini kontrol edin.")
        st.info("İpucu: Sayfa isminin tamamen küçük harf ve boşluksuz olduğundan emin ol.")

# ... Geri kalan fonksiyonlar (besin_analizi_yap vb.) önceki kodla aynı kalacak şekilde devam edebilirsin.
