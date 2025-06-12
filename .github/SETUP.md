# 🔧 GitHub Actions ve Docker Hub Setup Rehberi

Bu rehber, GitHub Actions ile otomatik Docker image build ve publish işlemlerini nasıl kuracağınızı açıkar.

## 📋 Ön Gereksinimler

### 1. Docker Hub Hesabı
- [Docker Hub](https://hub.docker.com/)'da hesap oluşturun
- Username'inizi not edin (örnek: `suysoftware`)

### 2. GitHub Repository
- Repository'niz GitHub'da public olmalı
- Main ve dev branch'leri mevcut olmalı

## 🔐 GitHub Secrets Konfigürasyonu

### 1. Docker Hub Credentials
GitHub repository'nizde şu secrets'ları ekleyin:

1. **DOCKER_USERNAME**: Docker Hub kullanıcı adınız
2. **DOCKER_PASSWORD**: Docker Hub şifreniz veya Access Token

#### Docker Hub Access Token Oluşturma (Önerilen)
1. Docker Hub'da Account Settings > Security'ye gidin
2. "New Access Token" butonuna tıklayın
3. Token adı verin (örnek: "github-actions")
4. "Read, Write, Delete" yetkilerini verin
5. Oluşturulan token'ı kopyalayın
6. GitHub'da `DOCKER_PASSWORD` secret'ı olarak kullanın

### 2. GitHub Secrets Ekleme
1. GitHub repository'nize gidin
2. Settings > Secrets and variables > Actions
3. "New repository secret" butonuna tıklayın
4. Name: `DOCKER_USERNAME`, Secret: Docker Hub kullanıcı adınız
5. Name: `DOCKER_PASSWORD`, Secret: Docker Hub şifreniz/token'ınız

## ⚙️ Workflow Konfigürasyonu

### 1. Docker Image Adını Güncelleme
`.github/workflows/docker-build-and-push.yml` dosyasında:

```yaml
env:
  DOCKER_IMAGE: KULLANICI_ADINIZ/modulex  # Bunu değiştirin!
```

Örnek:
```yaml
env:
  DOCKER_IMAGE: suysoftware/modulex
```

### 2. README'de Image Adını Güncelleme
`README.md` dosyasındaki tüm `suysoftware/modulex` referanslarını kendi kullanıcı adınızla değiştirin.

## 🚀 İlk Deployment

### 1. Değişiklikleri Commit Edin
```bash
git add .
git commit -m "🐳 Add Docker Hub integration"
git push origin main
```

### 2. Workflow'un Çalışmasını İzleyin
1. GitHub repository'nizde Actions sekmesine gidin
2. "Build and Push Docker Image" workflow'unu bulun
3. Çalışmasını izleyin

### 3. Docker Hub'da Image'ı Kontrol Edin
1. Docker Hub hesabınıza gidin
2. Repository'niz oluşmuş olmalı
3. `latest` tag'i görmelisiniz

## 🏷️ Versioning Stratejisi

### Otomatik Version Bumping
Sistem commit mesajlarınıza göre otomatik version artırımı yapar:

- **patch** (0.1.0 → 0.1.1): Normal commit'ler
- **minor** (0.1.0 → 0.2.0): "feat:", "feature:" ile başlayan commit'ler
- **major** (0.1.0 → 1.0.0): "breaking:", "major:" ile başlayan commit'ler

### Manuel Version Bump
1. GitHub repository'nizde Actions sekmesine gidin
2. "Release and Version Bump" workflow'unu seçin
3. "Run workflow" butonuna tıklayın
4. Version type'ı seçin (patch/minor/major)

### Version Tag'leri
Sistem otomatik olarak şu tag'leri oluşturur:
- `v0.1.0` - Specific version
- `latest` - En son stable version
- `dev` - Development version

## 🔄 Workflow Açıklamaları

### docker-build-and-push.yml
- **Tetikleyici**: main branch'e push, PR
- **Görev**: Docker image build, test, push
- **Platform**: linux/amd64, linux/arm64
- **Security**: Docker Scout ile güvenlik taraması

### release.yml
- **Tetikleyici**: main branch'e push
- **Görev**: Version bump, tag oluşturma, release notes
- **Çıktı**: GitHub Release, CHANGELOG.md

## 🐛 Troubleshooting

### Docker Hub Login Hatası
```
Error: Cannot perform an interactive login from a non TTY device
```
**Çözüm**: DOCKER_USERNAME ve DOCKER_PASSWORD secrets'larının doğru girildiğinden emin olun.

### Image Push Hatası
```
denied: requested access to the resource is denied
```
**Çözüm**: Docker Hub'da repository'nin public olduğundan ve push yetkisinin olduğundan emin olun.

### Version Bump Hatası
```
fatal: tag 'v0.1.0' already exists
```
**Çözüm**: Mevcut tag'i silin veya manuel olarak yeni version belirleyin.

## 📞 Destek

Sorun yaşarsanız:
1. GitHub Issues'da sorun bildirin
2. Workflow loglarını kontrol edin
3. Docker Hub repository ayarlarını gözden geçirin 