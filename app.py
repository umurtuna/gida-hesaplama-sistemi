import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. EN ÜSTTE: SAYFA AYARI
st.set_page_config(page_title="Cocoa Works ERP V7", layout="wide")

# 2. ŞİFRE EKRANI (İzinsiz girişi burada durduruyoruz)
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

# 3. BURASI YENİ: GOOGLE SHEETS BAĞLANTI FONKSİYONU
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    varsayilan_data = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    try:
        # Sayfaları tek tek oku
        malz_df = conn.read(worksheet="malzemeler", ttl=0)
        
        # Sayfalar yoksa veya boşsa hata vermemesi için zırhlı okuma
        try: rece_df = conn.read(worksheet="receteler", ttl=0)
        except: rece_df = varsayilan_data["receteler_tablo"]
            
        try: kur_df = conn.read(worksheet="kurlar", ttl=0)
        except: kur_df = pd.DataFrame([{"doviz": "USD", "oran": 32.5}, {"doviz": "EUR", "oran": 35.0}])
        
        # Sayı Düzenleme (Virgül -> Nokta)
        if malz_df is not None and not malz_df.empty:
            sayisal_kolonlar = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal_kolonlar:
                if col in malz_df.columns:
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            malz_dict = malz_df.set_index("ad").to_dict('index')
        else: malz_dict = {}

        kurlar_dict = kur_df.set_index("doviz")["oran"].to_dict() if not kur_df.empty else varsayilan_data["kurlar"]
        
        return {
            "malzemeler": malz_dict,
            "receteler_tablo": rece_df if rece_df is not None else varsayilan_data["receteler_tablo"],
            "kurlar": kurlar_dict
        }
    except Exception as e:
        st.error(f"⚠️ Bağlantı Hatası: {e}")
        return varsayilan_data

# 4. KRİTİK NOKTA: VERİYİ BAŞLAT
# Uygulama aşağıya devam etmeden önce 'data' burada tanımlanır.
data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 5. ANALİZ FONKSİYONU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0 for k in besin_kalemleri + ["maliyet"]}
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df.iterrows():
        if row["Malzeme"] in malzemeler:
            m = malzemeler[row["Malzeme"]]
            oran = float(row["Miktar (g)"]) / 100
            for b in besin_kalemleri:
                analiz[b] += m[b] * oran
            kur = kurlar.get(m["birim"], 1.0)
            analiz["maliyet"] += (float(m["fiyat"]) * float(kur) / 1000) * float(row["Miktar (g)"])
    return analiz, t_gram

# 6. MENÜ VE İÇERİK (Bundan sonrası uygulamanın görsel kısmı)
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("İşlem Seçin", ["📦 Malzeme Envanteri", "📝 Yeni Malzeme Ekle", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv", "💱 Döviz Kurları"])

# Menü içerikleri (if menu == ... kısımları) buraya gelecek.
# ...
