# R2R Integration

R2R (RAG to Riches) entegrasyonu, üretim ortamına hazır, ölçeklenebilir bir retrieval-augmented generation sistemidir.

## Özellikler

- **Vector Search**: R2R bilgi tabanında vektör araması yapma
- **RAG (Retrieval-Augmented Generation)**: Bilgi tabanını kullanarak soru-cevap
- **Döküman Yönetimi**: Dökümanları listeleme ve detaylarını görme
- **Koleksiyon Yönetimi**: Koleksiyonları listeleme
- **Hibrit Arama**: Geleneksel ve vektör arama kombinasyonu
- **Knowledge Graph**: Bilgi grafı destekli arama

## Kurulum

1. Ana proje bağımlılıkları zaten `pyproject.toml` dosyasında tanımlıdır. R2R paketi dahil edilmiştir.

2. Environment değişkenlerini ayarlayın:
```bash
cp integrations/r2r/config/env.example .env
# .env dosyasını düzenleyerek R2R bilgilerinizi girin
```

## Yapılandırma

Aşağıdaki environment değişkenlerini ayarlamanız gerekiyor:

### Gerekli Değişkenler
- `R2R_API_BASE`: R2R API base URL'i
- `R2R_BASE_URL`: R2R base URL'i

### Kimlik Doğrulama (İkisinden birini seçin)
- **Seçenek 1 - API Key**: `R2R_API_KEY`
- **Seçenek 2 - Email/Password**: `R2R_EMAIL` ve `R2R_PASSWORD`

## Kullanım

### Arama (Search)
```json
{
  "action": "search",
  "parameters": {
    "query": "Python programming",
    "limit": 10
  }
}
```

### RAG Sorgusu
```json
{
  "action": "rag",
  "parameters": {
    "query": "Python'da web scraping nasıl yapılır?",
    "use_hybrid": true,
    "use_kg": false
  }
}
```

### Dökümanları Listeleme
```json
{
  "action": "list_documents",
  "parameters": {
    "limit": 20,
    "offset": 0
  }
}
```

### Belirli Döküman Detayı
```json
{
  "action": "get_document",
  "parameters": {
    "document_id": "doc_123456"
  }
}
```

### Koleksiyonları Listeleme
```json
{
  "action": "list_collections",
  "parameters": {}
}
```

## Komut Satırı Kullanımı

```bash
# Arama örneği
echo '{"action": "search", "parameters": {"query": "machine learning"}}' | python main.py

# RAG sorgusu örneği
echo '{"action": "rag", "parameters": {"query": "AI nedir?"}}' | python main.py

# Dökümanları listeleme örneği
echo '{"action": "list_documents", "parameters": {"limit": 5}}' | python main.py
```

## Hata Durumları

Entegrasyon şu durumlarda hata verebilir:
- R2R paketi yüklü değilse
- Environment değişkenleri eksikse
- R2R sunucusuna bağlantı kurulamazsa
- Kimlik doğrulama başarısız olursa

Hatalar JSON formatında döndürülür:
```json
{
  "error": "Error message",
  "type": "ErrorType"
}
```

## Geliştirme

**Not**: Tüm bağımlılıklar ana proje `pyproject.toml` dosyasında yönetilmektedir. R2R paketi burada tanımlanmıştır. 