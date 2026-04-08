import json

class GidaYonetimi:
    def __init__(self):
        self.malzeme_dosyasi = "malzemeler.json"
        self.recete_dosyasi = "receteler.json"
        self.kurlar = {"TL": 1.0, "USD": 32.5, "EUR": 35.0} 
        self.malzemeler = self.verileri_yukle(self.malzeme_dosyasi)
        self.receteler = self.verileri_yukle(self.recete_dosyasi)

    def verileri_yukle(self, dosya_adi):
        try:
            with open(dosya_adi, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def verileri_kaydet(self, veri, dosya_adi):
        with open(dosya_adi, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=4)

    def kur_guncelle(self):
        print("\n--- DÖVİZ KURU GÜNCELLEME ---")
        try:
            self.kurlar["USD"] = float(input("1 USD kaç TL? : "))
            self.kurlar["EUR"] = float(input("1 EUR kaç TL? : "))
            print("Kurlar başarıyla güncellendi!")
        except ValueError:
            print("Hata: Geçerli bir sayı girin.")

    def veri_girisi(self, isim):
        print(f"\n--- {isim.upper()} BİLGİ GİRİŞİ ---")
        enerji = float(input("- Enerji (kcal/100g): "))
        yag = float(input("- Yağ (g): "))
        karb = float(input("- Karbonhidrat (g): "))
        seker = float(input("  - Şeker (g): "))
        lif = float(input("- Lif (g): "))
        protein = float(input("- Protein (g): "))
        tuz = float(input("- Tuz (g): "))
        birim_fiyat = float(input("- Birim Fiyat (1 kg/lt için): "))
        birim = input("- Para Birimi (TL/USD/EUR): ").upper()
        
        return {
            "besin": {"enerji": enerji, "yag": yag, "karb": karb, "seker": seker, "lif": lif, "protein": protein, "tuz": tuz},
            "maliyet": {"fiyat": birim_fiyat, "birim": birim}
        }

    def malzeme_ekle(self):
        isim = input("Yeni Malzeme Adı: ").strip().lower()
        if isim in self.malzemeler:
            print("Bu malzeme zaten var.")
            return
        self.malzemeler[isim] = self.veri_girisi(isim)
        self.verileri_kaydet(self.malzemeler, self.malzeme_dosyasi)

    def malzeme_duzenle(self):
        print("Mevcutlar:", ", ".join(self.malzemeler.keys()))
        hedef = input("Düzenlenecek malzeme: ").strip().lower()
        if hedef in self.malzemeler:
            self.malzemeler[hedef] = self.veri_girisi(hedef)
            self.verileri_kaydet(self.malzemeler, self.malzeme_dosyasi)
        else:
            print("Malzeme bulunamadı.")

    def recete_olustur(self):
        print("\n--- YENİ REÇETE OLUŞTURMA ---")
        if not self.malzemeler:
            print("Önce malzeme eklemelisiniz!")
            return
        
        recete_adi = input("Reçete (Ürün) Adı: ").strip()
        icerik = []
        toplam_gramaj = 0
        
        while True:
            print("\nMalzemeler:", ", ".join(self.malzemeler.keys()))
            m_adi = input("Eklenecek malzeme (Bitirmek için 'tamam' yazın): ").lower()
            if m_adi == 'tamam': break
            
            if m_adi in self.malzemeler:
                miktar = float(input(f"{m_adi} miktar (gram/ml): "))
                icerik.append({"isim": m_adi, "miktar": miktar})
                toplam_gramaj += miktar
            else:
                print("Malzeme listede yok!")

        if icerik:
            self.receteler[recete_adi] = {"icerik": icerik, "toplam_gramaj": toplam_gramaj}
            self.verileri_kaydet(self.receteler, self.recete_dosyasi)
            print(f"'{recete_adi}' reçetesi kaydedildi.")

    def recete_goruntule(self):
        if not self.receteler:
            print("\nHenüz kayıtlı reçete yok.")
            return
        
        print("\n--- KAYITLI REÇETELER ---")
        liste = list(self.receteler.keys())
        for i, ad in enumerate(liste, 1):
            print(f"{i}. {ad}")
        
        try:
            secim = int(input("\nDetayını görmek istediğiniz numara (Geri için 0): "))
            if secim == 0: return
            
            ad = liste[secim-1]
            r = self.receteler[ad]
            
            print(f"\n--- {ad.upper()} ANALİZİ ---")
            t_enerji, t_seker, t_maliyet = 0, 0, 0
            
            for madde in r["icerik"]:
                m_veri = self.malzemeler[madde['isim']]
                oran = madde['miktar'] / 100
                t_enerji += m_veri["besin"]["enerji"] * oran
                t_seker += m_veri["besin"]["seker"] * oran
                
                birim_maliyet = m_veri["maliyet"]["fiyat"] * self.kurlar.get(m_veri["maliyet"]["birim"], 1.0)
                t_maliyet += (birim_maliyet / 1000) * madde['miktar'] # gram maliyeti
            
            print(f"Toplam Gramaj: {r['toplam_gramaj']}g")
            print(f"Toplam Maliyet: {t_maliyet:.2f} TL")
            print(f"100g için Enerji: { (t_enerji/(r['toplam_gramaj']/100)):.1f} kcal")
            print(f"100g için Şeker: { (t_seker/(r['toplam_gramaj']/100)):.1f} g")
            print("-" * 30)
        except:
            print("Geçersiz seçim.")

    def tum_malzemeleri_listele(self):
        header = f"{'Malzeme':<15} | {'Enerji':<6} | {'Şeker':<6} | {'Maliyet':<8} | {'Döviz'}"
        print("\n" + header + "\n" + "-"*len(header))
        for isim, v in self.malzemeler.items():
            print(f"{isim.capitalize():<15} | {v['besin']['enerji']:<6.1f} | {v['besin']['seker']:<6.1f} | {v['maliyet']['fiyat']:<8.2f} | {v['maliyet']['birim']}")

def menu():
    sistem = GidaYonetimi()
    while True:
        print("\n--- COCOA WORKS ERP V2 ---")
        print("1. Malzeme Ekle")
        print("2. Malzeme Düzenle")
        print("3. Tüm Malzemeleri Görüntüle")
        print("4. YENİ REÇETE OLUŞTUR")
        print("5. KAYITLI REÇETELERİ GÖRÜNTÜLE")
        print("6. Döviz Kurlarını Güncelle")
        print("7. Çıkış")
        
        secim = input("Seçim: ")
        if secim == "1": sistem.malzeme_ekle()
        elif secim == "2": sistem.malzeme_duzenle()
        elif secim == "3": sistem.tum_malzemeleri_listele()
        elif secim == "4": sistem.recete_olustur()
        elif secim == "5": sistem.recete_goruntule()
        elif secim == "6": sistem.kur_guncelle()
        elif secim == "7": break

if __name__ == "__main__":
    menu()
