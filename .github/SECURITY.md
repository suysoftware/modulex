# 🔐 Docker Image Güvenlik Rehberi

Bu rehber, Docker image'larınızı güvenli bir şekilde build ve publish etmek için önemli güvenlik noktalarını açıklar.

## 🛡️ Güvenlik Seviyeleri

### 1. **Temel Güvenlik** (Docker Hub)
```yaml
env:
  DOCKER_IMAGE: ${{ secrets.DOCKER_IMAGE }}  # Secret olarak saklanır
```

**Gerekli Secrets:**
- `DOCKER_USERNAME`: Docker Hub kullanıcı adı
- `DOCKER_PASSWORD`: Docker Hub token'ı (şifre değil!)
- `DOCKER_IMAGE`: `username/repository-name` formatında

### 2. **Yüksek Güvenlik** (GitHub Container Registry)
```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}  # Otomatik
```

**Avantajları:**
- ✅ Hiçbir credential gerekmez
- ✅ GitHub token otomatik kullanılır
- ✅ Repository adı otomatik alınır
- ✅ Private repository desteği
- ✅ GitHub ekosistemi entegrasyonu

## 🎯 Hangi Registry'yi Seçmeli?

### Docker Hub Seçin Eğer:
- ✅ Maksimum erişilebilirlik istiyorsanız
- ✅ Geniş community desteği önemliyse
- ✅ Docker Desktop entegrasyonu istiyorsanız
- ✅ Public image için

### GitHub Container Registry Seçin Eğer:
- ✅ Maksimum güvenlik istiyorsanız
- ✅ Private repository kullanıyorsanız
- ✅ GitHub ekosisteminde kalmak istiyorsanız
- ✅ Ekstra credential yönetimi istemiyorsanız

## 🔧 Uygulama Adımları

### Seçenek 1: Docker Hub (Güvenli Versiyon)

1. **Secrets Ekleyin:**
```bash
DOCKER_USERNAME: your-dockerhub-username
DOCKER_PASSWORD: your-dockerhub-token  # Şifre değil, token!
DOCKER_IMAGE: your-dockerhub-username/modulex
```

2. **Docker Hub Token Oluşturun:**
   - Docker Hub → Account Settings → Security
   - "New Access Token" → "Read, Write, Delete"
   - Token'ı kopyalayın (bir daha görmezsiniz!)

### Seçenek 2: GitHub Container Registry (Önerilen)

1. **Workflow Değiştirin:**
   - `.github/workflows/docker-build-and-push.yml` silin
   - `.github/workflows/docker-build-and-push-ghcr.yml` aktifleştirin

2. **Hiçbir Secret Gerekmez!**
   - GitHub otomatik olarak halleder

## 📦 Kullanım Örnekleri

### Docker Hub:
```bash
docker pull your-username/modulex:latest
docker run -p 8000:8000 your-username/modulex:latest
```

### GitHub Container Registry:
```bash
docker pull ghcr.io/your-username/modulex:latest
docker run -p 8000:8000 ghcr.io/your-username/modulex:latest
```

## 🚨 Güvenlik En İyi Uygulamaları

### 1. **Asla Şifre Kullanmayın**
```bash
❌ DOCKER_PASSWORD: your-dockerhub-password
✅ DOCKER_PASSWORD: your-dockerhub-token
```

### 2. **Token Yetkilerini Sınırlayın**
- Sadece gerekli repository'lere erişim
- "Read, Write" yeterli, "Delete" gereksizse eklemeyin

### 3. **Multi-Factor Authentication**
- Docker Hub hesabınızda MFA aktifleştirin
- GitHub hesabınızda MFA aktifleştirin

### 4. **Regular Token Rotation**
- Token'ları 3-6 ayda bir yenileyin
- Eski token'ları deaktive edin

### 5. **Minimum Permissions**
```yaml
permissions:
  contents: read      # Kod okuma
  packages: write     # Image yazma
  # Başka hiçbir yetki vermeyin
```

## 🔍 Güvenlik Kontrolü

### Image Tarama
Her build'de otomatik güvenlik taraması:
```yaml
- name: Security scan
  uses: docker/scout-action@v1
  with:
    command: cves
    only-severities: critical,high
```

### Vulnerability Monitoring
- Docker Scout ile sürekli monitoring
- Critical/High severity vulnerability'lerde build fail
- Güvenlik raporları GitHub'da görüntülenir

## 🆘 Güvenlik Problemi Durumunda

1. **Token Compromise:**
   - Hemen token'ı revoke edin
   - Yeni token oluşturun
   - GitHub secrets'ı güncelleyin

2. **Image Vulnerability:**
   - Affected version'ları Docker Hub'dan kaldırın
   - Patch uygulanmış yeni version yayınlayın
   - Security advisory yayınlayın

3. **Unauthorized Access:**
   - Docker Hub/GitHub hesap şifresini değiştirin
   - Tüm token'ları revoke edin
   - Audit log'ları kontrol edin

## 📞 Güvenlik Desteği

Güvenlik sorunu bildirmek için:
- 🔒 **Private**: security@your-domain.com
- 🔓 **Public**: GitHub Issues
- 📧 **Urgent**: Direct message to maintainers

---

**Güvenlik, sürekli bir süreçtir. Düzenli olarak güncelleme yapın!** 🔐 