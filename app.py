import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# ... (Güvenlik ve Veri Yükleme kısımları V21 ile aynıdır, değişmedi) ...

# 4. HESAPLAMA VE İÇERİK BİRLEŞTİRME MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    icerik_detay = {} # Hammadde bazlı toplam gramajı tutmak için
    
    df_calc = df.copy()
    if "Miktar (g)" in df_calc.columns:
        df_calc["Miktar (g)"] = df_calc["Miktar (g)"].apply(zorla_sayi_yap)
        t_gram = df_calc["Miktar (g)"].sum()
    else: return analiz, 0, {}
    
    if t_gram == 0: return analiz, 0, {}
    
    for _, row in df_calc.iterrows():
        m_ad = str(row["Malzeme"]).strip()
        miktar = float(row["Miktar (g)"])
        if miktar <= 0: continue
        
        # İçerik toplama (Ham haliyle isimleri sakla)
        icerik_detay[m_ad] = icerik_detay.get(m_ad, 0.0) + miktar
        
        m_key = m_ad.lower()
        if m_key in malzemeler:
            m = malzemeler[m_key]
            oran = miktar / 100
            for b in besin_kalemleri: analiz[b] += float(m.get(b, 0)) * oran
            kur = float(data["kurlar"].get(str(m.get("birim", "TRY")).upper(), 1.0))
            analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
            
    return analiz, t_gram, icerik_detay

# ... (Menü kısımları Hammaddeler ve Reçete Hazırla aynı kalıyor) ...

# --- KATMANLI ÜRÜN DENEME (GELİŞTİRİLMİŞ) ---
elif menu == "🔬 Katmanlı Ürün Deneme":
    st.header("🔬 Katmanlı Ürün Deneme & İçerik Deklarasyonu")
    d_sayisi = st.number_input("Reçete Sayısı", 1, 3, 2)
    
    final_deneme = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    total_icerik_map = {} # Tüm katmanlardaki hammaddelerin toplandığı yer
    t_yuzde = 0.0
    
    for i in range(int(d_sayisi)):
        with st.expander(f"🛠️ Deneme Reçetesi {i+1}", expanded=True):
            y = st.number_input(f"Karışım % (R{i+1})", 0.0, 100.0, key=f"v22_dy_{i}")
            t_yuzde += y
            if f'v22_den_{i}' not in st.session_state: st.session_state[f'v22_den_{i}'] = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
            
            cm, cb = st.columns([3, 1])
            m_s = cm.selectbox(f"Malzeme Seç", m_list, key=f"v22_dm_{i}")
            if cb.button(f"Ekle", key=f"v22_db_{i}"):
                st.session_state[f'v22_den_{i}'] = pd.concat([st.session_state[f'v22_den_{i}'], pd.DataFrame([{"Malzeme": m_s, "Miktar (g)": 0.0}])], ignore_index=True)
                st.rerun()
                
            d_ed = st.data_editor(st.session_state[f'v22_den_{i}'], num_rows="dynamic", use_container_width=True, key=f"v22_ded_{i}")
            st.session_state[f'v22_den_{i}'] = d_ed
            
            # Analiz yap ve katman içeriğini al
            d_res, d_tg, d_map = besin_analizi_yap(d_ed, data["malzemeler"], data["kurlar"])
            
            if d_tg > 0:
                p = y / 100
                # Besin/Maliyet toplama
                for b in besin_kalemleri: final_deneme[b] += (d_res[b] / (d_tg / 100)) * p
                final_deneme["maliyet"] += (d_res["maliyet"] / (d_tg / 1000)) * p
                
                # İçerik deklarasyonu için gramajları oranla çarpıp ana sepete ekle
                for mat_name, mat_gram in d_map.items():
                    pay_gram = (mat_gram / d_tg) * y # Bu katmandaki 100g içindeki ağırlığı
                    total_icerik_map[mat_name] = total_icerik_map.get(mat_name, 0.0) + pay_gram

    if abs(t_yuzde - 100) < 0.1:
        st.divider()
        st.subheader("🧪 Final Analiz & İçerik Listesi")
        
        # Maliyet ve Besin Tablosu
        st.table(pd.DataFrame({k.capitalize(): [round(final_deneme[k], 2)] for k in besin_kalemleri}))
        st.metric("Final KG Maliyeti", f"{final_deneme['maliyet']:.2f} TL")
        
        # İÇERİK DEKLARASYONU (Azalan sırada hammadde listesi)
        st.subheader("📜 İçerik Deklarasyonu (Azalan Sırada)")
        if total_icerik_map:
            # Sözlüğü gramaja göre büyükten küçüğe sırala
            sorted_icerik = sorted(total_icerik_map.items(), key=lambda x: x[1], reverse=True)
            
            # Metin oluşturma
            icerik_metni = ", ".join([f"{name}" for name, gram in sorted_icerik if gram > 0])
            
            st.info("Bu liste, tüm katmanlardaki ortak hammaddeleri toplayıp ağırlık sırasına göre dizer:")
            st.success(icerik_metni)
            
            # Detaylı Tablo (Kontrol için)
            with st.expander("Detaylı İçerik Dağılımını Gör"):
                detay_df = pd.DataFrame(sorted_icerik, columns=["Hammadde", "100g'daki Miktarı (g)"])
                st.dataframe(detay_df, use_container_width=True)
    else:
        st.warning(f"Toplam oran %100 olmalı. Şu an: %{t_yuzde}")

# ... (Arşiv ve diğer sekmeler aynı kalıyor) ...
