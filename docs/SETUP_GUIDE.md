# Complete Setup Guide - Real-Time Fraud Risk Scoring Platform

## 📋 Prerequisites Checklist

This guide provides direct download links and installation instructions for ALL tools needed.

---

## 1️⃣ Core Development Tools

### Python 3.11+
**Download**: https://www.python.org/downloads/
- Choose Python 3.11 or 3.12
- **Mac**: `brew install python@3.11`
- **Windows**: Download installer from link above
- **Linux**: `sudo apt update && sudo apt install python3.11 python3.11-venv`

**Verify**: `python3 --version` (should show 3.11+)

---

### Poetry (Python Package Manager)
**Install**: https://python-poetry.org/docs/#installation

```bash
# Official installer (all platforms)
curl -sSL https://install.python-poetry.org | python3 -

# Or via pipx (recommended)
pipx install poetry
```

**Verify**: `poetry --version`

---

### Docker Desktop
**Download**: https://www.docker.com/products/docker-desktop/

- **Mac**: Download .dmg, install, start Docker Desktop
- **Windows**: Download .exe, install, enable WSL 2 backend
- **Linux**: https://docs.docker.com/engine/install/ubuntu/

**Verify**: `docker --version` and `docker-compose --version`

---

## 2️⃣ AWS Tools

### AWS Account Setup
1. **Create account**: https://aws.amazon.com/free/
2. **Create IAM user** (not root):
   - Go to IAM Console: https://console.aws.amazon.com/iam/
   - Create user with "AdministratorAccess" policy
   - Generate access keys (save them securely!)

---

### AWS CLI v2
**Download**: https://aws.amazon.com/cli/

**Mac**:
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Windows**:
```bash
# Download MSI installer
https://awscli.amazonaws.com/AWSCLIV2.msi
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Configure**:
```bash
aws configure --profile fraud-demo
# Enter: Access Key ID, Secret Access Key, Region (us-west-2), Output (json)

export AWS_PROFILE=fraud-demo
```

**Verify**: `aws sts get-caller-identity`

---

## 3️⃣ Kubernetes Tools

### kubectl (Kubernetes CLI)
**Download**: https://kubernetes.io/docs/tasks/tools/

**Mac**:
```bash
brew install kubectl
```

**Windows**:
```bash
# Via Chocolatey
choco install kubernetes-cli

# Or download binary
https://dl.k8s.io/release/v1.29.0/bin/windows/amd64/kubectl.exe
```

**Linux**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

**Verify**: `kubectl version --client`

---

### eksctl (EKS Cluster Manager)
**Download**: https://eksctl.io/installation/

**Mac**:
```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

**Windows**:
```bash
choco install eksctl
```

**Linux**:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Verify**: `eksctl version`

---

### Helm (Kubernetes Package Manager)
**Download**: https://helm.sh/docs/intro/install/

**Mac**:
```bash
brew install helm
```

**Windows**:
```bash
choco install kubernetes-helm
```

**Linux**:
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

**Verify**: `helm version`

---

## 4️⃣ Load Testing & Utilities

### k6 (Load Testing)
**Download**: https://k6.io/docs/get-started/installation/

**Mac**:
```bash
brew install k6
```

**Windows**:
```bash
choco install k6
```

**Linux**:
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Verify**: `k6 version`

---

### jq (JSON Processor)
**Download**: https://jqlang.github.io/jq/download/

**Mac**:
```bash
brew install jq
```

**Windows**:
```bash
choco install jq
```

**Linux**:
```bash
sudo apt install jq
```

**Verify**: `jq --version`

---

## 5️⃣ Kaggle Dataset Access

### Kaggle API Setup
1. **Create account**: https://www.kaggle.com/
2. **Get API credentials**:
   - Go to https://www.kaggle.com/settings
   - Scroll to "API" section
   - Click "Create New API Token"
   - Save `kaggle.json` to `~/.kaggle/kaggle.json`

**Install Kaggle CLI**:
```bash
pip install kaggle
chmod 600 ~/.kaggle/kaggle.json
```

**Download dataset**:
```bash
cd streamlite-inference/data/raw/
kaggle datasets download -d mlg-ulb/creditcardfraud
unzip creditcardfraud.zip
```

**Verify**: You should have `creditcard.csv` in `data/raw/`

---

## 6️⃣ Optional but Recommended

### pyenv (Python Version Manager)
**Download**: https://github.com/pyenv/pyenv#installation

**Mac/Linux**:
```bash
curl https://pyenv.run | bash
```

Add to shell config:
```bash
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
```

---

### Git LFS (for large model files)
**Download**: https://git-lfs.github.com/

**Mac**:
```bash
brew install git-lfs
git lfs install
```

**Windows/Linux**: Follow instructions at link above

---

## 🚀 Quick Verification Script

Save this as `verify_setup.sh` and run it:

```bash
#!/bin/bash

echo "🔍 Verifying setup..."

check_tool() {
    if command -v $1 &> /dev/null; then
        echo "✅ $1: $(command -v $1)"
    else
        echo "❌ $1: NOT FOUND"
    fi
}

check_tool python3
check_tool poetry
check_tool docker
check_tool docker-compose
check_tool aws
check_tool kubectl
check_tool eksctl
check_tool helm
check_tool k6
check_tool jq
check_tool kaggle

echo ""
echo "🔧 Python version:"
python3 --version

echo ""
echo "🔧 AWS Profile:"
aws sts get-caller-identity --profile fraud-demo 2>/dev/null && echo "✅ AWS configured" || echo "❌ AWS not configured"

echo ""
echo "📦 Kaggle credentials:"
[ -f ~/.kaggle/kaggle.json ] && echo "✅ kaggle.json found" || echo "❌ kaggle.json missing"
```

Run it:
```bash
chmod +x verify_setup.sh
./verify_setup.sh
```

---

## 📊 AWS Resource Provisioning

After installing all tools, run these to set up AWS resources:

```bash
# 1. Create ECR repositories
cd infra/aws
./01_ecr.sh

# 2. Create S3 bucket
./02_s3.sh

# 3. Create EKS cluster (this takes ~15 minutes)
eksctl create cluster -f eks-cluster.yaml
```

---

## 🎯 Next Steps

Once all tools are installed:

1. Clone/create the repository
2. Run `poetry install` to install Python dependencies
3. Download Kaggle dataset
4. Run `docker-compose up` to test locally
5. Follow the 15-hour timeline in the project plan

---

## 💡 Troubleshooting

### Docker permission issues (Linux)
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### AWS CLI not found after install
Add to PATH or restart terminal

### Poetry not found
Add `$HOME/.local/bin` to PATH

### kubectl connection refused
Make sure Docker Desktop Kubernetes is enabled (Settings → Kubernetes → Enable)

---

## 📚 Documentation Links

- AWS EKS: https://docs.aws.amazon.com/eks/
- Kubernetes: https://kubernetes.io/docs/
- FastAPI: https://fastapi.tiangolo.com/
- Redis: https://redis.io/docs/
- PyTorch: https://pytorch.org/docs/

---

**Ready to build? Let's go! 🚀**
