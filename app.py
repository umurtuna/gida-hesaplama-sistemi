import streamlit as st
import json
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Cocoa Works ERP", layout="wide")

# Veri Yükleme ve Kaydetme Fonksiyonları
def verileri_yukle():
    try:
        with open("veriler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "malzemeler": {}, 
            "receteler": {}, 
            "kurlar": {"USD": 32.5, "EUR": 35.0}
        }

def verileri_kaydet(veri):
    with open("veriler.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# Uygulama Hafızasını Başlat (Session State)
if 'data' not in st.session_state:
    st.session_state.data = verileri_yukle()

data = st.session_state.data

st.title("🍫 Cocoa Works Yönetim Paneli")
st.sidebar.header("Menü")
menu = st.sidebar.radio("İşlem Seçin", 
    ["Malzeme Listesi", "Yeni Malzeme Ekle/Düzenle", "Reçete Oluştur", "Kayıtlı Reçeteler", "Döviz Kurları"])

# --- 1. MALZEME LİSTESİ ---
if menu == "Malzeme Listesi":
    st.header("📦 Mevcut Malzemeler ve Besin Değerleri")
    if data["malzemeler"]:
        df = pd.DataFrame.from_dict(data["malzemeler"], orient='index')
        # Besin ve Maliyet verilerini ayırarak tabloyu güzelleştirelim
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Henüz malzeme eklenmemiş.")

# --- 2. YENİ MALZEME EKLE / DÜZENLE ---
elif menu == "Yeni Malzeme Ekle/Düzenle":
    st.header("📝 Malzeme Kayıt ve Güncelleme")
    
    with st.form("malzeme_form"):
        ad = st.text_input("Malzeme Adı (Düzenlemek için mevcut ismi yazın)").lower().strip()
        
        col1, col2, col3 = st.columns(3)
        enerji = col1.number_input("Enerji (kcal)", min_value=0.0)
        yag = col2.number_input("Yağ (g)", min_value=0.0)
        karb = col3.number_input("Karbonhidrat (g)", min_value=0.0)
        
        seker = col1.number_input("Şeker (g)", min_value=0.0)
        lif = col2.number_input("Lif (g)", min_value=0.0)
        protein = col3.number_input("Protein (g)", min_value=0.0)
        
        tuz = col1.number_input("Tuz (g)", min_value=0.0)
        fiyat = col2.number_input("Birim Fiyat (kg/lt)", min_value=0.0)
        birim = col3.selectbox("Para Birimi", ["TL", "USD", "EUR"])
        
        submit = st.form_submit_button("Malzemeyi Kaydet / Güncelle")
        
        if submit and ad:
            data["malzemeler"][ad] = {
                "enerji": enerji, "yag": yag, "karb": karb, "seker": seker,
                "lif": lif, "protein": protein, "tuz": tuz, "fiyat": fiyat, "birim": birim
            }
            verileri_kaydet(data)
            st.success(f"'{ad}' başarıyla kaydedildi!")

# --- 3. REÇETE OLUŞTUR ---
elif menu == "Reçete Oluştur":
    st.header("🧪 Yeni Ürün Reçetesi Hazırla")
    
    if not data["malzemeler"]:
        st.warning("Önce malzeme eklemelisiniz!")
    else:
        recete_adi = st.text_input("Reçete (Ürün) Adı")
        
        # Seçilen malzemeleri tutmak için geçici bir liste
        if 'gecici_icerik' not in st.session_state:
            st.session_state.gecici_icerik = []

        c1, c2 = st.columns([2, 1])
        secilen_m = c1.selectbox("Malzeme Seç", list(data["malzemeler"].keys()))
        miktar = c2.number_input("Miktar (Gram)", min_value=1.0)
        
        if st.button("Malzemeyi Reçeteye Ekle"):
            st.session_state.gecici_icerik.append({"isim": secilen_m, "miktar": miktar})
            st.toast(f"{secilen_m} eklendi!")

        # Mevcut reçete taslağını göster
        if st.session_state.gecici_icerik:
            st.subheader("Reçete İçeriği")
            for i, kalem in enumerate(st.session_state.gecici_icerik):
                st.text(f"- {kalem['isim']}: {kalem['miktar']}g")
            
            if st.button("REÇETEYİ TAMAMLA VE KAYDET"):
                if recete_adi:
                    data["receteler"][recete_adi] = st.session_state.gecici_icerik
                    verileri_kaydet(data)
                    st.session_state.gecici_icerik = [] # Listeyi temizle
                    st.success(f"'{recete_adi}' reçetesi kaydedildi!")
                else:
                    st.error("Lütfen reçete adı girin!")

# --- 4. KAYITLI REÇETELER ---
elif menu == "Kayıtlı Reçeteler":
    st.header("📋 Reçete Analizi ve Maliyet")
    
    if not data["receteler"]:
        st.info("Kayıtlı reçete bulunamadı.")
    else:
        secilen_r = st.selectbox("Görüntülenecek Reçete", list(data["receteler"].keys()))
        icerik = data["receteler"][secilen_r]
        
        t_enerji, t_seker, t_maliyet, t_gramaj = 0, 0, 0, 0
        
        for kalem in icerik:
            m = data["malzemeler"][kalem["isim"]]
            gram = kalem["miktar"]
            t_gramaj += gram
            t_enerji += (m["enerji"] / 100) * gram
            t_seker += (m["seker"] / 100) * gram
            
            # Kur hesabı
            kur = data["kurlar"].get(m["birim"], 1.0)
            t_maliyet += (m["fiyat"] * kur / 1000) * gram

        # Özet Tablo
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Ağırlık", f"{t_gramaj} g")
        col2.metric("Toplam Maliyet", f"{t_maliyet:.2f} TL")
        col3.metric("100g/Enerji", f"{(t_enerji/(t_gramaj/100)):.1f} kcal")

# --- 5. DÖVİZ KURLARI ---
elif menu == "Döviz Kurlarını Güncelle":
    st.header("💱 Güncel Kurlar")
    u_kur = st.number_input("1 USD kaç TL?", value=data["kurlar"]["USD"])
    e_kur = st.number_input("1 EUR kaç TL?", value=data["kurlar"]["EUR"])
    
    if st.button("Kurları Sisteme İşle"):
        data["kurlar"]["USD"] = u_kur
        data["kurlar"]["EUR"] = e_kur
        verileri_kaydet(data)
        st.success("Kurlar başarıyla güncellendi!")
