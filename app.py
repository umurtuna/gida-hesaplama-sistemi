import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Cocoa Works Cloud ERP V10", layout="wide")

# 2. ŞİFRE SİSTEMİ
ERISIM_SIFRESI = "Cocoa2026!" 
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Cocoa Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if s == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Hatalı!")
    st.stop()

# 3. BAĞLANTI VE VERİ YÜKLEME
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    data_yapisi = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    
    try:
        # MALZEMELER (İsimsiz okuma - En soldaki ilk sekme)
        malz_df = conn.read(ttl=0)
        if malz_df is not None and not malz_df.empty:
            malz_df.columns = [c.strip().lower() for c in malz_df.columns]
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in malz_df.columns:
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            data_yapisi["malzemeler"] = malz_df.set_index("ad").to_dict('index')

        # REÇETELER VE KURLAR (Hala 400 hatası verme ihtimaline karşı zırhlı okuma)
        try:
            r_df = conn.read(worksheet="receteler", ttl=0)
            if r_df is not None: data_yapisi["receteler_tablo"] = r_df
        except: pass
        
        try:
            k_df = conn.read(worksheet="kurlar", ttl=0)
            if k_df is not None and not k_df.empty:
                k_df.columns = [c.strip().lower() for c in k_df.columns]
                data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
        except: pass

        return data_yapisi
    except Exception as e:
        st.error(f"🚨 Veri yükleme hatası: {e}")
        return data_yapisi

data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0 for k in besin_kalemleri + ["maliyet"]}
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = float(row["Miktar (g)"]) / 100
            for b in besin_kalemleri:
                analiz[b] += float(m[b]) * oran
            k_tipi = m.get("birim", "TRY")
            kur_degeri = float(kurlar.get(k_tipi, 1.0))
            analiz["maliyet"] += (float(m["fiyat"]) * kur_degeri / 1000) * float(row["Miktar (g)"])
    return analiz, t_gram

# 5. ARAYÜZ VE MENÜLER
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("İşlem Seçin", ["📦 Malzeme Envanteri", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.success("Veriler Google Sheets'ten başarıyla yüklendi.")
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else: st.warning("Envanter listesi işlenemedi.")

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama & Kopyalama İstasyonu")
    if not data["malzemeler"]: st.error("Önce Excel'e malzeme girin.")
    else:
        if 'gecici' not in st.session_state: 
            st.session_state.gecici = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
        
        # Malzeme Ekleme Alanı
        c_add1, c_add2 = st.columns([3,1])
        m_sec = c_add1.selectbox("Malzeme Seç", list(data["malzemeler"].keys()))
        if c_add2.button("Listeye Ekle"):
            st.session_state.gecici = pd.concat([st.session_state.gecici, pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])], ignore_index=True)
        
        # Tablo Düzenleme
        edit_df = st.data_editor(st.session_state.gecici, num_rows="dynamic", use_container_width=True)
        st.session_state.gecici = edit_df
        
        if not edit_df.empty:
            res, tg = besin_analizi_yap(edit_df, data["malzemeler"], data["kurlar"])
            if tg > 0:
                st.divider()
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.subheader("📊 Analiz (100g)")
                    st.table(pd.DataFrame({k: [round(res[k]/(tg/100), 2)] for k in besin_kalemleri}))
                with col_res2:
                    st.subheader("💰 Maliyet")
                    st.metric("KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")
                    st.metric("Toplam Reçete", f"{tg:.1f} g")

                st.divider()
                st.subheader("📋 Excel'e Kaydet")
                r_isim = st.text_input("Reçete Adı", "yeni_recete")
                
                # Excel Formatına Hazırlama (Tablo yapısı)
                export_df = edit_df.copy()
                export_df.insert(0, 'recete_ad', r_isim)
                export_df = export_df.rename(columns={"Malzeme": "malzeme", "Miktar (g)": "miktar_g"})
                
                # Sütun isimleri olmadan sadece veriyi gösteriyoruz
                st.info("Aşağıdaki satırları seçip kopyalayın ve Excel'deki 'receteler' sayfasının en altındaki boş hücreye sağ tıklayıp yapıştırın:")
                st.dataframe(export_df, use_container_width=True)
                
                # Kopyalamayı kolaylaştırmak için ham tablo görüntüsü (Tab-separated)
                tablo_metni = ""
                for index, row in export_df.iterrows():
                    tablo_metni += f"{row['recete_ad']}\t{row['malzeme']}\t{str(row['miktar_g']).replace('.', ',')}\n"
                
                st.text_area("Kopyalanacak Metin (Burayı seç, kopyala ve Excel'e yapıştır):", tablo_metni, height=150)
                
        # Tablo Düzenleme
        edit_df = st.data_editor(st.session_state.gecici, num_rows="dynamic", use_container_width=True)
        st.session_state.gecici = edit_df
        
        if not edit_df.empty:
            res, tg = besin_analizi_yap(edit_df, data["malzemeler"], data["kurlar"])
            if tg > 0:
                st.divider()
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.subheader("📊 Analiz (100g)")
                    st.table(pd.DataFrame({k: [round(res[k]/(tg/100), 2)] for k in besin_kalemleri}))
                with col_res2:
                    st.subheader("💰 Maliyet")
                    st.metric("KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")
                    st.metric("Toplam Reçete", f"{tg:.1f} g")

                st.divider()
                st.subheader("📋 Excel'e Kaydetme Formatı")
                r_isim = st.text_input("Reçete Adı (Örn: Bitter_Gofret_V1)", "yeni_recete")
                
                # Excel Formatına Dönüştürme
                # recete_ad, malzeme, miktar_g
                export_df = edit_df.copy()
                export_df.insert(0, 'recete_ad', r_isim)
                export_df = export_df.rename(columns={"Malzeme": "malzeme", "Miktar (g)": "miktar_g"})
                
                csv_output = export_df.to_csv(index=False, header=False, sep=',').strip()
                
                st.info("Aşağıdaki satırları kopyalayıp Excel'deki 'receteler' sayfasının en altındaki boş satıra yapıştırın:")
                st.code(csv_output, language="text")
                st.caption("Not: Yapıştırdıktan sonra Excel'de 'Metni Sütunlara Dönüştür' diyerek virgülü seçebilirsiniz.")
                

elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Katmanlı Ürün Analizi")
    if data["receteler_tablo"].empty: st.warning("Arşivde reçete bulunamadı! Lütfen Excel 'receteler' sayfasını doldurun.")
    else:
        k_sayisi = st.number_input("Katman Sayısı", 1, 5, 2)
        katmanlar = []
        t_oran = 0
        cols = st.columns(k_sayisi)
        for i in range(int(k_sayisi)):
            with cols[i]:
                k_ad = st.selectbox(f"Reçete {i+1}", data["receteler_tablo"]["recete_ad"].unique(), key=f"kat_{i}")
                k_o = st.number_input(f"Oran %", 0.0, 100.0, key=f"ora_{i}")
                katmanlar.append({"ad": k_ad, "oran": k_o})
                t_oran += k_o
        
        if t_oran == 100 and st.button("🧬 Kompozit Analiz Yap"):
            final = {k: 0 for k in besin_kalemleri + ["maliyet"]}
            for k in katmanlar:
                r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == k["ad"]].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                pay = k["oran"] / 100
                for b in besin_kalemleri: final[b] += (r_res[b] / (r_tg/100)) * pay
                final["maliyet"] += (r_res["maliyet"] / (r_tg/1000)) * pay
            st.subheader("🏁 Final Ürün Analizi (100g)")
            st.table(pd.DataFrame({k: [round(final[k], 2)] for k in besin_kalemleri}))
            st.metric("💰 Final KG Maliyeti", f"{final['maliyet']:.2f} TL")

elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        r_isim = st.selectbox("Görüntülenecek Reçete", data["receteler_tablo"]["recete_ad"].unique())
        r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == r_isim].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.write("**İçerik Listesi:**")
        st.dataframe(r_df, use_container_width=True)
        a_res, a_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
        st.write("**Besin Değerleri (100g):**")
        st.table(pd.DataFrame({k: [round(a_res[k]/(a_tg/100), 2)] for k in besin_kalemleri}))
    else: st.info("Arşivde henüz reçete yok.")
